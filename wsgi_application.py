"""Samplesheet editor.

Apache WSGI interface using the 'wireframe' package.

NOTE: Modified to behave after transferring the system from maggie to tools.

Currently, a 'pull' model is used. CBG has a rsync command in cron (user
hiseq) which syncs the data directory on the web server with that on CBG.

To allow for this, the directory structure of the samplesheet directory
has been changed to agree with that used on CBG, i.e. yearly subdirectories.
"""

import logging
import os
import csv
import re
from cStringIO import StringIO
import socket
import time
import string

from HyperText.HTML40 import *
from samplesheet.index_definitions import INDEX_LOOKUP
from samplesheet.annotate_index import hamming_distance, levenshtein_distance

import wireframe.application
from wireframe.response import *

URL_BASE = '/samplesheet'               # Previously configurable, now fixed!

hostname = socket.gethostname().split('.')[0]
if hostname == 'kraulis2':      # Development machine
    DATA_DIR  = '/var/local/samplesheet'
else:                           # Production machine
    DATA_DIR  = '/srv/mfs/samplesheets'
TRASH_DIR = os.path.join(DATA_DIR, 'trash')

# Strict set of allowed characters, to match CASAVA requirements
ALLOWED_CHARS = set(string.ascii_letters + string.digits + '_-')

# Sample identifier regexp
SAMPLEID_RX = re.compile(r'^P\d{3,3}_\d{3,4}[ABCDF]?$')

# Project identifier regexp
# Original, strict regexp
PROJECTID_RX = re.compile(r'^[A-Z]+__[A-Z][a-zA-Z]+_[0-9]{2,2}_[0-9]{2,2}$')
# XXX Relaxed regexp: Was considered too sloppy, not used.
# PROJECTID_RX = re.compile(r'^[A-Z][a-zA-Z_]+_[0-9]{2,2}_[0-9]{2,2}$')

# Minimum allowed edit distances between index sequences in a lane.
MIN_HAMMING_DISTANCE = 3
MIN_LEVENSHTEIN_DISTANCE = 2

HEADER = ('FCID',
          'Lane',
          'SampleID',
          'SampleRef',
          'Index',
          'Description',
          'Control',
          'Recipe',
          'Operator',
          'SampleProject')

SAMPLEREFS = [dict(value='unknown'),
              dict(value='hg19', label='human'),
              dict(value='hg18', label='human'),
              dict(value='phix', label='bacteriophage'),
              dict(value='dm3', label='drosophila'),
              dict(value='mm9', label='mouse'),
              dict(value='rn4', label='rat'),
              ## 'araTha_tair9',
              dict(value='tair9', label='arabidopsis'),
              dict(value='xenTro2', label='xenopus'),
              dict(value='sacCer2', label='yeast'),
              dict(value='WS210', label='worm'),
              dict(value='CanFam3', label='dog'),
              dict(value='other')]
# NOTE: lower-case!
SAMPLEREFS_SET = set([s['value'].lower() for s in SAMPLEREFS])



logging.basicConfig(level=logging.INFO)


