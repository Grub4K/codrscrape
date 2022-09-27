import re

MISSING = object()
_MARKDOWN_LOOKUP = {
    "h1": ("# ", "\n\n"),
    "h2": ("## ", "\n\n"),
    "h3": ("### ", "\n"),
    "h4": ("#### ", "\n"),
    "h5": ("#### ", "\n"),
    "h6": ("#### ", "\n"),
    "li": ("- ", "\n"),
    "b": ("**", "**"),
    "br": ("", "  \n"),
    "p": ("", "\n\n"),
    "strong": ("**", "**"),
    "i": ("*", "*"),
    "em": ("*", "*"),
    "del": ("~~", "~~"),
    "u": ("__", "__"),
}

MD_ESCAPE = str.maketrans({char: Rf"\{char}" for char in "*_~#"})
MULTIPLE_NEWLINE_REGEX = re.compile(r"(?:\r?(\n))?(\r?\n)+\s*")


def convert_md(tag):
    def _convert_md(tag):
        if isinstance(tag, str):
            return tag.translate(MD_ESCAPE).strip()

        inner = "".join(_convert_md(child) for child in tag.children)
        translation = _MARKDOWN_LOOKUP.get(tag.name)
        if translation is None:
            return inner

        return f"{translation[0]}{inner}{translation[1]}"

    return MULTIPLE_NEWLINE_REGEX.sub(r"\g<1>\n", _convert_md(tag)).replace(
        "\r\n", "\n"
    )


def traverse(obj, path, default=None):
    def _traverse(obj, path):
        val = obj
        for key in path:
            if callable(key):
                if isinstance(val, list):
                    iterable = enumerate(val)
                elif isinstance(val, dict):
                    iterable = val.items()
                else:
                    return MISSING

                for a, b in iterable:
                    if key(a, b):
                        val = b
                        break
                else:
                    return MISSING

            elif isinstance(val, dict):
                val = val.get(key, MISSING)

            elif isinstance(val, list):
                try:
                    val = val[key]
                except IndexError:
                    return MISSING

            else:
                return MISSING

            if val is MISSING:
                return MISSING

        return val

    result = _traverse(obj, path)
    return result if result is not MISSING else default


def try_float(data):
    try:
        return float(data)
    except ValueError:
        return None
