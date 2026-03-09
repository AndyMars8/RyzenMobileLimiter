# This program parses valid arguments for the main program to process by writing them to ryzenm-limit.conf

import argparse, sys, ansi


class ParseArgs(argparse.ArgumentParser):
    def __init__(self):
        formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=25)
        super().__init__(
            prog="ryzenm-limit",
            add_help=False,
            usage="{}%(prog)s [options]{}".format(ansi.colour["yellow"], ansi.colour["end"]),
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

        if len(sys.argv) == 1:  # No arguments provided
            self.print_help()

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
        if args.power_limit is not None and (
            args.stapm_limit is not None or
            args.fast_limit is not None or
            args.slow_limit is not None
        ):
            parser.error(
                "argument -p/--power-limit cannot be used with " +
                "-a/--stapm-limit, " +
                "-b/--fast-limit or " +
                "-c/--slow-limit"
            )
        elif args.power_limits is not None and (
            args.stapm_limit is not None or
            args.fast_limit is not None or
            args.slow_limit is not None
        ):
            parser.error(
                "argument -q/--power-limits cannot be used with " +
                "-a/--stapm-limit, " +
                "-b/--fast-limit or " +
                "-c/--slow-limit"
            )


if __name__ == "__main__":
    ap = ParseArgs()
