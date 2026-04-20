'''
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2026 AndyMars8 <https://github.com/AndyMars8>
RyzenMobileLimiter - A simplified power management utility for laptops with AMD Ryzen APU
'''
# This program is the daemon for ryzenm-limit

import fcntl, os, sys, signal, time, shutil, subprocess, logging, atexit
import logging.config
from runtime_check import RuntimeCheck
from management import RyzenAdj


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
            "filters": ["no_stderr"],   # Treat STDOUT and STDERR separately so that warning and error logs aren't duplicated
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
            "filename": RuntimeCheck.get_path("log"),
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
    if not log_path.exists():
        RuntimeCheck.create_file("log")

    logging.config.dictConfig(logging_config)
    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


class DaemonHelper:
    def __init__(self):
        self.lockfile = RuntimeCheck.LOCK_PATH
        self.lock_fd = self.run_once()
        self.config = RuntimeCheck.get_path("config")
        self.settings = {}
        self.last_mtime = os.path.getmtime(self.config)

        self.ryzenadj = None

        self.retrieve_settings()

    # Ensures a single instance of the daemon is running on the system by creating a lock file
    def run_once(self):
        self.lockfile.touch(exist_ok=True)
        self.lockfile.chmod(0o644)
        fd = os.open(str(self.lockfile), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print("Daemon is already running.")
            sys.exit(1)
        return fd

    def init_ryzenadj(self):
        ryzenadj_path = RuntimeCheck.get_path("lib")
        try:
            self.ryzenadj = RyzenAdj(ryzenadj_path)
        except:
            logger.error(f"libryzenadj.so is required for daemon to operate: Could not open {ryzenadj_path}")
            sys.exit(1)

    def cleanup_ryzenadj(self):
        self.ryzenadj.cleanup()

    def monitor(self):
        # Check if config content has changed
        try:
            current_mtime = os.path.getmtime(self.config)
        except FileNotFoundError:
            RuntimeCheck.create_file("config")
            self.last_mtime = os.path.getmtime(self.config)
            return

        if current_mtime != self.last_mtime:
            self.retrieve_settings()
            self.apply_settings()
            self.last_mtime = current_mtime
        time.sleep(1)
        self.ryzenadj.refresh_table()

        # Reapply user limits if a reset has been detected or user has changed settings
        for s in self.settings:
            actual_setting = int(self.ryzenadj.get_limit(s))
            if actual_setting != self.settings[s]:
                logger.info("Reapplying settings for persistence")
                self.apply_settings()
                break

    def apply_settings(self):
        for s in self.settings:
            # Skip setting if it hasn't changed
            try:
                actual_setting = int(self.ryzenadj.get_limit(s))
                if actual_setting == self.settings[s]:
                    continue
            except:
                pass

            # Change setting
            if self.ryzenadj.set_limit(s, self.settings[s]):
                if s == "tctl_temp":
                    logger.error(f"Unsuccessful in setting {s} to {self.settings[s]}°C")
                else:
                    logger.error(f"Unsuccessful in setting {s} to {self.settings[s]}W")
            else:
                if s == "tctl_temp":
                    logger.info(f"Successfully set {s} to {self.settings[s]}°C")
                else:
                    logger.info(f"Successfully set {s} to {self.settings[s]}W")

    def retrieve_settings(self):
        try:
            params = RuntimeCheck.get_valid_values()
            for p in params:
                try:
                    if p == 'temp-limit':
                        self.settings["tctl_temp"] = int(params[p])
                    else:
                        self.settings[p.replace('-', '_')] = int(params[p])
                except:
                    logger.warning(f"Invalid value: {params[p]} detected for {p}")
        except FileNotFoundError:
            RuntimeCheck.create_file("config")


def handle_quit_signal(signum, frame):
    print("\nAttempting to terminate gracefully...")
    logger.info(f"{signal.strsignal(signum)} signal received")
    sys.exit(0)


def start():
    signal.signal(signal.SIGINT, handle_quit_signal)
    signal.signal(signal.SIGTERM, handle_quit_signal)
    signal.signal(signal.SIGHUP, handle_quit_signal)

    if os.geteuid() != 0:
        print("Root privileges are required")
        sys.exit(1)

    logging_setup()
    d = DaemonHelper()

    try:
        # Check if ryzen_smu is loaded
        kmods = subprocess.run(["lsmod"], capture_output=True, text=True, check=True).stdout.split()
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
        if d.ryzenadj is not None:
            d.cleanup_ryzenadj()
        # Remove lock file upon exiting
        fcntl.flock(d.lock_fd, fcntl.LOCK_UN)
        os.close(d.lock_fd)
        os.unlink(str(d.lockfile))

if __name__ == "__main__":
    start()
