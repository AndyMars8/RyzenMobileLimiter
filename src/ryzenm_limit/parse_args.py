# This program parses valid arguments for the daemon to process by writing them to ryzenm-limit.conf
# If daemon isn't active, user would be provided the option to write to config or apply immediately

import argparse, sys, os
from ansi import Ansi
from runtime_check import RuntimeCheck
from management import RyzenAdj


class RemoveMetavars(argparse.HelpFormatter):
    def __init__(self, prog, indent_increment=4, max_help_position=25, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)

    def _format_action_invocation(self, action):
        return f"{', '.join(action.option_strings)}"


class ParseArgs(argparse.ArgumentParser):
    def __init__(self):
        self.daemon_is_active = True
        if not RuntimeCheck.check_daemon_status():
            print(Ansi.style_str("WARNING: Daemon isn't running", "red", "bold"))
            self.daemon_is_active = False

        super().__init__(
            prog="ryzenm-limit",
            add_help=False,
            usage = Ansi.style_str("%(prog)s [options]", "yellow", "bold"),
            description="A simple tool to set power and temperature limits for Ryzen mobile APUs",
            formatter_class=RemoveMetavars,
            exit_on_error=True
        )

        # Setup and organise arguments by groups
        self.info_group = self.__setup_info_group()
        self.temp_group = self.__setup_temp_group()
        self.power_group = self.__setup_power_group()
        self.fine_power_group = self.__setup_fine_power_group()

        self.args = self.parse_args()
        self.ryzenadj = None

        if len(sys.argv) == 1:  # Print help page if no arguments are provided
            self.print_help()
        elif self.args.info:
            self.__print_info()
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
        if self.args.power_limit is not None and not (
            self.args.stapm_limit is None and
            self.args.fast_limit is None and
            self.args.slow_limit is None
        ):
            self.error(
                "argument -p/--power-limit cannot be used with " +
                "-a/--stapm-limit, " +
                "-b/--fast-limit or " +
                "-c/--slow-limit"
            )
        elif self.args.power_limits is not None and not (
            self.args.stapm_limit is None and
            self.args.fast_limit is None and
            self.args.slow_limit is None
        ):
            self.error(
                "argument -q/--power-limits cannot be used with " +
                "-a/--stapm-limit, " +
                "-b/--fast-limit or " +
                "-c/--slow-limit"
            )

    # If user requests to apply settings immediately when daemon isn't active, libryzenadj would be utilised
    # Settings would be written to config regardless of choice
    def __apply_args(self, arg_type, arg_val, apply_immediately):
        if apply_immediately:
            if arg_type == "temp-limit":
                self.ryzenadj.set_limit("tctl_temp", arg_val)
            else:
                self.ryzenadj.set_limit(arg_type.replace('-', '_'), arg_val)
        RuntimeCheck.config_entry(arg_type, arg_val)

    def __write_to_config(self):
        if RuntimeCheck.get_path("src") == RuntimeCheck.INSTALLED_SRC_PATH and os.geteuid() != 0:
            print("Root privileges are required")
            sys.exit(1)

        apply_immediately = False
        # Request user to apply settings immediately is daemon isn't active
        # Values might not persist and the system might change the limits at any given time
        # The config will not reflect those changes made by the system
        if not self.daemon_is_active:
            inp = input("Would you like to apply settings immediately? (y/n): ").lower()
            while not (inp == 'y' or inp == 'n'):
                #if inp != 'y' and inp != 'n':
                if not (inp == 'y' or inp == 'n'):
                    print(f"Invalid input: {inp}")
                    inp = input("Would you like to apply settings immediately? (y/n): ").lower()
            if inp == 'y':
                apply_immediately = True
            if apply_immediately and os.geteuid() != 0:
                print("Root privileges are required")
                sys.exit(1)
            elif apply_immediately and os.geteuid() == 0:
                ryzenadj_path = RuntimeCheck.get_path("lib")
                try:
                    self.ryzenadj = RyzenAdj(ryzenadj_path)
                except:
                    print(f"libryzenadj.so is required to apply these settings: Could not open {ryzenadj_path}")
                    sys.exit(1)

        try:
            RuntimeCheck.read_config()
        except:
            pass

        if self.args.temp_limit is not None:
            print(f"Setting CPU temperature limit to {self.args.temp_limit}°C")
            self.__apply_args("temp-limit", self.args.temp_limit, apply_immediately)

        if self.args.power_limit is not None:
            print(f"Setting CPU power limit to {self.args.power_limit}W")
            for a in RuntimeCheck.get_config_params()[1:]:
                self.__apply_args(a, self.args.power_limit, apply_immediately)
        elif self.args.power_limits is not None:
            print(f"Setting CPU power limits:")
            print(f"\tSTAPM:    {self.args.power_limits[0]}W")
            print(f"\tFAST_PPT: {self.args.power_limits[1]}W")
            print(f"\tSLOW_PPT: {self.args.power_limits[2]}W")
            for i, a in enumerate(RuntimeCheck.get_config_params()[1:]):
                self.__apply_args(a, self.args.power_limits[i], apply_immediately)
        elif self.args.power_limits is None:
            if self.args.stapm_limit is not None:
                print(f"Setting STAPM limit to {self.args.stapm_limit}W")
                self.__apply_args("stapm-limit", self.args.stapm_limit, apply_immediately)
            if self.args.fast_limit is not None:
                print(f"Setting FAST_PPT limit to {self.args.fast_limit}W")
                self.__apply_args("fast-limit", self.args.fast_limit, apply_immediately)
            if self.args.slow_limit is not None:
                print(f"Setting SLOW_PPT limit to {self.args.slow_limit}W")
                self.__apply_args("slow-limit", self.args.slow_limit, apply_immediately)

        RuntimeCheck.finalise_config()

        if not self.daemon_is_active and apply_immediately == 'n':
            print(Ansi.style_str("Please enable daemon to apply settings", "red", "bold"))

    def __print_info(self):
        try:
            with open("/proc/cpuinfo", 'r') as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu = line.split(':')[1].strip()
                        print("CPU:", cpu, end="\n\n")
                        break
        except:
            print("Can't retrieve CPU model")

        try:
            config = RuntimeCheck.get_valid_values()
        except:
            print("Config not found")
            sys.exit(1)

        if os.geteuid() == 0:
            ryzenadj_path = RuntimeCheck.get_path("lib")
            try:
                self.ryzenadj = RyzenAdj(ryzenadj_path)
            except:
                print(f"libryzenadj.so is required to read actual CPU limits: Could not open {ryzenadj_path}")
                sys.exit(1)

            self.ryzenadj.refresh_table()

            print("\t\t\t---------------------------------")
            print(f"\t\t\t| {Ansi.style_str('Config', 'reset', 'bold')}\t| {Ansi.style_str('Actual', 'reset', 'bold')}\t|")
            for param in RuntimeCheck.get_config_params():
                if param in config:
                    print("\t-------------------------------------------------")
                    print(f"\t| {Ansi.style_str(param, 'reset', 'bold')}\t| {config[param]}", end='')
                    if param == "temp-limit":
                        print(f"°C\t\t| {int(self.ryzenadj.get_limit('tctl_temp'))}°C\t\t|")
                    else:
                        print(f"W\t\t| {int(self.ryzenadj.get_limit(param.replace('-', '_')))}W\t\t|")
            print("\t-------------------------------------------------\n")
        else:
            print(Ansi.style_str("*These values are extrapolated from configuration and may not be reflective of applied values", "reset", "bold"))
            for param in RuntimeCheck.get_config_params():
                if param in config:
                    print("\t-------------------------")
                    print(f"\t| {Ansi.style_str(param, 'reset', 'bold')}\t| {config[param]}", end='')
                    if param == "temp-limit":
                        print("°C\t|")
                    else:
                        print("W\t|")
            print("\t-------------------------\n")


if __name__ == "__main__":
    ParseArgs()
