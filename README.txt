This is a simple web application to produce a samplesheet CSV file for
the Illumina HiSeq instrument. The samplesheet is also used by Brad Chapman's
downstream processing pipeline for demultiplexing.

It works by storing all samplesheets in native CSV format, allowing the user
to edit one using a simple forms-based interface.j

There is no account authorization involved, so the Apache server must be
setup for appropriate access control.

The implementation uses the Python WSGI interface, via the 'wireframe' and
'HyperText' packages (available in github). It requires Python 2.6 or 2.7.

To make this work for you, a number of variables need to be modified for
your setup, specifically URL_BASE, DATADIR, TRASHDIR, REMOTE_LOGIN
and REMOTE_PATH.
