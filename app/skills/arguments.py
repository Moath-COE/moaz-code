import re

_PLACEHOLDER = re.compile(r"\$ARGUMENTS\[(\d+)\]|\$ARGUMENTS|\$(\d+)")


def substitute_arguments(body: str, arguments: str) -> str:
    words = arguments.split()

    def replace(match: re.Match) -> str:
        index = match.group(1) or match.group(2)  # [N] form, or $N form
        if index is None:  # plain $ARGUMENTS
            return arguments
        i = int(index)
        return words[i] if i < len(words) else ""

    return _PLACEHOLDER.sub(replace, body)
