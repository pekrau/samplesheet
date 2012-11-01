""" Sequence index definitions for samplesheet generator.

Per Kraulis, Pontus Larsson
"""

# The module variabel BASIC_LOOKUP contains the primary definitions of
# the sequence indexes and their names.
BASIC_LOOKUP = dict()

# The module variable INDEX_LOOKUP, contains a number of aliases
# for the index names.
INDEX_LOOKUP = dict()

# The Illumina index number-to-sequence mappings have been double-checked
# against the documentation from Illumina dated 2011-10-11.
# index1-index27 are from the table "TruSeq RNA and DNA Sample Prep Kits".
# Identifying prefixes: 'index', '', 'idx', 'in', 'i'
ILLUMINA = dict(index1='ATCACG',
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
BASIC_LOOKUP.update(ILLUMINA)
INDEX_LOOKUP.update(ILLUMINA)
INDEX_LOOKUP.update(dict([(k.replace('index', ''), v)
                          for k,v in ILLUMINA.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'idx'), v)
                          for k,v in ILLUMINA.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'in'), v)
                          for k,v in ILLUMINA.items()]))
INDEX_LOOKUP.update(dict([(k.replace('index', 'i'), v)
                          for k,v in ILLUMINA.items()]))

# rpi1-rpi48 are from the table "TruSeq Small RNA Sample Prep Kits",
# after reverse-complement conversion.
# RPI indexes for "TruSeq Small RNA", 
# These are reverse-complement of Illumina documentation
# Identifying prefixes: 'rpi', 'r', 'indexr'
RPI = dict(rpi1='ATCACG',
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
BASIC_LOOKUP.update(RPI)
INDEX_LOOKUP.update(RPI)
INDEX_LOOKUP.update(dict([(k.replace('rpi', 'r'), v)
                          for k,v in RPI.items()]))
INDEX_LOOKUP.update(dict([(k.replace('rpi', 'indexr'), v)
                          for k,v in RPI.items()]))

# The Agilent indexes agilent1-agilent96 are from the Google Docs spreadsheet
# "illumina 96 barcodes plate format_column arrangement" by Joel Gruselius.
# Identifying prefixes: 'agilent', 'a', 'indexa'
AGILENT = dict(agilent1='ATCACG',
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
               agilent96='AGGTTT')
BASIC_LOOKUP.update(AGILENT)
INDEX_LOOKUP.update(AGILENT)
INDEX_LOOKUP.update(dict([(k.replace('agilent', 'a'), v)
                          for k,v in AGILENT.items()]))
INDEX_LOOKUP.update(dict([(k.replace('agilent', 'indexa'), v)
                          for k,v in AGILENT.items()]))

# Indexes mondrian1-mondrian16 are from the PDF "User Guide for ovation
# SP Ultralow Library System" a.k.a. Mondrian system.
# Identifying prefixes: 'mondrian', 'm', 'indexm'
MONDRIAN = dict(mondrian1='AAGGGA',
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
                mondrian16='TGTTGC')
BASIC_LOOKUP.update(MONDRIAN)
INDEX_LOOKUP.update(MONDRIAN)
INDEX_LOOKUP.update(dict([(k.replace('mondrian', 'm'), v)
                          for k,v in MONDRIAN.items()]))
INDEX_LOOKUP.update(dict([(k.replace('mondrian', 'indexm'), v)
                          for k,v in MONDRIAN.items()]))

# Indexes halo1-halo96 are from the PDF "Haloplex PCR Target Enrichment &
# Library Preparation Guide, Version 2.0, November 2011"
# Identifying prefixes: 'halo', 'h', 'indexh'
HALO = dict(halo1='CTCGGT',
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
            halo96='ACTTAT')
BASIC_LOOKUP.update(HALO)
INDEX_LOOKUP.update(HALO)
INDEX_LOOKUP.update(dict([(k.replace('halo', 'h'), v)
                          for k,v in HALO.items()]))
INDEX_LOOKUP.update(dict([(k.replace('halo', 'indexh'), v)
                          for k,v in HALO.items()]))

# Indexes haloht1-haloht96 are the new 8-bp indexes for Haloplex.
# From a CSV file "oligo_reference-halo8.csv" provided by Joel Gruselius.
# Identifying prefixes: 'haloht', 'ht'
HALOHT = dict(haloht1='AACGTGAT',
              haloht2='AAACATCG',
              haloht3='ATGCCTAA',
              haloht4='AGTGGTCA',
              haloht5='ACCACTGT',
              haloht6='ACATTGGC',
              haloht7='CAGATCTG',
              haloht8='CATCAAGT',
              haloht9='CGCTGATC',
              haloht10='ACAAGCTA',
              haloht11='CTGTAGCC',
              haloht12='AGTACAAG',
              haloht13='AACAACCA',
              haloht14='AACCGAGA',
              haloht15='AACGCTTA',
              haloht16='AAGACGGA',
              haloht17='AAGGTACA',
              haloht18='ACACAGAA',
              haloht19='ACAGCAGA',
              haloht20='ACCTCCAA',
              haloht21='ACGCTCGA',
              haloht22='ACGTATCA',
              haloht23='ACTATGCA',
              haloht24='AGAGTCAA',
              haloht25='AGATCGCA',
              haloht26='AGCAGGAA',
              haloht27='AGTCACTA',
              haloht28='ATCCTGTA',
              haloht29='ATTGAGGA',
              haloht30='CAACCACA',
              haloht31='CAAGACTA',
              haloht32='CAATGGAA',
              haloht33='CACTTCGA',
              haloht34='CAGCGTTA',
              haloht35='CATACCAA',
              haloht36='CCAGTTCA',
              haloht37='CCGAAGTA',
              haloht38='CCGTGAGA',
              haloht39='CCTCCTGA',
              haloht40='CGAACTTA',
              haloht41='CGACTGGA',
              haloht42='CGCATACA',
              haloht43='CTCAATGA',
              haloht44='CTGAGCCA',
              haloht45='CTGGCATA',
              haloht46='GAATCTGA',
              haloht47='GACTAGTA',
              haloht48='GAGCTGAA',
              haloht49='GATAGACA',
              haloht50='GCCACATA',
              haloht51='GCGAGTAA',
              haloht52='GCTAACGA',
              haloht53='GCTCGGTA',
              haloht54='GGAGAACA',
              haloht55='GGTGCGAA',
              haloht56='GTACGCAA',
              haloht57='GTCGTAGA',
              haloht58='GTCTGTCA',
              haloht59='GTGTTCTA',
              haloht60='TAGGATGA',
              haloht61='TATCAGCA',
              haloht62='TCCGTCTA',
              haloht63='TCTTCACA',
              haloht64='TGAAGAGA',
              haloht65='TGGAACAA',
              haloht66='TGGCTTCA',
              haloht67='TGGTGGTA',
              haloht68='TTCACGCA',
              haloht69='AACTCACC',
              haloht70='AAGAGATC',
              haloht71='AAGGACAC',
              haloht72='AATCCGTC',
              haloht73='AATGTTGC',
              haloht74='ACACGACC',
              haloht75='ACAGATTC',
              haloht76='AGATGTAC',
              haloht77='AGCACCTC',
              haloht78='AGCCATGC',
              haloht79='AGGCTAAC',
              haloht80='ATAGCGAC',
              haloht81='ATCATTCC',
              haloht82='ATTGGCTC',
              haloht83='CAAGGAGC',
              haloht84='CACCTTAC',
              haloht85='CCATCCTC',
              haloht86='CCGACAAC',
              haloht87='CCTAATCC',
              haloht88='CCTCTATC',
              haloht89='CGACACAC',
              haloht90='CGGATTGC',
              haloht91='CTAAGGTC',
              haloht92='GAACAGGC',
              haloht93='GACAGTGC',
              haloht94='GAGTTAGC',
              haloht95='GATGAATC',
              haloht96='GCCAAGAC')
BASIC_LOOKUP.update(HALOHT)
INDEX_LOOKUP.update(HALOHT)
INDEX_LOOKUP.update(dict([(k.replace('haloht', 'ht'), v)
                          for k,v in HALOHT.items()]))

# Indexes sureselect1-sureselect16 are the 16 SureSelect indexes.
# From a CSV file "oligo_reference-halo8.csv" provided by Joel Gruselius.
# Identifying prefixes: 'sureselect', 'ss'
SURESELECT = dict(sureselect1='ATCACG',
                  sureselect2='CGATGT',
                  sureselect3='TTAGGC',
                  sureselect4='TGACCA',
                  sureselect5='ACAGTG',
                  sureselect6='GCCAAT',
                  sureselect7='CAGATC',
                  sureselect8='ACTTGA',
                  sureselect9='GATCAG',
                  sureselect10='TAGCTT',
                  sureselect11='GGCTAC',
                  sureselect12='CTTGTA',
                  sureselect13='AAACAT',
                  sureselect14='CAAAAG',
                  sureselect15='GAAACC',
                  sureselect16='AAAGCA')
BASIC_LOOKUP.update(SURESELECT)
INDEX_LOOKUP.update(SURESELECT)
INDEX_LOOKUP.update(dict([(k.replace('sureselect', 'ss'), v)
                          for k,v in SURESELECT.items()]))


# Finally, allow all upper-case variants of index designations.
INDEX_LOOKUP.update(dict([(k.upper(), v)
                          for k,v in INDEX_LOOKUP.items()]))
