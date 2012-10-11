"""
Read index sequence(s) from standard in and echo back to standard out with 
a comma-separated list of matching and close-matching index names
"""
import sys
from index_definitions import BASIC_LOOKUP

def hamming_distance(s1, s2):
    """Calculate the Hamming distance between two strings of equal lengths.
    Raise ValueError if strings are of unequal length.
    """
    if len(s1) != len(s2): raise ValueError('strings of unequal length')
    return sum(ch1 != ch2 for ch1, ch2 in zip(s1, s2))    


if __name__ == '__main__':

    mismatches = 1
    for record in sys.stdin:
        index = None
        for col in record.strip().split():
            col = col.upper()
            if len([c for c in col if c not in "ACGTN-"]) > 0:
                continue
            index = col
            break
        if index is None:
            continue

        names = []
        for name, sequence in BASIC_LOOKUP.items():
            try:
                dist = hamming_distance(index,sequence)
                if dist <= mismatches:
                    names.append([name,dist])
            except:
                pass

        print("\t".join(record.strip().split() + [",".join(sorted([n[0] for n in names if n[1] == i])) for i in range(mismatches+1)]))

