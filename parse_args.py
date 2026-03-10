# This program parses valid arguments for the main program to process by writing them to ryzenm-limit.conf

import argparse, sys, os
from ansi import Ansi


class ParseArgs(argparse.ArgumentParser):
    def __init__(self):
        self.daemon_is_active = True
        if not RuntimeCheck.check_daemon_status():
            print(Ansi.style_str("WARNING: Daemon isn't running", "red", "bold"))
            self.daemon_is_active = False

        formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=25)
        super().__init__(
            prog="ryzenm-limit",
            add_help=False,
            usage = Ansi.style_str("%(prog)s [options]", "yellow", "bold"),
            description="A simple tool to set power and temperature limits for Ryzen mobile APUs",
            formatter_class=formatter,
            exit_on_error=True
        )

        # Setup and organise arguments by groups
        self.info_group = self.__setup_info_group()
        self.temp_group = self.__setup_temp_group()
        self.power_group = self.__setup_power_group()
        self.fine_power_group = self.__setup_fine_power_group()

        self.args = self.parse_args()

        if len(sys.argv) == 1:  # Print help page if no arguments are provided
            self.print_help()
        else:
            self.__power_args_exclusion()
            self.__write_to_config()

    def __setup_info_group(self):
        info_group = self.add_argument_group('Options')
        info_group.add_argument(
            '-h',
            '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show this help message and exit'
        )
        info_group.add_argument(
            "-i",
            "--info",
            action='store_true',
            help="Show current CPU metrics"
        )
        return info_group

    def __setup_temp_group(self):
        temp_group = self.add_argument_group('Temperature Limit')
        temp_group.add_argument(
            "-t",
            "--temp-limit",
            type=int,
            help="Set CPU temperature limit (°C)",
            metavar=""
        )
        return temp_group

    def __setup_power_group(self):
        power_group = self.add_argument_group("Power Limit Options").add_mutually_exclusive_group()
        power_group.add_argument(
            "-p",
            "--power-limit",
            type=int,
            help="Set CPU power limit (W)",
            metavar=""
        )
        power_group.add_argument(
            "-q",
            "--power-limits",
            type=int,
            nargs=3,
            help="Set CPU power limits (STAPM FAST_PPT SLOW_PPT)",
            metavar=""
        )
        return power_group

    def __setup_fine_power_group(self):
        fine_power_group = self.add_argument_group('Fine-tuned Power Limit Options')
        fine_power_group.add_argument(
            "-a",
            "--stapm-limit",
            type=int,
            help="Set CPU STAPM limit (W)",
            metavar=""
        )
        fine_power_group.add_argument(
            "-b",
            "--fast-limit",
            type=int,
            help="Set CPU FAST_PPT limit (W)",
            metavar=""
        )
        fine_power_group.add_argument(
            "-c",
            "--slow-limit",
            type=int,
            help="Set CPU SLOW_PPT limit (W)",
            metavar=""
        )
        return fine_power_group

    def __power_args_exclusion(self):
        if self.args.power_limit is not None and (
            self.args.stapm_limit is not None or
            self.args.fast_limit is not None or
            self.args.slow_limit is not None
        ):
            self.error(
                "argument -p/--power-limit cannot be used with " +
                "-a/--stapm-limit, " +
                "-b/--fast-limit or " +
                "-c/--slow-limit"
            )
        elif self.args.power_limits is not None and (
            self.args.stapm_limit is not None or
            self.args.fast_limit is not None or
            self.args.slow_limit is not None
        ):
            self.error(
                "argument -q/--power-limits cannot be used with " +
                "-a/--stapm-limit, " +
                "-b/--fast-limit or " +
                "-c/--slow-limit"
            )

    def __write_to_config(self):
        RuntimeCheck.read_config()

        if self.args.temp_limit is not None:
            print(f"Setting CPU temperature limit to {self.args.temp_limit}°C")
            RuntimeCheck.config_entry("temp-limit", self.args.temp_limit)

        if self.args.power_limit is not None:
            print(f"Setting CPU power limit to {self.args.power_limit}W")
            RuntimeCheck.config_entry("stapm-limit", self.args.power_limit)
            RuntimeCheck.config_entry("fast-limit", self.args.power_limit)
            RuntimeCheck.config_entry("slow-limit", self.args.power_limit)
        elif self.args.power_limits is not None:
            print(f"Setting CPU power limits:")
            print(f"\tSTAPM: \t\t{self.args.power_limits[0]}W")
            print(f"\tFAST_PPT: \t{self.args.power_limits[1]}W")
            print(f"\tSLOW_PPT: \t{self.args.power_limits[2]}W")
            RuntimeCheck.config_entry("stapm-limit", self.args.power_limits[0])
            RuntimeCheck.config_entry("fast-limit", self.args.power_limits[1])
            RuntimeCheck.config_entry("slow-limit", self.args.power_limits[2])
        elif self.args.power_limits is None:
            if self.args.stapm_limit is not None:
                print(f"Setting STAPM limit to {self.args.stapm_limit}W")
                RuntimeCheck.config_entry("stapm-limit", self.args.stapm_limit)
            if self.args.fast_limit is not None:
                print(f"Setting FAST_PPT limit to {self.args.fast_limit}W")
                RuntimeCheck.config_entry("fast-limit", self.args.fast_limit)
            if self.args.slow_limit is not None:
                print(f"Setting SLOW_PPT limit to {self.args.slow_limit}W")
                RuntimeCheck.config_entry("slow-limit", self.args.slow_limit)

        RuntimeCheck.finalise_config()

        if not self.daemon_is_active:
            print(Ansi.style_str("Please enable daemon to apply settings", "red", "bold"))


class RuntimeCheck:
    # Default configuration path at project root
    config_path = os.getcwd() + "/ryzenm-limit.conf"

    config_params = {
            "temp-limit",
            "stapm-limit",
            "fast-limit",
            "slow-limit"
    }
    _config_content = []
    _valid_params = {}
    _valid_values = {}
    _invalid_lines = set()

    _write_params = {}

    def check_daemon_status():
        lock_path = "/run/lock/ryzenm-limit.lock"
        try:
            fd = open(lock_path, 'r')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fd.close()
            return False    # No lock held, daemon not running
        except FileNotFoundError:
            return False    # No lock file found, daemon not running
        except IOError:
            return True     # Lock held, daemon is running

    @classmethod
    def find_config(cls):
        alt_config_path = os.path.expanduser("~/.config/ryzenm-limit/ryzenm-limit.conf")
        if os.path.exists(alt_config_path):
            cls.config_path = alt_config_path
        return cls.config_path

    @classmethod
    def read_config(cls):
        with open(cls.find_config(), 'r') as f:
            for ln, line in enumerate(f):
                cls._config_content.append(line)
                ll = line.strip().split('=')
                if line.startswith('#'): # Ignore empty lines
                    continue
                elif not line.startswith('#') and len(ll) >= 2: # Ignore comments
                    param, value = ll[0], ll[1]
                    if param in cls.config_params:
                        if not param in cls._valid_params:
                            cls._valid_params[param] = ln
                        else:
                            cls._invalid_lines.add(ln)
                        if not value.isdigit():
                            cls._invalid_lines.add(ln)
                            cls._valid_values[param] = None
                            continue
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


if __name__ == "__main__":
    ap = ParseArgs()
