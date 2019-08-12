import ctypes
from libcbm.wrapper.libcbm_error import LibCBM_Error
from libcbm.wrapper.libcbm_ctypes import LibCBM_ctypes


class LibCBMHandle(LibCBM_ctypes):
    """Initialize a libcbm handle with the specified pools, and flux indicators.

    Arguments:
        dll_path (str): path to the libcbm compiled library
        config (str): a json formatted string containing configuration
            for libcbm pools and flux definitions.

            The number of pools, and flux indicators defined here,
            corresponds to other data dimensions used during the lifetime
            of this instance:

                1. The number of pools here defines the number of columns
                   in the pool value matrix used by several other libCBM
                   functions
                2. The number of flux_indicators here defines the number
                   of columns in the flux indicator matrix in the
                   ComputeFlux method.
                3. The number of pools here defines the number of rows,
                   and the number of columns of all matrices allocated by
                   the :py:func:`AllocateOp` function.


            Example::

                {
                    "pools": [
                        {"id": 1, "index": 0, "name": "pool_1"},
                        {"id": 2, "index": 1, "name": "pool_2"},
                        ...
                        {"id": n, "index": n-1, "name": "pool_n"}],

                    "flux_indicators": [
                        {
                            "id": 1,
                            "index": 0,
                            "process_id": 1,
                            "source_pools": [1, 2]
                            "sink_pools": [3]
                        },
                        {
                            "id": 2,
                            "index": 1,
                            "process_id": 1,
                            "source_pools": [1, 2]
                            "sink_pools": [3]
                        },
                        ...
                    ]
                }

            Pool/Flux Indicators configuration rules:

                1. ids may be any integer, but are constrained to be unique
                   within the set of pools.
                2. indexes must be the ordered set of integers from 0 to
                   n_pools - 1.
                3. For flux indicator source_pools and sink_pools, list
                   values correspond to id values in the collection of
                   pools
    """

    def __init__(self, dll_path, config):
        super().__init__(dll_path)
        self.err = LibCBM_Error()
        p_config = ctypes.c_char_p(config.encode("UTF-8"))
        self.pointer = self._dll.LibCBM_Initialize(
            ctypes.byref(self.err), p_config)
        if self.err.Error != 0:
            raise RuntimeError(self.err.getErrorMessage())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """frees the allocated libcbm pointer"""
        if self.pointer:
            err = LibCBM_Error()
            self._dll.LibCBM_Free(ctypes.byref(err), self.pointer)
            if err.Error != 0:
                raise RuntimeError(err.getErrorMessage())

    def call(self, func_name, *args):
        func = getattr(self._dll, func_name)
        args = (ctypes.byref(self.err), self.pointer) + args
        result = func(*args)
        if self.err.Error != 0:
            raise RuntimeError(self.err.getErrorMessage())
        return result
