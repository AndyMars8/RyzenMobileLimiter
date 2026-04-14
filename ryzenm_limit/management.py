import sys, os, ctypes


# Sets up RyzenAdj dynamic library
class RyzenAdj:
    def __init__(self, ryzenadj_path):
        self.settings = [
            "tctl_temp",
            "stapm_limit",
            "fast_limit",
            "slow_limit"
        ]
        self.lib = ctypes.CDLL(ryzenadj_path)
        self.ryzenadj = None
        self.__setup()

    def __setup(self):
        self.lib.init_ryzenadj.restype = ctypes.c_void_p

        self.lib.cleanup_ryzenadj.restype = ctypes.c_void_p
        self.lib.cleanup_ryzenadj.argtypes = [ctypes.c_void_p]

        self.lib.refresh_table.argtypes = [ctypes.c_void_p]

        for s in self.settings:
            getattr(self.lib, "get_" + s).restype = ctypes.c_float
            getattr(self.lib, "get_" + s).argtypes = [ctypes.c_void_p]
            getattr(self.lib, "set_" + s).argtypes = [ctypes.c_void_p, ctypes.c_ulong]

        self.ryzenadj = self.lib.init_ryzenadj()

    def cleanup(self):
        return self.lib.cleanup_ryzenadj(self.ryzenadj)

    # PM table requires refresh to retrieve up-to-date values when using get_*
    def refresh_table(self):
        return self.lib.refresh_table(self.ryzenadj)

    def get_limit(self, limit_type):
        return getattr(self.lib, "get_" + limit_type)(self.ryzenadj)

    def set_limit(self, limit_type, val):
        if limit_type == "tctl_temp":
            getattr(self.lib, "set_" + limit_type)(self.ryzenadj, val)
        else:
            getattr(self.lib, "set_" + limit_type)(self.ryzenadj, val * 1000)

    def get_settings(self):
        return self.settings