def get_year():
    return time.localtime()[0]

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
            raise HTTP_BAD_REQUEST('FCID must contain 9 characters: %s' % fcid)
        if not fcid.isalnum():
            raise HTTP_BAD_REQUEST('FCID must contain only alphanumerical characters')
        self.fcid = fcid.upper()
        self.header = []
        self.records = []

    def __str__(self):
        return "Samplesheet %s" % self.fcid

    def __cmp__(self, other):
        return cmp(self.mtime, other.mtime)

    @property
    def filepath(self):
        try:
            return self._filepath
        except AttributeError:
            filename = self.fcid +'.csv'
            for year in range(2011, get_year() + 1):
                self._filepath = os.path.join(DATA_DIR, str(year), filename)
                if os.path.exists(self._filepath): break
            return self._filepath

    def get_url(self, *suffixes):
        return get_url(self.fcid, *suffixes)

    @property
    def url(self):
        return get_url(self.fcid)

    @property
    def file_url(self):
        return get_url(self.fcid + '.csv')

    @property
    def mtime(self):
        try:
            return self._mtime
        except AttributeError:
            if self.exists:
                mtime = os.path.getmtime(self.filepath)
                self._mtime = time.strftime("%Y-%m-%d %H:%M:%S",
                                            time.localtime(mtime))
            else:
                self._mtime = None
            return self._mtime

    @property
    def exists(self):
        if not self.fcid: return False
        return os.path.exists(self.filepath)

    def get_content(self):
        return open(self.filepath).read()

    def create(self):
        self.header = HEADER[:]         # Proper list copy!
        self.write()

    def from_rows(self, rows):
        self.records = rows[:]
        self.fix_records()

    def read(self):
        try:
            infile = open(self.filepath, 'rU')
        except OSError:
            raise HTTP_NOT_FOUND("no such %s" % self)
        reader = csv.reader(infile)
        reader.next()                   # Skip past header
        self.header = HEADER[:]         # Use fresh header
        self.records = [record for record in reader if len(record)] # Skip empty
        self.fix_records()

    def fix_records(self):
        "Various fixes to original CSV data."
        for record in self.records:
            # Convert lane to int
            record[1] = int(record[1])
            # Blank reference genome must converted to 'unknown' for pipeline
            if not record[3].strip():
                record[3] = 'unknown'
            # Index sequence: Convert dummy to empty.
            # NOTE: Keep this even if the QQQQQQ dummy is no longer used
            # for output; old samplesheets may still have the dummy.
            if record[4] == 'QQQQQQ':
                record[4] = ''
            # Upgrade to new samplesheet; additional column 'SampleProject'
            # and copy over data from 'Description'.
            if len(record) < 10:
                record.append(record[5])
            # Else copy over data to 'Description' from 'SampleProject'.
            else:
                record[5] = record[9]
                # Algorithm to change back first underscore to dot (signified
                # by double underscore), unless special case like "GA_13_02"
                # or "Spruce_13_01".
                try:
                    pos = record[5].index('_')
                    if record[5][pos+1] not in '_0123456789':
                        record[5] = record[5].replace('_', '__', 1)
                except (ValueError, IndexError):
                    pass

    def sort(self):
        self.records.sort(key=lambda r: (r[1], r[2]))

    def write(self):
        "Save the records to file."
        dirpath = os.path.dirname(self.filepath)
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
        outfile = open(self.filepath, 'wb')
        writer = csv.writer(outfile)
        writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(self.header)
        for record in self.records:
            # Copy over data to 'SampleProject' from 'Description'.
            record[9] = record[5]
            writer.writerow(record)
        outfile.close()


def cleanup_identifier(identifier):
    """Strip it, replace all whitespaces with underscore,
    replace the abominable dot '.' with double underscore,
    replace Swedish alphabet characters with ASCII,
    replace disallowed characters with underscore."""
    identifier = identifier.strip()
    identifier = identifier.replace('.', '__')
    identifier = '_'.join(identifier.split())
    identifier = identifier.replace('\xc3\xa5', 'a')
    identifier = identifier.replace('\xc3\xa4', 'a')
    identifier = identifier.replace('\xc3\xb6', 'o')
    identifier = identifier.replace('\xc3\x85', 'A')
    identifier = identifier.replace('\xc3\x84', 'A')
    identifier = identifier.replace('\xc3\x96', 'O')
    chars = []
    for c in identifier:
        if c in ALLOWED_CHARS:
            chars.append(c)
        else:
            chars.append('_')
    return ''.join(chars)

def interpret_sampleid_for_index(sampleid, append_a=False):
    """Look for index number at end of sampleid.
    Also append that extra A if requested."""
    try:
        result = INDEX_LOOKUP[sampleid.split('_')[-1]]
    except (KeyError, IndexError):
        return ''
    if result:
        if append_a: result += 'A'
    return result


def get_samplesheets():
    "Return list of all samplesheets in reverse chronological order."
    sheets = []
    for year in range(2011, get_year() + 1):
        dirpath = os.path.join(DATA_DIR, str(year))
        if not os.path.exists(dirpath): continue
        for filename in os.listdir(dirpath):
            if not filename.endswith('.csv'): continue
            fcid = os.path.splitext(os.path.basename(filename))[0]
            sheets.append(Samplesheet(fcid))
    sheets.sort()
    sheets.reverse()
    return sheets

def invalid_data_dir(request, response):
    "Check whether the DATA_DIR exists and is readable."
    try:
        os.listdir(DATA_DIR)
    except OSError, msg:
        response['Content-Type'] = 'text/html'
        response.append(str(HTML(HEAD(TITLE('Error')),
                                 BODY(H1('Error'),
                                      P("Unable to read DATA_DIR '%s'." % DATA_DIR),
                                      P('Contact Per Kraulis, Pontus Larsson or Niclas Rosell.')))))
        return True
        

