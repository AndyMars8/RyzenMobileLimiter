import sys, os, fcntl, ctypes, time

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
        self.setup()

    def setup(self):
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

    def refresh_table(self):
        return self.lib.refresh_table(self.ryzenadj)

    def get_tctl_temp(self):
        return self.lib.get_tctl_temp(self.ryzenadj)

    def set_tctl_temp(self, val):
        self.lib.set_tctl_temp(self.ryzenadj, val)

    def get_stapm_limit(self):
        return self.lib.get_stapm_limit(self.ryzenadj)

    def set_stapm_limit(self, val):
        self.lib.set_stapm_limit(self.ryzenadj, val * 1000)

    def get_fast_limit(self):
        return self.lib.get_fast_limit(self.ryzenadj)

    def set_fast_limit(self, val):
        self.lib.set_fast_limit(self.ryzenadj, val * 1000)

    def get_slow_limit(self):
        return self.lib.get_slow_limit(self.ryzenadj)

    def set_slow_limit(self, val):
        self.lib.set_slow_limit(self.ryzenadj, val * 1000)

    def get_settings(self):
        return self.settings
