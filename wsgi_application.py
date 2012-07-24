"""Samplesheet editor.

Apache WSGI interface using the 'wireframe' package.

The transfer of samplesheets to the remote machine (comicbookguy, CBG)
has been changed. The 'push' model used previously, whereby this script
used scp to transfer a newly modified file to CBG, has been scrapped.

Currently, CBG has a rsync command in cron (user hiseq) which syncs
the data directory on the web server with that on CBG.

To allow for this, the directory structure of the samplesheet directory
has been changed to agree with that used on CBG, i.e. yearly subdirectories.

The reason for this change was that the ssh keys could not be made to
work properly when the owner of the apache server was changed back to
the default. We couldn't figure out why, and decided it wasn't worth
the effort. Instead, the current solution was adopted.

/Per Kraulis, 2012-02-06

The data visible in column 'Description' is now also stored in 'SampleProject'.
This is a stop-gap solution.
/Per Kraulis 2012-02-17

Added cut-and-paste feature.
/Per Kraulis 2012-02-28

Apply strict character control on sample name and project name, for CASAVA.
/Per Kraulis 2012-05-10
"""

import logging
import os
import csv
from cStringIO import StringIO
import socket
import time
import string
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

DATA_DIR  = '/var/local/samplesheet'
TRASH_DIR = '/var/local/samplesheet/trash'

# Strict set of allowed characters, to match CASAVA requirements
ALLOWED_CHARS = set(string.ascii_letters + string.digits + '_-')

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
              # item number 2 (index 1) is default
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
              dict(value='WS210', label='worm')]
SAMPLEREFS_SET = set([s['value'] for s in SAMPLEREFS])

# The Illumina index number-to-sequence mappings have been double-checked
# against the documentation from Illumina dated 2011-10-11.
# index1-index27 are from the table "TruSeq RNA and DNA Sample Prep Kits".
BASIC_LOOKUP = dict(index1='ATCACG',
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
                    index27='ATTCCT')
# rpi1-rpi48 are from the table "TruSeq Small RNA Sample Prep Kits",
# after reverse-complement conversion.
# RPI indexes for "TruSeq Small RNA", 
# These are reverse-complement of Illumina documentation
BASIC_LOOKUP.update(
    dict(rpi1='ATCACG',
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
        rpi48='TCGGCA'))
# Indexes agilent1-agilent96 are from the Google Docs spreadsheet
# "illumina 96 barcodes plate format_column arrangement" by Joel Gruselius.
# It specifies the Agilent indexes.
BASIC_LOOKUP.update(
    dict(agilent1='ATCACG',
        agilent2='CGATGT',
        agilent3='TTAGGC',
        agilent4='TGACCA',
        agilent5='ACAGTG',
        agilent6='GCCAAT',
        agilent7='CAGATC',
        agilent8='ACTTGA',
        agilent9='GATCAG',
        agilent10='TAGCTT',
        agilent11='GGCTAC',
        agilent12='CTTGTA',
        agilent13='AAACAT',
        agilent14='CAAAAG',
        agilent15='GAAACC',
        agilent16='TAATCG',
        agilent17='AAAGCA',
        agilent18='CAACTA',
        agilent19='GAATAA',
        agilent20='TACAGC',
        agilent21='AAATGC',
        agilent22='CACCGG',
        agilent23='GACGGA',
        agilent24='AGGCCG',
        agilent25='AACAAA',
        agilent26='CACGAT',
        agilent27='GATATA',
        agilent28='TATAAT',
        agilent29='AACCCC',
        agilent30='CACTCA',
        agilent31='GATGCT',
        agilent32='TCATTC',
        agilent33='AACTTG',
        agilent34='CAGGCG',
        agilent35='GCAAGG',
        agilent36='ATAATT',
        agilent37='AAGACT',
        agilent38='CATGGC',
        agilent39='GCACTT',
        agilent40='TCCCGA',
        agilent41='AAGCGA',
        agilent42='CATTTT',
        agilent43='GCCGCG',
        agilent44='TCGAAG',
        agilent45='AAGGAC',
        agilent46='CCAACA',
        agilent47='GCCTTA',
        agilent48='ATACGG',
        agilent49='AATAGG',
        agilent50='CCACGC',
        agilent51='GCTCCA',
        agilent52='TCGGCA',
        agilent53='ACAAAC',
        agilent54='CCCATG',
        agilent55='GGCACA',
        agilent56='TCTACC',
        agilent57='ACATCT',
        agilent58='CCCCCT',
        agilent59='GGCCTG',
        agilent60='ATCCTA',
        agilent61='ACCCAG',
        agilent62='CCGCAA',
        agilent63='GTAGAG',
        agilent64='TGAATG',
        agilent65='ACCGGC',
        agilent66='CCTTAG',
        agilent67='GTCCGC',
        agilent68='TGCCAT',
        agilent69='ACGATA',
        agilent70='CGAGAA',
        agilent71='GTGAAA',
        agilent72='ATCTAT',
        agilent73='ACTCTC',
        agilent74='CGGAAT',
        agilent75='GTGGCC',
        agilent76='TGCTGG',
        agilent77='ACTGAT',
        agilent78='CTAGCT',
        agilent79='GTTTCG',
        agilent80='TGGCGC',
        agilent81='AGAAGA',
        agilent82='CTATAC',
        agilent83='CGTACG',
        agilent84='ATGAGC',
        agilent85='AGATAG',
        agilent86='CTCAGA',
        agilent87='GAGTGG',
        agilent88='TTCGAA',
        agilent89='AGCATC',
        agilent90='CTGCTG',
        agilent91='GGTAGC',
        agilent92='TTCTCC',
        agilent93='AGCGCT',
        agilent94='CCGTCC',
        agilent95='ATTCCT',
        agilent96='AGGTTT'))
