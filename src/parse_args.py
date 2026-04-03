# This program parses valid arguments for the daemon to process by writing them to ryzenm-limit.conf

import argparse, sys, os
from ansi import Ansi
from runtime_check import RuntimeCheck


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
        if RuntimeCheck.get_src_path() == RuntimeCheck.INSTALLED_SRC_PATH and os.geteuid() != 0:
            print("Root privileges are required")
            sys.exit(1)

        try:
            RuntimeCheck.read_config()
        except:
            pass

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
            print(f"\tSTAPM:    {self.args.power_limits[0]}W")
            print(f"\tFAST_PPT: {self.args.power_limits[1]}W")
            print(f"\tSLOW_PPT: {self.args.power_limits[2]}W")
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

        print(Ansi.style_str("*These values are extrapolated from configuration and may not be reflective of applied values", "reset", "bold"))

        RuntimeCheck.read_config()
        config = RuntimeCheck._valid_values
        for param in RuntimeCheck.config_params:
            if param in config:
                print("\t-------------------------")
                print(f"\t| {Ansi.style_str(param, 'reset', 'bold')}\t| {config[param]}", end='')
                if param == "temp-limit":
                    print("°C\t|")
                else:
                    print("W\t|")
        print("\t-------------------------\n")


if __name__ == "__main__":
    ap = ParseArgs()
