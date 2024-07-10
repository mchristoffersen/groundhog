Groundhog GPR Processor Documentation
=====================================

Python API
----------

.. autosummary::
   ghog.load
   ghog.save
   ghog.filt
   ghog.nmo
   ghog.restack
   ghog.stolt
   ghog.figure

HDF5 I/O
^^^^^^^^
.. autofunction:: ghog.load 
.. autofunction:: ghog.save

Processing
^^^^^^^^^^
.. autofunction:: ghog.filt
.. autofunction:: ghog.nmo 
.. autofunction:: ghog.restack 
.. autofunction:: ghog.stolt 

Visualization
^^^^^^^^^^^^^
.. autofunction:: ghog.figure

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