"""Samplesheet editor.

Apache WSGI interface using the 'wireframe' package.

It has been decided to allow incomplete samplesheets to be transferred
to comicbookguy. The complications involving numerous edge cases were simply
too many. These related to:
- Samplesheets that legitimately lack an index sequence.
- What to do when a previously complete samplesheet becomes incomplete
  when new records are added.
"""

import os
import csv
import logging
import socket
import time
import subprocess

from HyperText.HTML40 import *

import wireframe.application
from wireframe.response import *

hostname = socket.gethostname()
if hostname == 'kraulis':               # Development machine
    URL_BASE = 'http://localhost/samplesheet'
elif hostname == 'maggie':              # Production machine
    URL_BASE = 'http://tools.scilifelab.se/samplesheet'
else:
    raise NotImplementedError("host %s" % hostname)

REMOTE_LOGIN = 'hiseq@cbg'
REMOTE_DIRPATH = '/home/hiseq.hiseq/samplesheets_illumina'

DATADIR  = '/var/local/samplesheet'
TRASHDIR = '/var/local/samplesheet/trash'
TMPDIR   = '/var/local/samplesheet/tmp'

HEADER = ('FCID',
          'Lane',
          'SampleID',
          'SampleRef',
          'Index',
          'Description',
          'Control',
          'Recipe',
          'Operator')

# 'unknown' is hardwired
SAMPLEREFS = ['hg19',
              'hg18',
              'phix',
              'dm3',
              'mm9',
              'araTha_tair9',
              'xenTro2',
              'sacCer2',
              'WS210']

# These index number-to-sequence mappings have been double-checked
# against the documentation from Illumina dated 2011-10-11.
# NOTE: index1-index27 are from the table "TruSeq RNA and DNA Sample Prep Kits".
# NOTE: r1-r48 are from the table "TruSeq Small RNA Sample Prep Kits",
#       after reverse-complement conversion.
INDEX_LOOKUP = dict(index1='ATCACG',
                    index2='CGATGT',
                    index3='TTAGGC',
                    index4='TGACCA',
                    index5='ACAGTG',
                    index6='GCCAAT',
                    index7='CAGATC',
                    index8='ACTTGA',
                    index9='GATCAG',
                    index10='TAGCTT',
                    index11='GGCTAC',
                    index12='CTTGTA',
                    index13='AGTCAA',
                    index14='AGTTCC',
                    index15='ATGTCA',
                    index16='CCGTCC',
                    # index17 is "reserved" by Illumina
                    index18='GTCCGC',
                    index19='GTGAAA',
                    index20='GTGGCC',
                    index21='GTTTCG',
                    index22='CGTACG',
                    index23='GAGTGG',
                    # index24 is "reserved" by Illumina
                    index25='ACTGAT',
                    # index26 is "reserved" by Illumina
                    index27='ATTCCT',
                    # RPI indexes for "TruSeq Small RNA", 
                    # These are reverse-complement of Illumina documentation
                    rpi1='ATCACG',
                    rpi2='CGATGT',
                    rpi3='TTAGGC',
                    rpi4='TGACCA',
                    rpi5='ACAGTG',
                    rpi6='GCCAAT',
                    rpi7='CAGATC',
                    rpi8='ACTTGA',
                    rpi9='GATCAG',
                    rpi10='TAGCTT',
                    rpi11='GGCTAC',
                    rpi12='CTTGTA',
                    rpi13='AGTCAA',
                    rpi14='AGTTCC',
                    rpi15='ATGTCA',
                    rpi16='CCGTCC',
                    rpi17='GTAGAG',
                    rpi18='GTCCGC',
                    rpi19='GTGAAA',
                    rpi20='GTGGCC',
                    rpi21='GTTTCG',
                    rpi22='CGTACG',
                    rpi23='GAGTGG',
                    rpi24='GGTAGC',
                    rpi25='ACTGAT',
                    rpi26='ATGAGC',
                    rpi27='ATTCCT',
                    rpi28='CAAAAG',
                    rpi29='CAACTA',
                    rpi30='CACCGG',
                    rpi31='CACGAT',
                    rpi32='CACTCA',
                    rpi33='CAGGCG',
                    rpi34='CATGGC',
                    rpi35='CATTTT',
                    rpi36='CAAACA',
                    rpi37='CGGAAT',
                    rpi38='CTAGCT',
                    rpi39='CTATAC',
                    rpi40='CTCAGA',
                    rpi41='GACGAC',
                    rpi42='TAATCG',
                    rpi43='TACAGC',
                    rpi44='TATAAT',
                    rpi45='TCATTC',
                    rpi46='TCCCGA',
                    rpi47='TCGAAG',
                    rpi48='TCGGCA')