# Indexes mondrian1-mondrian16 are from the PDF "User Guide for ovation
# SP Ultralow Library System" a.k.a. Mondrian system.
BASIC_LOOKUP.update(
    dict(mondrian1='AAGGGA',
        mondrian2='CCTTCA',
        mondrian3='GGACCC',
        mondrian4='TTCAGC',
        mondrian5='AAGACG',
        mondrian6='CCTCGG',
        mondrian7='GGATGT',
        mondrian8='TTCGCT',
        mondrian9='ACACGA',
        mondrian10='CACACA',
        mondrian11='GTGTTA',
        mondrian12='TGTGAA',
        mondrian13='ACAAAC',
        mondrian14='CACCTC',
        mondrian15='GTGGCC',
        mondrian16='TGTTGC'))
# Indexes halo1-halo96 are from the PDF "Haloplex PCR Target Enrichment &
# Library Preparation Guide, Version 2.0, November 2011"
BASIC_LOOKUP.update(
    dict(halo1='CTCGGT',
        halo2='AATCGT',
        halo3='GCGCGT',
        halo4='CGAAGT',
        halo5='TATTCT',
        halo6='AGATCT',
        halo7='CAGGCT',
        halo8='TCCGCT',
        halo9='GGTCCT',
        halo10='TCGTAT',
        halo11='GTCCAT',
        halo12='GATTGG',
        halo13='TTACGG',
        halo14='CCTTCG',
        halo15='GGAGCG',
        halo16='ACGCAG',
        halo17='TGCCAG',
        halo18='GAGAAG',
        halo19='ATCAAG',
        halo20='CGATTC',
        halo21='ACCGTC',
        halo22='TAAGTC',
        halo23='TTCATC',
        halo24='AGCAGC',
        halo25='GCGTCC',
        halo26='AGGTAC',
        halo27='ACGTTA',
        halo28='AACCTA',
        halo29='TGGATA',
        halo30='TTATCA',
        halo31='ATAGAA',
        halo32='CTGGTT',
        halo33='GGAGTT',
        halo34='TACCTT',
        halo35='TCTACT',
        halo36='ATAACT',
        halo37='GAGTAT',
        halo38='AGCTAT',
        halo39='CAAGAT',
        halo40='TCGTTG',
        halo41='ACTCTG',
        halo42='GATATG',
        halo43='TATGCG',
        halo44='GTACCG',
        halo45='CAGACG',
        halo46='CCTGAG',
        halo47='TATTGC',
        halo48='GAGAGC',
        halo49='ATATAC',
        halo50='GCCGAC',
        halo51='CTTAAC',
        halo52='GTTCTA',
        halo53='CAGCTA',
        halo54='ACCGGA',
        halo55='CTCCGA',
        halo56='TTAAGA',
        halo57='GGTTCA',
        halo58='ACGCCA',
        halo59='CGACCA',
        halo60='TCGGAA',
        halo61='GGCCTT',
        halo62='AGACGT',
        halo63='CATAGT',
        halo64='GATGAT',
        halo65='CCTATG',
        halo66='AACTGG',
        halo67='GCGAGG',
        halo68='TTCTCG',
        halo69='GCTGCG',
        halo70='CTGGCG',
        halo71='CGAACG',
        halo72='ATTCAG',
        halo73='CCGTTC',
        halo74='TACTTC',
        halo75='GAGGTC',
        halo76='ATCCTC',
        halo77='TCAATC',
        halo78='CTTCGC',
        halo79='GACCGC',
        halo80='ATAAGC',
        halo81='CATTAC',
        halo82='TGATAC',
        halo83='CTAGAC',
        halo84='TAGAAC',
        halo85='ATGGTA',
        halo86='GTACGA',
        halo87='AAGAGA',
        halo88='GGCAGA',
        halo89='GGAGAA',
        halo90='GCGCAA',
        halo91='GCGGTT',
        halo92='TTAGTT',
        halo93='AGAATT',
        halo94='ATCAGT',
        halo95='GGCGCT',
        halo96='ACTTAT'))

