import ctypes, logging, sqlite3, numpy as np
from numpy.ctypeslib import ndpointer

class LibCBM_SpinupState:
    HistoricalRotation = 0,
    HistoricalDisturbance = 1,
    LastPassDisturbance = 2,
    GrowToFinalAge = 3,
    Delay = 4,
    Done = 5
    @staticmethod
    def getName(x):
        if x == 0: return "HistoricalRotation" 
        elif x == 1: return "HistoricalDisturbance"
        elif x == 2: return "LastPassDisturbance"
        elif x == 3: return "GrowToFinalAge"
        elif x == 4: return "Delay"
        elif x == 5: return "Done"
        else: raise ValueError("invalid Spinup state code")

class LibCBM_Matrix(ctypes.Structure):

    _fields_ = [('rows', ctypes.c_ssize_t),
                ('cols', ctypes.c_ssize_t),
                ('values', ctypes.POINTER(ctypes.c_double))]

    def __init__(self, matrix):
        self.rows = matrix.shape[0]
        self.cols = matrix.shape[1]
        if not matrix.flags["C_CONTIGUOUS"] or not matrix.dtype == np.double:
            raise ValueError("matrix must be c contiguous and of type np.double")
        self.values = matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_double))

class LibCBM_Matrix_Int(ctypes.Structure):

    _fields_ = [('rows', ctypes.c_ssize_t),
                ('cols', ctypes.c_ssize_t),
                ('values', ctypes.POINTER(ctypes.c_int))]

    def __init__(self, matrix):
        self.rows = matrix.shape[0]
        self.cols = matrix.shape[1]
        if not matrix.flags["C_CONTIGUOUS"] or not matrix.dtype == np.int32:
            raise ValueError("matrix must be c contiguous and of type np.int32")
        self.values = matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_int))

class LibCBM_Table(ctypes.Structure):
    _fields_ = [("table_name", ctypes.c_size_t),
                ("column_names", ctypes.c_char_p),
                ("values", LibCBM_Matrix)]

    def __init__(self, table_name, col_names, matrix):
        pass

class LibCBM_Error(ctypes.Structure):
    _fields_ = [("Error", ctypes.c_int),
                ("Message", ctypes.ARRAY(ctypes.c_byte, 1000))]

    def __init__(self):
        setattr(self, "Error", 0)
        setattr(self, "Message", ctypes.ARRAY(ctypes.c_byte, 1000)())

    def getError(self):
        code = getattr(self, "Error")
        return code

    def getErrorMessage(self):
        msg = ctypes.cast(getattr(self, "Message"), ctypes.c_char_p).value
        return msg

