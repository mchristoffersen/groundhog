Groundhog GPR Processor Documentation
=====================================
.. autosummary::
   ghog.load
   ghog.save
   ghog.filt
   ghog.nmo
   ghog.restack
   ghog.stolt

HDF5 I/O
--------
.. autofunction:: ghog.load 
.. autofunction:: ghog.save

Processing
----------
.. autofunction:: ghog.filt
.. autofunction:: ghog.nmo 
.. autofunction:: ghog.restack 
.. autofunction:: ghog.stolt 

Command Line Tools
------------------
ghog_mkh5
^^^^^^^^^
.. argparse::
   :module: ghog.bin.ghog_mkh5
   :func: cli
   :prog: ghog_mkh5

ghog_mkgpkg
^^^^^^^^^^^
.. argparse::
   :module: ghog.bin.ghog_mkgpkg
   :func: cli
   :prog: ghog_mkgpkg

ghog_mkqlook
^^^^^^^^^^^^
.. argparse::
   :module: ghog.bin.ghog_mkqlook
   :func: cli
   :prog: ghog_mkqlook