Groundhog GPR Processor Documentation
=====================================

Installation
------------
To install the Groundhog GPR processor:

.. code-block:: bash

   pip install git+https://github.com/mchristoffersen/groundhog.git

Nominal Workflow
----------------

The usual workflow for processing and interpreting raw Groundhog data looks like this:

   1. Convert raw digitizer files to HDF5 with the ``ghog_mkh5`` command line tool.

      .. code-block:: bash

         ghog_mkh5 /path/to/your/files/*.ghog
      
   2. Run a processing script over the HDF5 files.

      .. code-block:: python

        ## Example processing script
        import ghog

        file = "/your/hdf5/file.h5"

        # Load data
        data = ghog.load(file)

        # Fast time filter (edges in Hz)
        data = ghog.filt(data, (0.5e6, 4e6), axis=0)

        # NMO correction for 100 meter separation
        data = ghog.nmo(data, 100)

        # Restack to constant 5 m intervals between traces
        data = ghog.restack(data, 5)   

        # Slow time filter (edges in wavenumber)
        data = ghog.filt(data, (1/1000, 1/200), axis=1)

        # Stolt migration with default 3.15 dielectric constant
        data = ghog.stolt(data)

        # Save back to the same HDF5 file in a group named restack
        ghog.save(file, data, group="restack")

   3. Use interpretation software, such as `RAGU <https://github.com/btobers/RAGU>`_, to pick reflectors in the data.

There are two additional command line tools:

   * ``ghog_mkgpkg`` generates a `Geopackage <https://www.geopackage.org/>`_ containing the position information of all of the HDF5 files it is directed to. The positionin information in each file is used to create a line object, and each line has the associated HDF5 file name as an attribute.
   * ``ghog_mkqlook`` generates a figure from each HDF5 file it is directed to, saving each figure in the same directory as the accompanying HDF5 file. 

Python API
----------

.. autosummary::
   ghog.load
   ghog.save
   ghog.filt
   ghog.nmo
   ghog.restack
   ghog.stolt
   ghog.gain
   ghog.mute
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
.. autofunction:: ghog.gain
.. autofunction:: ghog.mute

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
