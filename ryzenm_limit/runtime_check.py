import os, sys, fcntl, re
from pathlib import Path


# Assigns appropriate file paths, power management values, and configuration validation during program runtime
class RuntimeCheck:
    _home_dir = Path.home()
    _user = os.environ.get('SUDO_USER')
    if _user:   # Acquire home directory under non-root user
        _home_dir = Path(f'~{_user}').expanduser()
    elif re.search("/home/.*/.*", sys.prefix):  # Acquire home directory under Python environment in non-root home directory
        _home_dir = Path('/'.join(sys.prefix.split('/')[1:3]))

    src_path = Path(__file__).parent
    config_path = None
    lib_path = None
    log_path = None

    LOCK_PATH = Path("/run/lock/ryzenm-limit.lock")

    INSTALLED_SRC_PATH = Path("/usr/local/src/ryzenm-limit")
    INSTALLED_CONFIG_PATH = Path("/etc/ryzenm-limit/ryzenm-limit.conf")
    INSTALLED_LIB_PATH = Path("/usr/local/lib/ryzenm-limit/libryzenadj.so")
    INSTALLED_LOG_PATH = Path("/var/log/ryzenm-limit/ryzenm-limit.log")

    PROJECT_CONFIG_PATH = (src_path / "../config/ryzenm-limit.conf").resolve()
    PROJECT_LIB_PATH = (src_path / "libryzenadj.so").resolve()
    PROJECT_LOG_PATH = (src_path / "../logs/ryzenm-limit.log").resolve()

    USER_HOME_CONFIG_PATH = _home_dir / ".ryzenm-limit/config/ryzenm-limit.conf"
    USER_HOME_LIB_PATH = PROJECT_LIB_PATH
    USER_HOME_LOG_PATH = _home_dir / ".ryzenm-limit/log/ryzenm-limit.log"

    OPT_SRC_PATH = Path("/opt/ryzenm-limit/src")
    OPT_CONFIG_PATH = Path("/etc/opt/ryzenm-limit/ryzenm-limit.conf")
    OPT_LIB_PATH = Path("/opt/ryzenm-limit/lib/libryzenadj.so")
    OPT_LOG_PATH = Path("/var/opt/ryzenm-limit/log/ryzenm-limit.log")

    SYSTEM_PKG_SRC_PATH_PATTERN = "/usr/.*lib.*/python3.*/site-packages"
    HOME_PKG_SRC_PATH_PATTERN = "/home/.*lib.*/python3.*/site-packages"
    OPT_PKG_SRC_PATH_PATTERN = "/opt/.*lib.*/python3.*/site-packages"

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

    # Check is daemon is running
    @classmethod
    def check_daemon_status(cls):
        try:
            fd = cls.LOCK_PATH.open('r')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fd.close()
            return False    # No lock held, daemon not running
        except FileNotFoundError:
            return False    # No lock file found, daemon not running
        except IOError:
            return True     # Lock held, daemon is running

    @classmethod
    def read_config(cls):
        with cls.get_path("config").open('r') as f:
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

    # Prepare valid parameters for config
    @classmethod
    def config_entry(cls, param, value):
        if param in cls._valid_params:  # Replace existing parameter with modified value
            cls._config_content[cls._valid_params[param]] = f"{param}={value}\n"
            cls._valid_params.pop(param)
        else:   # Add new parameter entry
            cls._write_params[param] = value

    # Write all valid lines to config
    @classmethod
    def finalise_config(cls):
        for param in cls._valid_params: # Prepare to rewrite unmodified parameters
            cls._config_content[cls._valid_params[param]] = f"{param}={cls._valid_values[param]}\n"

        temp_config = cls.config_path.with_suffix(cls.config_path.suffix + ".tmp")
        with temp_config.open('w') as f:
            for ln, line in enumerate(cls._config_content):
                if ln not in cls._invalid_lines:
                    f.write(line)
            for param in cls._write_params:
                f.write(f"{param}={cls._write_params[param]}\n")
        temp_config.rename(cls.config_path)

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
            if cls.src_path == cls.INSTALLED_SRC_PATH or re.search(cls.SYSTEM_PKG_SRC_PATH_PATTERN, str(cls.src_path)):
                path = getattr(cls, "INSTALLED_" + path_type.upper() + "_PATH")
            elif re.search(cls.HOME_PKG_SRC_PATH_PATTERN, str(cls.src_path)):
                path = getattr(cls, "USER_HOME_" + path_type.upper() + "_PATH")
            elif cls.src_path == cls.OPT_SRC_PATH or re.search(cls.OPT_PKG_SRC_PATH_PATTERN, str(cls.src_path)):
                if cls.src_path == cls.OPT_SRC_PATH and path_type == "lib":
                    path = cls.PROJECT_LIB_PATH
                else:
                    path = getattr(cls, "OPT_" + path_type.upper() + "_PATH")
            setattr(cls, path_type + "_path", path)

        return getattr(cls, path_type + "_path")

    @classmethod
    def create_file(cls, file_type):
        file_path = cls.get_path(file_type)
        file_dir = file_path.parent
        os.makedirs(file_dir, exist_ok=True)
        file_path.touch(exist_ok=True)
        # Non-root user owns file if source is not in user's home directory
        if ('SUDO_UID' and 'SUDO_GID') in os.environ and file_dir.is_relative_to(cls._home_dir):
            uid, gid = int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID'])
            os.chown(file_dir, uid, gid)
            os.chown(file_path, uid, gid)
