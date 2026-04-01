# This program is the daemon for ryzenm-limit

import fcntl, os, sys, signal, time, shutil, subprocess, ctypes, logging, atexit
import logging.config
from parse_args import RuntimeCheck


def get_log_path():
    src_path = RuntimeCheck.get_src_path()
    log_path = src_path + "/../logs"
    if src_path == RuntimeCheck.INSTALLED_SRC_PATH:
        log_path = "/var/log/ryzenm-limit"
    return log_path


class NoStderrFilter(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.WARNING


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
    "filters": {
        "no_stderr": {
            "()": NoStderrFilter
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "filters": ["no_stderr"],
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
            "filename": f"{get_log_path()}/ryzenm-limit.log",
            "maxBytes": 1000000,
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
    log_path = logging_config["handlers"]["file"]["filename"]
    if log_path == "/var/log/ryzenm-limit/ryzenm-limit.log":
        os.makedirs("/var/log/ryzenm-limit", exist_ok=True)
    else:
        os.makedirs(RuntimeCheck.get_src_path() + "/../logs", exist_ok=True)

    logging.config.dictConfig(logging_config)
    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


class DaemonHelper:
    def __init__(self):
        self.src_path = RuntimeCheck.get_src_path()
        self.lockfile = RuntimeCheck.LOCK_PATH
        self.lock_fd = self.run_once(self.lockfile)
        self.settings = {}
        self.last_mtime = 0

        self.ryzenadj = None
        self.lib = None

        self.retrieve_settings()

    # Ensures a single instance of the daemon is running on the system by creating a lock file
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
        ryzenadj_path = self.src_path + "/../lib/libryzenadj.so"
        if self.src_path == RuntimeCheck.INSTALLED_SRC_PATH:
            ryzenadj_path = "/usr/local/lib/ryzenm-limit/libryzenadj.so"
        try:
            self.lib = ctypes.cdll.LoadLibrary(ryzenadj_path)
        except:
            logger.error("libryzenadj.so is required for daemon to operate. Cannot acquire path to libryzenadj.so")
            sys.exit(1)

        # Define ctype mappings for relevant settings
        config_params = RuntimeCheck.get_config_params()

        self.lib.init_ryzenadj.restype = ctypes.c_void_p
        self.lib.refresh_table.argtypes = [ctypes.c_void_p]

        self.lib.get_tctl_temp.restype = ctypes.c_float
        self.lib.get_tctl_temp.argtypes = [ctypes.c_void_p]
        self.lib.set_tctl_temp.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

        for i in range(1, len(config_params)):
            param = config_params[i].replace('-', '_')
            getattr(self.lib, "get_" + param).restype = ctypes.c_float
            getattr(self.lib, "get_" + param).argtypes = [ctypes.c_void_p]
            getattr(self.lib, "set_" + param).argtypes = [ctypes.c_void_p, ctypes.c_ulong]

        self.ryzenadj = self.lib.init_ryzenadj()

    def cleanup_ryzenadj(self):
        self.lib.cleanup_ryzenadj.restype = ctypes.c_void_p
        self.lib.cleanup_ryzenadj.argtypes = [ctypes.c_void_p]
        self.lib.cleanup_ryzenadj(self.ryzenadj)

    def monitor(self):
        # Check if config content has changed
        current_mtime = os.path.getmtime(RuntimeCheck.get_config_path())
        if current_mtime != self.last_mtime:
            self.retrieve_settings()
            self.apply_settings()
            self.last_mtime = current_mtime
        time.sleep(1)
        self.lib.refresh_table(self.ryzenadj)

        # Reapply user limits if a reset has been detected or user has changed settings
        for s in self.settings:
            actual_setting = int(getattr(self.lib, "get_" + s)(self.ryzenadj))
            if (s == "tctl_temp" and actual_setting != self.settings[s]) or (
                s != "tctl_temp" and actual_setting != self.settings[s] // 1000):
                logger.info("Reapplying settings for persistence")
                self.apply_settings()
                break
        time.sleep(1)

    def apply_settings(self):
        for s in self.settings:
            # Skip setting if it hasn't changed
            try:
                actual_setting = int(getattr(self.lib, "get_" + s)(self.ryzenadj))
                if (s == "tctl_temp" and actual_setting == self.settings[s]) or (
                    s != "tctl_temp" and actual_setting == self.settings[s] // 1000):
                    continue
            except:
                pass

            # Change setting
            if getattr(self.lib, "set_" + s)(self.ryzenadj, self.settings[s]):
                if s == "tctl_temp":
                    logger.error(f"Unsuccessful in setting {s} to {self.settings[s]}°C")
                else:
                    logger.error(f"Unsuccessful in setting {s} to {self.settings[s] // 1000}W")
            else:
                if s == "tctl_temp":
                    logger.info(f"Successfully set {s} to {self.settings[s]}°C")
                else:
                    logger.info(f"Successfully set {s} to {self.settings[s] // 1000}W")

    def retrieve_settings(self):
        params = RuntimeCheck.get_valid_values()
        for p in params:
            try:
                if p == 'temp-limit':
                    self.settings["tctl_temp"] = int(params[p])
                else:
                    self.settings[p.replace('-', '_')] = int(params[p]) * 1000  # Convert W to mW
            except:
                logger.warning(f"Invalid value: {params[p]} detected for {p}")


def handle_quit_signal(signum, frame):
    print("\nAttempting to terminate gracefully...")
    logger.info(f"{signal.strsignal(signum)} signal received")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_quit_signal)
    signal.signal(signal.SIGTERM, handle_quit_signal)
    signal.signal(signal.SIGHUP, handle_quit_signal)

    if os.geteuid() != 0:
        print("Root privileges are required")
        sys.exit(1)

    d = DaemonHelper()

    try:
        logging_setup()

        # Check if ryzen_smu is loaded
        kmods = subprocess.Popen(["lsmod"], stdout=subprocess.PIPE).communicate()[0].decode("utf-8").split()
        if not "ryzen_smu" in kmods:
            logger.warning("ryzen_smu not loaded")
            # Fallback to /dev/mem
            kparams = None
            with open('/proc/cmdline', 'r') as f:
                kparams = f.read().strip()
            if not "iomem=relaxed" in kparams:
                logger.error("Cannot utilise /dev/mem")
                sys.exit(1)

        d.init_ryzenadj()
        logger.info("Started RyzenMobileLimiter daemon")
        while True:
            time.sleep(1)
            d.monitor()
    except SystemExit as e:
        logger.info(f"Daemon exited with status: {e}")
    finally:
        d.cleanup_ryzenadj()
        # Remove lock file upon exiting
        fcntl.flock(d.lock_fd, fcntl.LOCK_UN)
        os.close(d.lock_fd)
        os.unlink(d.lockfile)
