class Ansi:
    _styles = {
        "normal"    : "\033[0",
        "bold"      : "\033[1",
    }

    _colours = {
        "red"       : ";31m",
        "green"     : ";32m",
        "yellow"    : ";33m",
        "blue"      : ";34m",
        "reset"     : "m"
    }

    @classmethod
    def style_str(cls, text, colour, style="normal"):
        return cls._styles[style] + \
            cls._colours[colour] + \
            text + \
            cls._styles["normal"] + \
            cls._colours['reset']


if __name__ == "__main__":
    # Print styled text
    print(Ansi.style_str("Normal red text", "red"))
    print(Ansi.style_str("Bold green text.", "green", "bold"))
    print(Ansi.style_str("Normal yellow text.", "yellow", "normal"))

# colour = {
#     "yellow-bold": "\033[1;33m",
#     "red-bold": "\033[1;31m",
#     "end": "\033[0m"
# }

# import json
#
# # Load the ANSI escape codes from the JSON file
# with open('file.json', 'r') as file:
#     colors = json.load(file)
#
# # Example usage of the ANSI escape codes
# def styled_text(text, color):
#     return f"{colors[color]}{text}{colors['reset']}"
#
# # Print styled text
# print(styled_text("Hello, World!", "red"))
# print(styled_text("This is green text.", "green"))
# print(styled_text("This is blue text.", "blue"))