def home(request, response):
    if invalid_data_dir(request, response): return
    rows = [TR(TH('Samplesheet'),
               TH('Modified'))]
    for sheet in get_samplesheets():
        rows.append(TR(TD(A(sheet.fcid, href=sheet.url)),
                       TD(sheet.mtime)))
    info = DIV('Follow the instructions in the Google document ',
               B('10249 To create a samplesheet for demultiplexing HiSeq runs.'),
               P('Comments or questions to Per Kraulis (',
                 A('per.kraulis@scilifelab.se',
                   href='mailto:per.kraulis@scilifelab.se'),
                 ') or Pontus Larssons (',
                 A('pontus.larsson@scilifelab.se',
                   href='mailto:pontus.larsson@scilifelab.se'),
                 ').'))
    form1 = FORM('Flowcell ID: ',
                 INPUT(type='text', name='FCID'),
                 INPUT(type='submit', value='Create new samplesheet'),
                 method='POST',
                 action=get_url())
    form2 = FORM('CSV file: ',
                 INPUT(type='file', name='infile'),
                 INPUT(type='submit', value='Upload new samplesheet'),
                 method='POST',
                 enctype='multipart/form-data',
                 action=get_url())
    table = TABLE(*rows)
    response['Content-Type'] = 'text/html'
    title = 'Samplesheet editor'
    response.append(str(HTML(HEAD(TITLE(title)),
                             BODY(H1(title),
                                  info,
                                  P(form1),
                                  P(form2),
                                  P(table)))))

def create(request, response):
    if invalid_data_dir(request, response): return
    try:
        infile = request.cgi_fields['infile'].value.strip()
    except KeyError:
        samplesheet = Samplesheet(request.cgi_fields['FCID'].value.strip())
        if samplesheet.exists:
            raise HTTP_BAD_REQUEST('samplesheet exists already')
    else:
        reader = csv.reader(StringIO(infile))
        rows = [row for row in reader if len(row)] # Skip empty
        rows = rows[1:]                            # Skip header row
        if not rows:
            raise HTTP_BAD_REQUEST('empty file')
        fcid = rows[1][0]
        samplesheet = Samplesheet(fcid)
        if samplesheet.exists:
            raise HTTP_BAD_REQUEST('samplesheet exists already')
        samplesheet.from_rows(rows)
    samplesheet.create()
    raise HTTP_SEE_OTHER(Location=samplesheet.url)

