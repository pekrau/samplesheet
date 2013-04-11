"""
Read index sequence(s) from standard in and echo back to standard out with 
a comma-separated list of matching and close-matching index names
"""
import sys
from index_definitions import BASIC_LOOKUP

def hamming_distance(s1, s2, shortest=False):
    """Calculate the Hamming distance between two strings.
    If 'shortest' is True, then check the strings up to the length of
    the shortest of them.
    If 'shortest' is False, raise ValueError if strings are of unequal length.
    """
    if len(s1) != len(s2):
        if shortest:
            length = min(len(s1), len(s2))
            s1 = s1[:length]
            s2 = s2[:length]
        else:
            raise ValueError('strings of unequal length')
    return sum(ch1 != ch2 for ch1, ch2 in zip(s1, s2))    

def levenshtein_distance(s1, s2, shortest=False):
    """Calculate the Levenshtein distance between two strings.
    If 'shortest' is True, then check the strings up to the length of
    the shortest of them.
    If 'shortest' is False, compare the strings as they are.
    From http://en.wikibooks.org/wiki/Algorithm_implementation/Strings/Levenshtein_distance#Python 4th version.
    """
    if shortest and len(s1) != len(s2):
        length = min(len(s1), len(s2))
        s1 = s1[:length]
        s2 = s2[:length]
    oneago = None
    thisrow = range(1, len(s2) + 1) + [0]
    for x in xrange(len(s1)):
        twoago, oneago, thisrow = oneago, thisrow, [0] * len(s2) + [x + 1]
        for y in xrange(len(s2)):
            delcost = oneago[y] + 1
            addcost = thisrow[y - 1] + 1
            subcost = oneago[y - 1] + (s1[x] != s2[y])
            thisrow[y] = min(delcost, addcost, subcost)
    return thisrow[len(s2) - 1]


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