class LibCBMWrapper(object):
    def __init__(self, dllpath):
        self.handle = False
        self._dll = ctypes.CDLL(dllpath)
        self.err = LibCBM_Error();

        self._dll.LibCBM_Free.argtypes = (
            ctypes.POINTER(LibCBM_Error), # error struct
            ctypes.c_void_p # handle pointer
        )

        self._dll.LibCBM_Initialize.argtypes = (
            ctypes.POINTER(LibCBM_Error), # error struct
            ctypes.c_char_p # config json string
        )

        self._dll.LibCBM_AdvanceSpinupState.argtypes = (
            ctypes.POINTER(LibCBM_Error), # error struct
            ctypes.c_void_p, #handle
            ctypes.c_size_t, #n stands
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #return interval (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #minRotations (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #maxRotations (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #final age (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #delay (length n)
            ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"), #slowpools (length n)
            ndpointer(ctypes.c_uint, flags="C_CONTIGUOUS"), #spinup state code (length n) (return value)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #Rotation num (length n)(return value)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #simulation step (length n)(return value)
            ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"), #last rotation slow (length n)(return value)
        )

        self._dll.LibCBM_ComputePools.argtypes = (
                ctypes.POINTER(LibCBM_Error), # error struct
                ctypes.c_void_p, #handle
                ctypes.POINTER(ctypes.c_size_t), #op ids
                ctypes.c_size_t, #number of op ids
                LibCBM_Matrix #pools
            )

        self._dll.LibCBM_GetMerchVolumeGrowthAndDeclineOps.argtypes = (
            ctypes.POINTER(LibCBM_Error), # error struct
            ctypes.c_void_p, #handle
            ctypes.ARRAY(ctypes.c_size_t,2), #op_ids (returned value)
            ctypes.c_size_t, #n stands
            LibCBM_Matrix_Int, #classifiers
            LibCBM_Matrix, #pools
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #stand ages (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #spatial unit id (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), # last disturbance type (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), # time since last disturbance
            ndpointer(ctypes.c_double, flags="C_CONTIGUOUS") #growth multiplier
            )

        self._dll.LibCBM_GetTurnoverOps.argtypes = (
            ctypes.POINTER(LibCBM_Error), # error struct
            ctypes.c_void_p, #handle
            ctypes.ARRAY(ctypes.c_size_t,2), #op_ids (returned value))
            ctypes.c_size_t, #n stands
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS")) #spatial unit id (length n)

        self._dll.LibCBM_GetDecayOps.argtypes = (
            ctypes.POINTER(LibCBM_Error), # error struct
            ctypes.c_void_p, #handle
            ctypes.ARRAY(ctypes.c_size_t,3), #op_ids (returned value))
            ctypes.c_size_t, #n stands
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #spatial unit id (length n)
            ctypes.POINTER(ctypes.c_double), #mean annual temp, not using ndpointer becuase we are allowing null
            ctypes.c_bool #use mean annual temp 
            )

        self._dll.LibCBM_GetDisturbanceOps.argtypes = (
            ctypes.POINTER(LibCBM_Error), # error struct
            ctypes.c_void_p, #handle
            ctypes.ARRAY(ctypes.c_size_t,1), #op_ids (returned value))
            ctypes.c_size_t, #n stands
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS"), #spatial unit id (length n)
            ndpointer(ctypes.c_int, flags="C_CONTIGUOUS") #disturbance type id
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.handle:
            err = LibCBM_Error()
            self._dll.LibCBM_Free(ctypes.byref(err), self.handle)
            if err.Error != 0:
                raise RuntimeError(err.getErrorMessage())

    def Initialize(self, config):

        p_config = ctypes.c_char_p(config.encode("UTF-8"));

        self.handle = self._dll.LibCBM_Initialize(
            ctypes.byref(self.err), #error struct
            p_config
            )

        if self.err.Error != 0:
            raise RuntimeError(self.err.getErrorMessage())

    def AdvanceSpinupState(self, returnInterval, minRotations, maxRotations,
                           finalAge, delay, slowPools, state, rotation, step,
                           lastRotationSlowC):
       if not self.handle:
           raise AssertionError("dll not initialized")
       n = returnInterval.shape[0]

       self._dll.LibCBM_AdvanceSpinupState(
            ctypes.byref(self.err),
            self.handle,
            n,
            returnInterval,
            minRotations,
            maxRotations,
            finalAge,
            delay,
            slowPools,
            state,
            rotation,
            step,
            lastRotationSlowC)
        

       if self.err.Error != 0:
           raise RuntimeError(self.err.getErrorMessage())

    def ComputePools(self, ops, pools):

       if not self.handle:
           raise AssertionError("dll not initialized")

       n_ops = len(ops)
       poolMat = LibCBM_Matrix(pools)
       ops_p = ctypes.cast((ctypes.c_size_t*n_ops)(*ops), ctypes.POINTER(ctypes.c_size_t))
       
       self._dll.LibCBM_ComputePools(
            ctypes.byref(self.err),
            self.handle,
            ops_p,
            n_ops,
            poolMat)

       if self.err.Error != 0:
           raise RuntimeError(self.err.getErrorMessage())

    def GetMerchVolumeGrowthAndDeclineOps(self,
        classifiers, pools, ages, spatial_units, last_dist_type,
        time_since_last_dist, growth_multipliers):

       if not self.handle:
           raise AssertionError("dll not initialized")
       n = pools.shape[0]
       poolMat = LibCBM_Matrix(pools)
       classifiersMat = LibCBM_Matrix_Int(classifiers)
       opIds = (ctypes.c_size_t * (2))(*[0,0])
       self._dll.LibCBM_GetMerchVolumeGrowthAndDeclineOps(
           ctypes.byref(self.err),
           self.handle,
           opIds,
           n,
           classifiersMat, poolMat,
           ages,
           spatial_units,
           last_dist_type,
           time_since_last_dist,
           growth_multipliers)

       if self.err.Error != 0:
           raise RuntimeError(self.err.getErrorMessage())

       return [
           {"id": opIds[0], "name": "Growth"},
           {"id": opIds[1], "name": "OvermatureDecline"}
           ]

    def GetTurnoverOps(self, spatial_units):
        if not self.handle:
           raise AssertionError("dll not initialized")

        n = spatial_units.shape[0]
        opIds = (ctypes.c_size_t * (2))(*[0,0])

        self._dll.LibCBM_GetTurnoverOps(
           ctypes.byref(self.err),
           self.handle,
           opIds,
           n,
           spatial_units)

        if self.err.Error != 0:
           raise RuntimeError(self.err.getErrorMessage())

        return {
           opIds[0]: "BiomassTurnover",
           opIds[1]: "SnagTurnover"
           }

    def GetDecayOps(self, spatial_units, mean_annual_temp=None):
        if not self.handle:
           raise AssertionError("dll not initialized")
        n = spatial_units.shape[0]
        opIds = (ctypes.c_size_t * (3))(*[0,0,0])
        self._dll.LibCBM_GetDecayOps(
           ctypes.byref(self.err),
           self.handle,
           opIds,
           n,
           spatial_units,
           None if mean_annual_temp is None else #null pointer if no mean annual temp specified
                mean_annual_temp.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
           False if mean_annual_temp is None else True)

        if self.err.Error != 0:
           raise RuntimeError(self.err.getErrorMessage())

        return {
           opIds[0]: "DomDecay",
           opIds[1]: "SlowDecay",
           opIds[2]: "SlowMixing",
           }

    def GetDisturbanceOps(self, spatial_units, disturbance_types):
        if not self.handle:
           raise AssertionError("dll not initialized")
        n = spatial_units.shape[0]
        opIds = (ctypes.c_size_t * (1))(*[0])
        
        self._dll.LibCBM_GetDisturbanceOps(ctypes.byref(self.err),
           self.handle,
           opIds,
           n,
           spatial_units,
           disturbance_types)

        if self.err.Error != 0:
           raise RuntimeError(self.err.getErrorMessage())
        return {
           opIds[0]: "Disturbance"
           }
