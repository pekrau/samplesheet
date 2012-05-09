"""Check for overlap between index sequences.
Output a CSV file listing all indexes, giving identical,
one and two mismatch indexes.
"""

import csv

from samplesheet.wsgi_application import BASIC_LOOKUP

outfile = csv.writer(open('index_overlaps.csv', 'wb'))
outfile.writerow(['Index', 'Sequence', 'Identical',
                  'One mismatch', 'Two mismatches'])

def compare(key1, key2):
    for pos in xrange(len(key1)-1, -1, -1):
        if not key1[pos].isdigit():
            k1 = (key1[0:pos+1], int(key1[pos+1:]))
            break
    for pos in xrange(len(key2)-1, -1, -1):
        if not key2[pos].isdigit():
            k2 = (key2[0:pos+1], int(key2[pos+1:]))
            break
    return cmp(k1, k2)

keys = sorted(BASIC_LOOKUP.keys(), cmp=compare)

for key1 in keys:
    seq1 = BASIC_LOOKUP[key1]
    identical = []
    one = []
    two = []
    for key2 in keys:
        if key1 == key2: continue
        seq2 = BASIC_LOOKUP[key2]
        mismatch = 0
        for n1, n2 in zip(seq1, seq2):
            if n1 != n2: mismatch += 1
        if mismatch == 0:
            identical.append(key2)
        elif mismatch == 1:
            one.append(key2)
        elif mismatch == 2:
            two.append(key2)
    outfile.writerow([key1, seq1, ' '.join(identical),
                      ' '.join(one), ' '.join(two)])
