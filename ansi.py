# Provides ANSI styling for strings

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