INDEX_LOOKUP.update(dict([(k.replace('index', ''), v)
                          for k,v in INDEX_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'idx'), v)
                          for k,v in INDEX_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'in'), v)
                          for k,v in INDEX_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('rpi', 'r'), v)
                          for k,v in INDEX_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.upper(), v)
                          for k,v in INDEX_LOOKUP.items()]))


logging.basicConfig(level=logging.INFO)


def get_url(*parts):
    return '/'.join([URL_BASE] + list(parts))

def get_default(request, field, default=''):
    try:
        value = request.cgi_fields[field].value.strip()
        if not value: raise KeyError
    except KeyError:
        if default is None: raise
        return default
    else:
        return value


class Samplesheet(object):

    def __init__(self, fcid):
        # Check input: length and sensible characters
        if len(fcid) !=  9:
            raise HTTP_BAD_REQUEST('FCID must contain 9 characters')
        if not fcid.isalnum():
            raise HTTP_BAD_REQUEST('FCID must contain only alphanumerical characters')
        self.fcid = fcid.upper()
        self.header = []
        self.records = []

    def __str__(self):
        return "Samplesheet %s" % self.fcid

    @property
    def filename(self):
        return os.path.join(DATADIR, self.fcid +'.csv')

    @property
    def tmpfilename(self):
        return os.path.join(TMPDIR,  self.fcid +'.csv')

    @property
    def url(self):
        return get_url(self.fcid)

    @property
    def file_url(self):
        return get_url(self.fcid + '.csv')

    def exists(self):
        if not self.fcid: return False
        return os.path.exists(self.filename)

    def get_content(self):
        return open(self.filename).read()

    def create(self):
        self.header = HEADER[:]         # Proper list copy!
        self.write()

    def read(self):
        try:
            infile = open(self.filename, 'rU')
        except OSError:
            raise HTTP_NOT_FOUND("no such %s" % self)
        reader = csv.reader(infile)
        self.header = reader.next()
        self.records = [record for record in reader if len(record)] # Skip empty
        for record in self.records:     # Convert lane to int
            record[1] = int(record[1])

    def sort(self):
        self.records.sort(key=lambda r: (r[1], r[2]))

    def write(self):
        "Save the records to file."
        outfile = open(self.filename, 'wb')
        writer = csv.writer(outfile)
        writer = csv.writer(outfile, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(self.header)
        writer.writerows(self.records)
        outfile.close()

    def sort_write(self):
        """Sort and write the records to a temporary file.
        The read in the unsorted records again.
        """
        outfile = open(self.tmpfilename, 'w')
        self.sort()
        writer = csv.writer(outfile)
        writer = csv.writer(outfile, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(self.header)
        writer.writerows(self.records)
        outfile.close()
        self.read()
        return self.tmpfilename

def interpret_sampleid_for_index(sampleid, append_a=True):
    try:                            # delimiter: white space
        result = INDEX_LOOKUP[sampleid.split()[-1]]
    except (KeyError, IndexError):
        try:                        # delimiter: underscore
            result = INDEX_LOOKUP[sampleid.split('_')[-1]]
        except (KeyError, IndexError):
            return ''
    if result:
        if append_a: result += 'A'
    return result


def home(request, response):
    sheets = [(os.path.getmtime(os.path.join(DATADIR, s)), s)
              for s in os.listdir(DATADIR) if s.endswith('.csv')]
    sheets.sort()
    sheets.reverse()
    rows = [TR(TH('Samplesheet'),
               TH('Modified'))]
    for mtime, filename in sheets:
        name = os.path.splitext(filename)[0]
        rows.append(TR(TD(A(name, href=get_url(name))),
                       TD(time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(mtime)))))
    info = DIV('Follow the instructions in the Google document ',
               A('10249_01_To create a samplesheet for demultiplexing HiSeq runs',
                 href='https://docs.google.com/a/scilifelab.se/document/d/1tBABcyk-mUt4FosqunrmooRGA-IfgkmLxWe2aj0pnNc/edit'),
               P('Comments or questions to Per Kraulis (',
                 A('per.kraulis@scilifelab.se',
                   href='mailto:per.kraulis@scilifelab.se'),
                 ') or Roman Valls (',
                 A('roman.valls.guimera@scilifelab.se',
                   href='mailto:roman.valls.guimera@scilifelab.se'),
                 ').'))
    form = FORM('Flowcell ID: ',
                INPUT(type='text', name='FCID'),
                INPUT(type='submit', value='Create new samplesheet'),
                method='POST',
                action=get_url())
    table = TABLE(*rows)
    response['Content-Type'] = 'text/html'
    title = 'Samplesheet editor'
    response.append(str(HTML(HEAD(TITLE(title)),
                             BODY(H1(title),
                                  info,
                                  P(form),
                                  P(table)))))

def create(request, response):
    samplesheet = Samplesheet(request.cgi_fields['FCID'].value.strip())
    if samplesheet.exists():
        raise HTTP_BAD_REQUEST('FCID samplesheet exists already')
    samplesheet.create()
    raise HTTP_SEE_OTHER(Location=samplesheet.url)

def view(request, response, xfer_msg=None):
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    if not samplesheet.exists():
        raise HTTP_NOT_FOUND(str(samplesheet))
    samplesheet.read()
    problems = list()
    header = TR(TH(),
                TH('FCID'),
                TH('Lane'),
                TH('SampleID', BR(), '(as "ID_indexN" or "ID N")'),
                TH('SampleRef'),
                TH('Index', BR(), '(sequence)'),
                TH('Description'),
                TH('Control'),
                TH('Recipe'),
                TH('Operator'))
    rows = []
    seqindex_lengths = dict()
    seqindex_lookup = dict()            # Key: lane number, value: seq index
    for pos, record in enumerate(samplesheet.records):
        lanes = []
        for i in xrange(1, 9):
            if i == record[1]:
                lanes.append(OPTION(str(i), selected=True))
            else:
                lanes.append(OPTION(str(i)))
        samplerefs = []
        found = False
        for sr in SAMPLEREFS:
            if sr == record[3]:
                samplerefs.append(OPTION(sr, selected=True))
                found = True
            else:
                samplerefs.append(OPTION(sr))
        if found:
            samplerefs.insert(0, OPTION('unknown'))
        else:
            samplerefs.insert(0, OPTION('unknown', selected=True))
        warning = []
        if record[4]:
            if set(record[4].upper()).difference(set('ATGC')):
                warning.append('Invalid nucleotide sequence!')
            length = seqindex_lengths.setdefault(record[1], len(record[4]))
            if length != len(record[4]):
                warning.append('Unequal length of sequence index for lane!')
            if record[4] in seqindex_lookup.get(record[1], dict()):
                warning.append('Sequence index already used in lane!')
            else:
                seqindex_lookup.setdefault(record[1], set()).add(record[4])
            if interpret_sampleid_for_index(record[2]) != record[4]:
                warning.append('SampleID and Index sequence inconsistent!')
        else:
            warning.append('Missing sequence!')
        if warning:
            problems.append(str(pos+1))
        warning = B(' '.join(warning), style='color: red;')
        rows.append(TR(TD(str(pos+1)),
                       TD(record[0]),
                       TD(SELECT(name="lane%i" % pos, *lanes)),
                       TD(INPUT(type='text', name="sampleid%i" % pos,
                                value=record[2], size=30)),
                       TD(SELECT(name="sampleref%i" % pos, *samplerefs)),
                       TD(INPUT(type='text', name="index%i" % pos,
                                value=record[4], size=10),
                          warning),
                       TD(INPUT(type='text', name="description%i" % pos,
                                value=record[5], size=24)),
                       TD(INPUT(type='radio', name="control%i" % pos,
                                value='N', checked=record[6]=='N'), 'N ',
                          INPUT(type='radio', name="control%i" % pos,
                                value='Y', checked=record[6]=='Y'), 'Y'),
                       TD(INPUT(type='text', name="recipe%i" % pos,
                                value=record[7], size=4)),
                       TD(INPUT(type='text', name="operator%i" % pos,
                                value=record[8], size=4))))
    try:
        previous_lane = samplesheet.records[-1][1]
        previous_sampleref = samplesheet.records[-1][3]
    except IndexError:
        previous_lane = None
        previous_sampleref = None
    lanes = []
    for i in xrange(1, 9):
        if i == previous_lane:
            lanes.append(OPTION(str(i), selected=True))
        else:
            lanes.append(OPTION(str(i)))
        samplerefs = []
        found = False
        for sr in SAMPLEREFS:
            if sr == previous_sampleref:
                samplerefs.append(OPTION(sr, selected=True))
                found = True
            else:
                samplerefs.append(OPTION(sr))
        if found:
            samplerefs.insert(0, OPTION('unknown'))
        else:
            samplerefs.insert(0, OPTION('unknown', selected=True))
    rows.append(TR(TD(str(len(samplesheet.records)+1)),
                   TD(samplesheet.fcid),
                   TD(SELECT(name='lane', multiple=True, *lanes)),
                   TD(INPUT(type='text', name='sampleid', size=30)),
                   TD(SELECT(name='sampleref', *samplerefs)),
                   TD(INPUT(type='text', name='index', size=10)),
                   TD(INPUT(type='text', name='description', size=24)),
                   TD(INPUT(type='radio', checked=True,
                            name='control', value='N'), 'N ',
                      INPUT(type='radio', name='control', value='Y'), 'Y'),
                   TD(INPUT(type='text', name='recipe', size=4)),
                   TD(INPUT(type='text', name='operator', size=4))))
    rows.reverse()
    rows.insert(0, header)
    table = TABLE(border=1, *rows)
    instructions = P(UL(LI('To add another record,'
                           ' fill in values in the first row.'),
                        LI('To delete a record, set its SampleID'
                           ' to a blank character.'),
                        LI('To modify a record, change the value'
                           ' in the field.')),
                     ' Clicking "Save" stores the samplesheet, and transfers'
                     ' it automatically to Comicbookguy.')
    ops = TABLE(TR(TD(FORM(INPUT(type='submit',
                                 value='Sort samplesheet records'),
                           INPUT(type='hidden', name='sort', value='default'),
                           method='POST',
                           action=samplesheet.url))),
                TR(TD(FORM(INPUT(type='submit',
                                 value='Download CSV file (obsolete)'),
                           method='GET',
                           action=samplesheet.file_url))),
                TR(TD(FORM(INPUT(type='submit',
                                 value='Delete this samplesheet',
                                 onclick="return confirm('Really delete?');"),
                           INPUT(type='hidden',
                                 name='http_method', value='DELETE'),
                           method='POST',
                           action=samplesheet.url))),
                width='100%')
    warning = []
    if xfer_msg:
        warning.append(P(xfer_msg))
    if problems:
        warning.append(P("There are problems regarding records %s!" %
                         ', '.join(problems)))
    warning = DIV(style='color: red;', *warning)
    form = FORM(P(INPUT(type='submit', value='Save'),
                  INPUT(type='checkbox', name='append_a',
                        value='y', checked=True),
                  " Append an 'A' to a newly defined index sequence."),
                P(table),
                method='POST',
                action=samplesheet.url)
    response['Content-Type'] = 'text/html'
    response.append(str(HTML(HEAD(TITLE(str(samplesheet))),
                             BODY(A('Home', href=get_url()),
                                  H1(str(samplesheet)),
                                  TABLE(TR(TD(instructions),
                                           TD(ops))),
                                  warning,
                                  form))))

def update(request, response):
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    samplesheet.read()
    try:
        request.cgi_fields['sort']
    except KeyError:
        pass
    else:
        samplesheet.sort()
        samplesheet.write()
        view(request, response)
        return                          # NOTE: This does not scp to CBG!
    try:
        append_a = request.cgi_fields['append_a'].value.strip().lower()
        append_a = append_a == 'y'
    except KeyError:
        append_a = False
    complete = True

    # Modify existing records
    pos = -1                             # Define variable no matter what
    for pos, record in enumerate(samplesheet.records):
        try:
            sampleid = request.cgi_fields["sampleid%i" % pos].value
        except KeyError:
            continue
        record[1] = int(request.cgi_fields["lane%i" % pos].value)
        sampleid = sampleid.strip()
        record[3] = get_default(request, "sampleref%i" % pos, default='unknown')
        try:
            index = get_default(request, "index%i" % pos)
            if not index: raise KeyError
            # If SampleId was changed, then reinterpret
            if sampleid != record[2]: raise KeyError
        except KeyError:
            logging.debug("samplesheet: sampleid '%s'", sampleid)
            index = interpret_sampleid_for_index(sampleid, append_a)
        record[2] = sampleid
        record[4] = index
        record[5] = get_default(request, "description%i" % pos)
        record[6] = request.cgi_fields["control%i" % pos].value
        record[7] = get_default(request, "recipe%i" % pos)
        record[8] = get_default(request, "operator%i" % pos)
    # Delete all records which have blank SampleID
    samplesheet.records = [r for r in samplesheet.records if r[2]]
    # Add a new record
    try:
        sampleid = request.cgi_fields['sampleid'].value.strip()
        if not sampleid: raise KeyError
    except KeyError:
        pass
    else:
        record = [samplesheet.fcid]
        lanes = [int(v) for v in request.cgi_fields.getlist('lane')]
        try:
            record.append(lanes.pop())
        except IndexError:
            record.append(1)
        record.append(sampleid)
        try:
            default = samplesheet.records[-1][3]
        except IndexError:
            default = 'unknown'
        record.append(get_default(request, 'sampleref', default=default))
        try:
            index = request.cgi_fields['index'].value.strip()
            if not index: raise KeyError
        except KeyError:
            index = interpret_sampleid_for_index(record[2], append_a)
        record.append(index)
        try:
            default = samplesheet.records[-1][5]
        except IndexError:
            default = ''
        record.append(get_default(request, 'description', default=default))
        record.append(get_default(request, 'control', default='N'))
        try:
            default = samplesheet.records[-1][7]
        except IndexError:
            default = 'R1'
        record.append(get_default(request, 'recipe', default=default))
        try:
            default = samplesheet.records[-1][8]
        except IndexError:
            default = 'NN'
        record.append(get_default(request, 'operator', default=default))
        samplesheet.records.append(record)
        # Clone sample into other lanes
        while lanes:
            record = record[:]          # Proper list copy!
            record[1] = lanes.pop()
            samplesheet.records.append(record)
    samplesheet.write()                 # Proper save
    source = samplesheet.sort_write()   # Sort and write to tmp, for xfer
    destination = "%s:%s/%s" % (REMOTE_LOGIN,
                                REMOTE_DIRPATH,
                                time.strftime("%Y", time.localtime()))
    try:
        code = subprocess.check_call(['scp',
                                      '-q',
                                      source,
                                      destination])
    except subprocess.CalledProcessError, msg:
        code = msg.returncode
    if code == 0:
        msg = None
    else:
        msg = "The CSV file was saved, but transfer to comicbookguy failed"
        " (error code %s). Contact Per Kraulis or Roman Valls." % code
    view(request, response, xfer_msg=msg)

def delete(request, response):
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    os.rename(samplesheet.filename,
              os.path.join(TRASHDIR, samplesheet.fcid + '.csv'))
    try:
        # regexp must not include 'trash' directory
        source = "%s/20*/%s.csv" % (REMOTE_DIRPATH, samplesheet.fcid)
        destination = "%s/trash" % REMOTE_DIRPATH
        code = subprocess.check_call(['ssh',
                                      REMOTE_LOGIN,
                                      "mv -f -t %s %s" % (destination, source)])
    except subprocess.CalledProcessError, msg:
        raise HTTP_INTERNAL_SERVER_ERROR("The CSV file was not properly deleted"
                                         " from comicbookguy.\n"
                                         "Contact Per Kraulis or Roman Valls!\n"
                                         "%s" % msg)
    raise HTTP_SEE_OTHER(Location=get_url())

def download(request, response):
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    response['Content-Type'] = 'text/csv'
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % samplesheet.fcid
    response.append(samplesheet.get_content())

def redirect_sheet(request, response):
    url = get_url(request.path_named_values['fcid'])
    raise HTTP_SEE_OTHER(Location=url)

def redirect_file(request, response):
    url = "%s.csv" % get_url(request.path_named_values['fcid'])
    raise HTTP_SEE_OTHER(Location=url)


application = wireframe.application.Application(human_debug_output=True)

application.add_map(r'template:/?', GET=home, POST=create)
# For obsolete URLs
application.add_map('template:/sheet/{fcid}', GET=redirect_sheet)
application.add_map('template:/file/{fcid}', GET=redirect_file)
# Modern URLs
application.add_map('template:/{fcid}.csv', GET=download)
application.add_map('template:/{fcid}',
                    GET=view, POST=update, DELETE=delete)
