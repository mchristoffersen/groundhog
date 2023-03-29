import numpy as np
cimport numpy as np
cimport cython

np.import_array()

DTYPE = np.int16
ctypedef np.int16_t DTYPE_t

@cython.boundscheck(False)
@cython.wraparound(False)
def ampTrigger(np.ndarray[DTYPE_t, ndim=1] x, np.int16_t a):
    cdef Py_ssize_t n = x.shape[0]
    for i in range(n):
        if(x[i] > a):
            return i
    return -1