def view(request, response, xfer_msg=None):
    if invalid_data_dir(request, response): return
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    if not samplesheet.exists:
        raise HTTP_NOT_FOUND(str(samplesheet))
    samplesheet.read()
    problems = set()
    header = TR(TH(),
                TH('FCID'),
                TH('Lane'),
                TH('SampleID + index-spec',
                   BR(),
                   '(format: see above)',
                   width='20%'),
                TH('SampleRef'),
                TH('Index', BR(), '(sequence)'),
                TH('ProjectID'),
                TH('Control'),
                TH('Recipe'),
                TH('Operator'))
    rows = []
    seqindex_lookup = dict()            # Key: lane number, value: seq index
    # Figure out whether that extra A has been appended previously.
    append_a = None
    for record in samplesheet.records:
        if append_a is None or append_a == True:
            append_a = len(record[4]) > 6 and record[4][-1] == 'A'
    if append_a is None:
        append_a = False
    # Require same index sequence length within each lane.
    index_sequence_lengths = [None] * 9     # 1-based index for max 8 lanes.
    for pos, record in enumerate(samplesheet.records):
        lane = record[1]
        lanes = []
        for i in xrange(1, 9):
            if i == lane:
                lanes.append(OPTION(str(i), selected=True))
            else:
                lanes.append(OPTION(str(i)))
        samplerefs = _get_sampleref_options(record[3])
        sample_warning = []
        project_warning = []
        # Check valid sampleid
        sampleid = record[2]
        if not SAMPLEID_RX.match(sampleid):
            sampleid = '_'.join(sampleid.split('_')[:-1])
            if not SAMPLEID_RX.match(sampleid):
                sample_warning.append('Invalid SampleID.')
        if record[3] == 'unknown':
            sample_warning.append('Unknown SampleRef.')
        if record[4]:                   # Check index sequence; '-' for dual
            if set(record[4].upper()).difference(set('ATGC-')):
                sample_warning.append('Invalid nucleotide in index sequence.')
            if index_sequence_lengths[lane] is None:
                index_sequence_lengths[lane] = len(record[4])
            else:
                if index_sequence_lengths[lane] != len(record[4]):
                    sample_warning.append('Unequal length of index sequence in lane.')
            other_seqindices = seqindex_lookup.get(lane, set())
            if record[4] in other_seqindices:
                sample_warning.append('Index sequence already used in lane.')
            else:
                for other_seqindex in other_seqindices:
                    ld = levenshtein_distance(record[4], other_seqindex,
                                              shortest=True)
                    if ld < MIN_LEVENSHTEIN_DISTANCE:
                        sample_warning.append('Too small Levenshtein distance'
                                              ' between this index sequence'
                                              ' and another in lane.')
                        break
                    hd = hamming_distance(record[4], other_seqindex,
                                          shortest=True)
                    if hd < MIN_HAMMING_DISTANCE:
                        sample_warning.append('Too small Hamming distance'
                                              ' between this index sequence'
                                              ' and another in lane.')
                        break
                seqindex_lookup.setdefault(lane, set()).add(record[4])
            indexseq = interpret_sampleid_for_index(record[2], append_a)
            if indexseq and indexseq != record[4]:
                sample_warning.append('SampleID and index sequence inconsistent.')
            if not record[4]:
                sample_warning.append('Index sequence missing.')
        else:
            sample_warning.append('Missing sequence.')
        if sample_warning:
            problems.add(pos+1)
        sample_warning = B('<br>'.join(sample_warning), style='color: red;')
        # The abominable dot '.' in project identifiers is stored as
        # double underscore, since CASAVA cannot handle dot.
        # For display purposes, the dot is shown instead of double underscore.
        description = record[5].replace('__', '.')
        if not PROJECTID_RX.match(record[5]):
            project_warning.append('Project ID is malformed')
        if project_warning:
            problems.add(pos+1)
        project_warning = B('<br>'.join(project_warning), style='color: red;')
        rows.append(TR(TD(str(pos+1)),
                       TD(record[0]),
                       TD(SELECT(name="lane%i" % pos, *lanes)),
                       TD(INPUT(type='text', name="sampleid%i" % pos,
                                value=record[2], size=24),
                          sample_warning),
                       TD(SELECT(name="sampleref%i" % pos, *samplerefs)),
                       TD(INPUT(type='text', name="index%i" % pos,
                                value=record[4], size=16)),
                       TD(INPUT(type='text', name="description%i" % pos,
                                value=description, size=24),
                          project_warning),
                       TD(INPUT(type='radio', name="control%i" % pos,
                                value='N', checked=record[6]=='N'), 'N ',
                          BR(),
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
        samplerefs = _get_sampleref_options(previous_sampleref)
    rows.append(TR(TD(str(len(samplesheet.records)+1)),
                   TD(samplesheet.fcid),
                   TD(SELECT(name='lane', multiple=True, *lanes)),
                   TD(INPUT(type='text', name='sampleid', size=24)),
                   TD(SELECT(name='sampleref', *samplerefs)),
                   TD(INPUT(type='text', name='index', size=16)),
                   TD(INPUT(type='text', name='description', size=24)),
                   TD(INPUT(type='radio', checked=True,
                            name='control', value='N'), 'N ',
                      BR(),
                      INPUT(type='radio', name='control', value='Y'), 'Y'),
                   TD(INPUT(type='text', name='recipe', size=4)),
                   TD(INPUT(type='text', name='operator', size=4))))
    rows.reverse()
    rows.insert(0, header)
    table = TABLE(border=1, cellpadding=2, *rows)
    instructions = P(UL(LI('To add several records, cut-and-paste'
                           ' from the Google Docs spreadsheet'
                           ' into the text box to the right, then save.'),
                        LI('To add another record, fill in values'
                           ' in the first row, then save.'),
                        LI('To delete a record, set its SampleID'
                           ' to a blank character, then save.'),
                        LI('To modify a record, change the value'
                           ' in the field, then save.'),
                        LI('Offensive characters in Project Identifiers'
                           ' will be automatically converted'
                           ' to underscores.'),
                        LI('SampleID must look like ',
                           B('P123_456'), ', possibly with any of the'
                           ' characters B, C, D or F attached.'),
                        LI('Specify index number for the sample by adding the'
                           ' appropriate suffix using underscore, like so:',
                           TABLE(TR(TH('Index type'),
                                    TH('Standard index spec'),
                                    TH('Alternate short index spec')),
                                 TR(TD('Illumina'),
                                    TD('sampleid_index3'),
                                    TD('sampleid_i3')),
                                 TR(TD('Small RNA'),
                                    TD('sampleid_rpi6'),
                                    TD('sampleid_r6')),
                                 TR(TD('Agilent'),
                                    TD('sampleid_agilent14'),
                                    TD('sampleid_a14')),
                                 TR(TD('Mondrian'),
                                    TD('sampleid_mondrian11'),
                                    TD('sampleid_m11')),
                                 TR(TD('Haloplex'),
                                    TD('sampleid_halo11'),
                                    TD('sampleid_h11')),
                                 TR(TD('Haloplex HT 8-bp'),
                                    TD('sampleid_haloht31'),
                                    TD('sampleid_hht31')),
                                 TR(TD('SureSelect'),
                                    TD('sampleid_sureselect9'),
                                    TD('sampleid_ss9')),
                                 TR(TD('TruSeq DNA Dual HT'),
                                    TD('sampleid_dual13')),
                                 TR(TD('Nextera Dual HT'),
                                    TD('sampleid_nxdual15')),
                                 TR(TD('Halo HT Dual'),
                                    TD('sampleid_haloht15dual')),
                                 TR(TD('Illumina Dual'),
                                    TD('sampleid_index15dual')),
                                 border=1,
                                 cellpadding=2))))
    ops = TABLE(TR(TD(FORM(I('Cut-and-paste 4 columns'
                             ' (Lane, Sample, Project, Ref.genome).'),
                           TEXTAREA(name='cutandpaste', cols=40, rows=4),
                           INPUT(type='submit', value='Add'),
                           method='POST',
                           action=samplesheet.url))),
                TR(TD(FORM(INPUT(type='submit',
                                 value='Sort samplesheet records'),
                           INPUT(type='hidden',
                                 name='sort', value='default'),
                           method='POST',
                           action=samplesheet.url))),
                TR(TD(FORM(INPUT(type='submit',
                                 value='Delete this samplesheet',
                                 onclick="return confirm('Really delete?');"),
                           INPUT(type='hidden',
                                 name='http_method', value='DELETE'),
                           method='POST',
                           action=samplesheet.url))),
                width='100%')
    title = "%s (%s)" % (samplesheet,
                         A("CSV file", href=samplesheet.file_url))
    warning = []
    if xfer_msg:
        warning.append(P(xfer_msg))
    if problems:
        problems = sorted(problems)
        problems = ', '.join(map(str, problems))
        warning.append(P("There are problems regarding records %s!" % problems))
    warning = DIV(style='color: red;', *warning)
    form = FORM(P(INPUT(type='submit', value='Save'),
                  ' Store the samplesheet. The pipeline computer (comicbookguy)'
                  ' will fetch it automatically within 15 minutes.'),
                P(table),
                method='POST',
                action=samplesheet.url)
    response['Content-Type'] = 'text/html'
    response.append(str(HTML(HEAD(TITLE(str(samplesheet))),
                             BODY(A('Home', href=get_url()),
                                  H1(title),
                                  TABLE(TR(TD(instructions),
                                           TD(ops))),
                                  warning,
                                  form))))

def update(request, response):
    if invalid_data_dir(request, response): return
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    samplesheet.read()

    # Sort existing records
    try:
        request.cgi_fields['sort']
    except KeyError:
        pass
    else:
        samplesheet.sort()
        samplesheet.write()
        view(request, response)
        return

    # Cut-and-paste from Google Docs spreadsheet
    try:
        cutandpaste = request.cgi_fields['cutandpaste'].value
        if not cutandpaste: raise KeyError
    except KeyError:
        pass
    else:
        logging.debug('Cut-and-paste: "%s"', cutandpaste)
        if '\t' in cutandpaste:
            reader = csv.reader(StringIO(cutandpaste), delimiter='\t')
        else:
            reader = csv.reader(StringIO(cutandpaste), delimiter=',')
        rows = list(reader)
        # Skip first row if it looks like the header
        if rows and rows[0][0].strip() == 'Lane':
            rows = rows[1:]
        logging.debug('rows: "%s"', rows)
        last_lane = None
        if samplesheet.records:
            control = samplesheet.records[-1][6]
            recipe = samplesheet.records[-1][7]
            operator = samplesheet.records[-1][8]
        else:
            control = 'N'
            recipe = 'R1'
            operator = 'NN'
        for row in rows:
            if len(row) < 4: continue
            record = [samplesheet.fcid]
            lane = row[0].strip()
            if not lane:
                lane = last_lane or '1'
            try:
                lane = max(1, min(8, int(lane.split()[-1])))
                record.append(lane) # 'Lane'
            except ValueError:
                continue
            last_lane = str(lane)
            sampleid = cleanup_identifier(row[1])
            if not sampleid: continue
            record.append(sampleid)      # 'SampleID'
            sampleref = row[3].strip()
            if sampleref.lower() in SAMPLEREFS_SET:
                record.append(sampleref) # 'SampleRef'
            else:
                record.append('unknown')
            record.append(interpret_sampleid_for_index(sampleid)) # 'Index'
            project = cleanup_identifier(row[2])
            if not project: continue
            record.append(project)       # 'Description'
            record.append(control)       # 'Control'
            record.append(recipe)        # 'Recipe'
            record.append(operator)      # 'Operator'
            record.append(project)       # 'SampleProject'
            samplesheet.records.append(record)
        samplesheet.write()
        view(request, response)
        return

    # Flag for appending 'A' to index sequence
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
            sampleid = cleanup_identifier(sampleid)
        except KeyError:
            continue
        record[1] = int(request.cgi_fields["lane%i" % pos].value)
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
        record[5] = cleanup_identifier(get_default(request, "description%i" % pos))
        record[6] = request.cgi_fields["control%i" % pos].value
        record[7] = get_default(request, "recipe%i" % pos)
        record[8] = get_default(request, "operator%i" % pos)

    # Only keep records with defined SampleID; delete all others
    samplesheet.records = [r for r in samplesheet.records if r[2]]

    # Add a new record
    try:
        sampleid = request.cgi_fields['sampleid'].value.strip()
        sampleid = cleanup_identifier(sampleid)
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
        record.append(cleanup_identifier(get_default(request, 'description', default=default)))
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
        try:
            default = samplesheet.records[-1][9]
        except IndexError:
            default = ''
        record.append(cleanup_identifier(get_default(request, 'sampleproject', default=default)))
        samplesheet.records.append(record)
        # Clone sample into other lanes
        while lanes:
            record = record[:]          # Proper list copy!
            record[1] = lanes.pop()
            samplesheet.records.append(record)
    samplesheet.write()                 # Proper save
    view(request, response)


def _get_sampleref_options(selected):
    "Get the list of OPTION elements."
    if selected:
        selected = selected.lower()
    for found in SAMPLEREFS:
        if found['value'].lower() == selected:
            break
    else:
        found = SAMPLEREFS[0]           # Item number 1 'unknown' is default
    options = []
    for sampleref in SAMPLEREFS:
        try:
            label = "%s (%s)" % (sampleref['value'], sampleref['label'])
        except KeyError:
            label = sampleref['value']
        if sampleref == found:
            options.append(OPTION(label,
                                  value=sampleref['value'],
                                  selected=True))
        else:
            options.append(OPTION(label, value=sampleref['value']))
    return options


def delete(request, response):
    if invalid_data_dir(request, response): return
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    os.rename(samplesheet.filepath,
              os.path.join(TRASH_DIR, samplesheet.fcid + '.csv'))
    raise HTTP_SEE_OTHER(Location=get_url())


def download(request, response):
    if invalid_data_dir(request, response): return
    fcid = request.path_named_values['fcid']
    if fcid == 'list':
        outfile = StringIO()
        writer = csv.writer(outfile)
        writer = csv.writer(outfile, quoting=csv.QUOTE_NONNUMERIC)
        for row in get_samplesheets():
            writer.writerow(row)
        content = outfile.getvalue()
    else:
        samplesheet = Samplesheet(fcid)
        content = samplesheet.get_content()
    response['Content-Type'] = 'text/csv'
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % fcid
    response.append(content)


application = wireframe.application.Application(human_debug_output=True)
application.add_map(r'template:/?',
                    GET=home,
                    POST=create)
# Must be specified before the next one, to catch the suffix.
application.add_map('template:/{fcid}.csv',
                    GET=download)
application.add_map('template:/{fcid}',
                    GET=view,
                    POST=update,
                    DELETE=delete)
