"""
Read index sequence(s) from standard in and echo back to standard out with 
a comma-separated list of matching and close-matching index names
"""
import sys
from samplesheet.index_definitions import BASIC_LOOKUP

mismatches = 1
print "\t".join(["Input"] + ["{} mismatch".format(str(i)) for i in range(mismatches+1)])

def hamming_distance(s1, s2):
    """Calculate the Hamming distance between two strings of equal lengths
    """
    assert len(s1) == len(s2)
    return sum(ch1 != ch2 for ch1, ch2 in zip(s1, s2))    
    
for record in sys.stdin:
    index = record.strip().split()[-1]
    names = []
    for name, sequence in BASIC_LOOKUP.items():
        try:
            dist = hamming_distance(index,sequence)
            if dist <= mismatches:
                names.append([name,dist])
        except:
            pass
        
    print "\t".join([record.strip()] + [",".join([n[0] for n in names if n[1] == i]) for i in range(mismatches+1)])
    