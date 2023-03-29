from setuptools import setup
from Cython.Build import cythonize
import numpy

setup(
    name='Amplitude Trigger',
    ext_modules=cythonize("trigger.pyx"),
    zip_safe=False,
    include_dirs=[numpy.get_include()],
)