A simple web service creating samplesheet CSV files for the Illumina HiSeq.
The samplesheet is also used by Brad Chapman's downstream processing
pipeline for demultiplexing.

It works by storing all samplesheets in native CSV format, allowing the user
to edit one using a simple forms-based interface.

There is no account authorization involved, so the Apache server must be
setup for appropriate access control.

The implementation uses the Python WSGI interface, via the 'wireframe' and
'HyperText' packages (available in github). It requires Python 2.6 or 2.7.
The web application is implemented within a single source code file.

To make this work for you, a number of variables need to be modified
for your setup, specifically URL_BASE, DATADIR, and TRASHDIR.

This script no longer transfers the samplesheets onto another machine.

The directory structure has been changed to use yearly subdirectories.
This is transparent for the web interface.