INDEX_LOOKUP = BASIC_LOOKUP.copy()

INDEX_LOOKUP.update(dict([(k.replace('index', ''), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'idx'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'in'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'i'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('rpi', 'r'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('rpi', 'indexr'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('agilent', 'a'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('agilent', 'indexa'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('mondrian', 'm'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('mondrian', 'indexm'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('halo', 'h'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.replace('halo', 'indexh'), v)
                          for k,v in BASIC_LOOKUP.items()]))
INDEX_LOOKUP.update(dict([(k.upper(), v)
                          for k,v in INDEX_LOOKUP.items()]))


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
            if self.exists():
                mtime = os.path.getmtime(self.filepath)
                self._mtime = time.strftime("%Y-%m-%d %H:%M:%S",
                                            time.localtime(mtime))
            else:
                self._mtime = None
            return self._mtime

    def exists(self):
        if not self.fcid: return False
        return os.path.exists(self.filepath)

    def get_content(self):
        return open(self.filepath).read()

    def create(self):
        self.header = HEADER[:]         # Proper list copy!
        self.write()

    def read(self):
        try:
            infile = open(self.filepath, 'rU')
        except OSError:
            raise HTTP_NOT_FOUND("no such %s" % self)
        reader = csv.reader(infile)
        reader.next()                   # Skip past header
        self.header = HEADER[:]         # Use fresh header
        self.records = [record for record in reader if len(record)] # Skip empty
        # Various fixes to the CSV data
        for record in self.records:
            # Convert lane to int
            record[1] = int(record[1])
            # Index sequence: Convert dummy to empty.
            if record[4] == 'QQQQQQ':
                record[4] = ''
            # Upgrade to new samplesheet; additional column 'SampleProject'
            # and copy over data from 'Description'.
            if len(record) < 10:
                record.append(record[5])
            # Copy over data to 'Description' from 'SampleProject'
            # if not already done.
            elif record[9] and not record[5]:
                record[5] = record[9]

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
            # Index sequence: Convert empty to dummy.
            if record[4] == '':
                record[4] = 'QQQQQQ'
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
    """Look for index number at end of samplid.
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

def home(request, response):
    rows = [TR(TH('Samplesheet'),
               TH('Modified'))]
    for sheet in get_samplesheets():
        rows.append(TR(TD(A(sheet.fcid, href=sheet.url)),
                       TD(sheet.mtime)))
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
    # Figure out whether that extra A has been appended previously.
    append_a = None
    for record in samplesheet.records:
        if append_a is None or append_a == True:
            append_a = len(record[4]) > 6 and record[4][-1] == 'A'
    if append_a is None:
        append_a = False
    for pos, record in enumerate(samplesheet.records):
        lanes = []
        for i in xrange(1, 9):
            if i == record[1]:
                lanes.append(OPTION(str(i), selected=True))
            else:
                lanes.append(OPTION(str(i)))
        samplerefs = _get_sampleref_options(record[3])
        warning = []
        if record[4]:                   # Index sequence
            if set(record[4].upper()).difference(set('ATGC')):
                warning.append('Invalid nucleotide sequence!')
            length = seqindex_lengths.setdefault(record[1], len(record[4]))
            if length != len(record[4]):
                warning.append('Unequal length of sequence index for lane!')
            if record[4] in seqindex_lookup.get(record[1], dict()):
                warning.append('Sequence index already used in lane!')
            else:
                seqindex_lookup.setdefault(record[1], set()).add(record[4])
            if interpret_sampleid_for_index(record[2], append_a) != record[4]:
                warning.append('SampleID and Index sequence inconsistent!')
        else:
            warning.append('Missing sequence!')
        if warning:
            problems.append(str(pos+1))
        warning = B(' '.join(warning), style='color: red;')
        # The abominable dot '.' in project identifiers is stored as
        # double underscore, since CASAVA cannot handle dot.
        # For display purposes, the dot is shown instead of double underscore.
        description = record[5].replace('__', '.')
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
                                value=description, size=24)),
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
        samplerefs = _get_sampleref_options(previous_sampleref)
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
    instructions = P(UL(LI('To add several records, cut-and-paste'
                           ' from the Google Docs spreadsheet'
                           ' into the text box to the right.'),
                        LI('To add another record,'
                           ' fill in values in the first row.'),
                        LI('To delete a record, set its SampleID'
                           ' to a blank character.'),
                        LI('To modify a record, change the value'
                           ' in the field.'),
                        LI('NOTE: Sample and project identifiers are now'
                           ' strictly controlled: Offensive characters are'
                           ' automatically converted to underscores.'),
                        LI('Specify index number for the sample like so:'),
                        DL(DT('Ordinary Illumina indexes:'),
                           DD("'samplename_index3', or 'samplename_3'"),
                           DT('Small RNA indexes:'),
                           DD("'samplename_rpi6', or 'samplename_r6'"),
                           DT('Agilent indexes:'),
                           DD("'samplename_agilent14', or 'samplename_a14'"),
                           DT('Mondrian indexes:'),
                           DD("'samplename_mondrian11', or 'samplename_m11'"),
                           DT('Haloplex indexes:'),
                           DD("'samplename_halo11', or 'samplename_h11'"))),
                     ' Click "Save" to store the samplesheet.'
                     ' Comicbookguy will fetch it automatically'
                     ' within 15 minutes.')
    ops = TABLE(TR(TD(FORM(I('Cut-and-paste 4 columns'
                             ' (Lane, Sample, Project, Ref.genome).'),
                           TEXTAREA(name='cutandpaste', cols=40, rows=4),
                           INPUT(type='submit', value='Add'),
                           method='POST',
                           action=samplesheet.url))),
                TR(TD(FORM(INPUT(type='submit',
                                 value='Sort samplesheet records'),
                           INPUT(type='hidden', name='sort', value='default'),
                           method='POST',
                           action=samplesheet.url))),
                ## TR(TD(FORM(INPUT(type='submit',
                ##                  value='Download CSV file (obsolete)'),
                ##            method='GET',
                ##            action=samplesheet.file_url))),
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
    form = FORM(P(INPUT(type='submit', value='Save')),
    ##               INPUT(type='checkbox', name='append_a',
    ##                     value='y', checked=append_a),
    ##               " Append an 'A' to a newly defined index sequence."),
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
        reader = csv.reader(StringIO(cutandpaste), delimiter='\t')
        rows = list(reader)
        # Skip first row if it looks like the header
        if rows and rows[0][0].strip() == 'Lane':
            rows = rows[1:]
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
            if sampleref in SAMPLEREFS_SET:
                record.append(sampleref) # 'SampleRef'
            else:
                record.append('')
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

    # Delete all records which have blank SampleID
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
    for found in SAMPLEREFS:
        if found['value'] == selected:
            break
    else:
        found = SAMPLEREFS[1]           # Yes! Item number 2 (index 1)
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
    samplesheet = Samplesheet(request.path_named_values['fcid'])
    os.rename(samplesheet.filepath,
              os.path.join(TRASH_DIR, samplesheet.fcid + '.csv'))
    raise HTTP_SEE_OTHER(Location=get_url())


def download(request, response):
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
