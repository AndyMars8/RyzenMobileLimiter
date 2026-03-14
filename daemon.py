# This program is the daemon for ryzenm-limit

import fcntl, os, sys, signal, time, shutil, subprocess, ctypes, logging, atexit
import logging.config
from parse_args import RuntimeCheck


logger = logging.getLogger("ryzenm-limit")
logging_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "simple": {
            "format": "[%(levelname)s] %(asctime)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "simple",
            "stream": "ext://sys.stderr"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": "logs/ryzenm-limit.log",
            "maxBytes": 200000,
            "backupCount": 2
        },
        "queue_handler": {
            "class": "logging.handlers.QueueHandler",
            "handlers": [
                "stdout",
                "stderr",
                "file"
            ],
            "respect_handler_level": True
        }
    },
    "loggers": {
        "ryzenm-limit": {
            "level": "DEBUG",
            "handlers": [
                "queue_handler"
            ]
        }
    }
}


def logging_setup():
    os.makedirs(os.path.dirname(os.path.abspath(__file__)) + "/logs", exist_ok=True)
    logging.config.dictConfig(logging_config)
    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


class DaemonHelper:
    def __init__(self):
        self.lockfile = "/run/lock/ryzenm-limit.lock"
        self.lock_fd = self.run_once(self.lockfile)
        self.settings = {}
        self.last_mtime = 0

        self.ryzenadj = None
        self.lib = None

        self.init_ryzenadj()
        self.retrieve_settings()
        # print("Applying settings at launch")
        # self.apply_settings()

    def run_once(self, lockfile):
        fd = os.open(lockfile, os.O_CREAT | os.O_RDWR)
        os.chmod(lockfile, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print("Daemon is already running.")
            sys.exit(1)
        return fd

    def init_ryzenadj(self):
        ryzenadj_path = os.path.dirname(os.path.abspath(__file__)) + "/libryzenadj.so"
        lib = None
        try:
            lib = ctypes.cdll.LoadLibrary(ryzenadj_path)
        except:
            print("libryzenadj.so is required for daemon to operate. Cannot acquire path to libryzenadj.so")
            sys.exit(1)

        print(ryzenadj_path)

        # Define ctype mappings for relevant settings
        config_params = RuntimeCheck.get_config_params()

        lib.init_ryzenadj.restype = ctypes.c_void_p
        lib.refresh_table.argtypes = [ctypes.c_void_p]

        lib.get_tctl_temp.restype = ctypes.c_float
        lib.get_tctl_temp.argtypes = [ctypes.c_void_p]
        lib.set_tctl_temp.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

        for i in range(1, len(config_params)):
            param = config_params[i].replace('-', '_')
            lib.__getattr__("get_" + param).restype = ctypes.c_float
            lib.__getattr__("get_" + param).argtypes = [ctypes.c_void_p]
            lib.__getattr__("set_" + param).argtypes = [ctypes.c_void_p, ctypes.c_ulong]


        self.lib = lib
        self.ryzenadj = self.lib.init_ryzenadj()

    def monitor(self):
        self.lib.refresh_table(self.ryzenadj)
        if self.lib.get_tctl_temp(self.ryzenadj) != self.settings["tctl_temp"]:    # Reapply user limits if a reset has been detected or user has changed settings
            print("Applying settings for persistence")
            self.apply_settings()
        time.sleep(1)
        # Check if config content has changed
        current_mtime = os.path.getmtime(RuntimeCheck.get_config_path())
        if current_mtime != self.last_mtime:
            self.retrieve_settings()
            print("Applying settings due to config change")
            self.apply_settings()
            self.last_mtime = current_mtime

    def apply_settings(self):
        if "tctl_temp" in self.settings:
            if self.lib.set_tctl_temp(self.ryzenadj, self.settings["tctl_temp"]):
                print(f"Unsuccessful in setting temperature limit to {self.settings["tctl_temp"]}°C")
            else:
                print(f"Successfully set temperature limit to {self.settings["tctl_temp"]}°C")
        if "stapm_limit" in self.settings:
            if self.lib.set_stapm_limit(self.ryzenadj, self.settings["stapm_limit"]):
                print(f"Unsuccessful in setting STAPM limit to {self.settings["stapm_limit"] // 1000}W")
            else:
                print(f"Successfully set STAPM limit to {self.settings["stapm_limit"] // 1000}W")
        if "fast_limit" in self.settings:
            if self.lib.set_fast_limit(self.ryzenadj, self.settings["fast_limit"]):
                print(f"Unsuccessful in setting Fast PPT limit to {self.settings["fast_limit"] // 1000}W")
            else:
                print(f"Successfully set Fast PPT limit to {self.settings["fast_limit"] // 1000}W")
        if "slow_limit" in self.settings:
            if self.lib.set_slow_limit(self.ryzenadj, self.settings["slow_limit"]):
                print(f"Unsuccessful in setting Slow PPT limit to {self.settings["slow_limit"] // 1000}W")
            else:
                print(f"Successfully set Slow PPT limit to {self.settings["slow_limit"] // 1000}W")
        # for s in self.settings:
        #     print(s, self.settings[s], "set_" + s)
        #     name = "set_" + s
        #     func = self.lib.__getattr__(name)
        #     #print(func)
        #     func(self.ryzenadj, self.settings[s])

    def retrieve_settings(self):
        params = RuntimeCheck.get_valid_values()
        for p in params:
            try:
                if p == 'temp-limit':
                    self.settings["tctl_temp"] = int(params[p])
                else:
                    self.settings[p.replace('-', '_')] = int(params[p]) * 1000  # Convert W to mW
            except:
                print(f"Invalid value: {params[p]} detected for {p}")


def handle_quit_signal(signum, frame):
    print(f"\n{signal.strsignal(signum)} signal received. Attempting to terminate gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_quit_signal)
    signal.signal(signal.SIGTERM, handle_quit_signal)

    if os.geteuid() != 0:
        print("Root privileges are required")
        sys.exit(1)

    print(os.getpid())

    d = DaemonHelper()

    try:
        logging_setup()
        logger.info(f"Started RyzenMobileLimiter daemon")
        while True:
            time.sleep(1)
            d.monitor()
    except SystemExit as e:
        print(f"Daemon exited with status: {e}")
    finally:
        fcntl.flock(d.lock_fd, fcntl.LOCK_UN)
        os.close(d.lock_fd)
        os.unlink(d.lockfile)
