import os, fcntl


# Assigns appropriate file paths, power management values, and configuration validation during program runtime
class RuntimeCheck:
    INSTALLED_SRC_PATH = "/usr/local/src/ryzenm-limit"
    INSTALLED_CONFIG_PATH = "/etc/ryzenm-limit/ryzenm-limit.conf"
    INSTALLED_LIB_PATH = "/usr/local/lib/ryzenm-limit/libryzenadj.so"
    INSTALLED_LOG_PATH = "/var/log/ryzenm-limit"

    LOCK_PATH = "/run/lock/ryzenm-limit.lock"

    src_path = os.path.dirname(os.path.abspath(__file__))
    config_path = None
    lib_path = None
    log_path = None

    PROJECT_CONFIG_PATH = os.path.realpath(src_path + "/../config/ryzenm-limit.conf")
    PROJECT_LIB_PATH = os.path.realpath(src_path + "/../lib/libryzenadj.so")
    PROJECT_LOG_PATH = os.path.realpath(src_path + "/../logs")

    config_params = [
        "temp-limit",
        "stapm-limit",
        "fast-limit",
        "slow-limit"
    ]
    _config_content = []
    _valid_params = {}
    _valid_values = {}
    _invalid_lines = set()

    _write_params = {}

    @classmethod
    def check_daemon_status(cls):
        try:
            fd = open(cls.LOCK_PATH, 'r')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fd.close()
            return False    # No lock held, daemon not running
        except FileNotFoundError:
            return False    # No lock file found, daemon not running
        except IOError:
            return True     # Lock held, daemon is running

    @classmethod
    def read_config(cls):
        with open(cls.get_path("config"), 'r') as f:
            for ln, line in enumerate(f):
                cls._config_content.append(line)
                ll = line.strip().split('=')
                if line.startswith('#'): # Ignore comments
                    continue
                elif not line.startswith('#') and len(ll) >= 2:
                    param, value = ll[0], ll[1]
                    if param in cls.config_params:
                        # Identify the first line a valid parameter appears, so that valid if can be rewritten with a valid value if the value is invalid
                        if not param in cls._valid_params:
                            cls._valid_params[param] = ln
                        else:   # Mark duplicate parameters as invalid, so that they can be discarded on next config write operation
                            cls._invalid_lines.add(ln)

                        # Skip check if invalid value is found on a valid paramter
                        if not value.isdigit() and not cls._valid_values.get(param):
                            cls._invalid_lines.add(ln)
                            cls._valid_values[param] = None
                            continue

                        # Add valid value to associated parameter
                        if cls._valid_values.get(param):
                            if cls._valid_values[param] is None:
                                cls._valid_values[param] = value
                        else:
                            cls._valid_values[param] = value
                        cls._invalid_lines.discard(cls._valid_params[param])
                    else:
                        cls._invalid_lines.add(ln)
                else:
                    cls._invalid_lines.add(ln)

    @classmethod
    def config_entry(cls, param, value):
        if param in cls._valid_params:  # Replace existing parameter with modified value
            cls._config_content[cls._valid_params[param]] = f"{param}={value}\n"
            cls._valid_params.pop(param)
        else:   # Add new parameter entry
            cls._write_params[param] = value

    @classmethod
    def finalise_config(cls):
        for param in cls._valid_params: # Prepare to rewrite unmodified parameters
            cls._config_content[cls._valid_params[param]] = f"{param}={cls._valid_values[param]}\n"
        with open(cls.config_path + ".tmp", 'w') as f:
            for ln, line in enumerate(cls._config_content):
                if ln not in cls._invalid_lines:
                    f.write(line)
            for param in cls._write_params:
                f.write(f"{param}={cls._write_params[param]}\n")
        os.rename(cls.config_path + ".tmp", cls.config_path)

    @classmethod
    def get_valid_values(cls):
        cls._valid_values.clear()
        cls.read_config()
        return cls._valid_values

    @classmethod
    def get_config_params(cls):
        return cls.config_params

    @classmethod
    def get_path(cls, path_type):
        if getattr(cls, path_type + "_path") is None:
            path = getattr(cls, "PROJECT_" + path_type.upper() + "_PATH")
            if cls.src_path == cls.INSTALLED_SRC_PATH:
                path = getattr(cls, "INSTALLED_" + path_type.upper() + "_PATH")
            setattr(cls, path_type + "_path", path)

        return getattr(cls, path_type + "_path")
