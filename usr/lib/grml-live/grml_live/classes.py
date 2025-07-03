# FAI-style classes layout support

from pathlib import Path


class ClassFileParsingFailed(Exception):
    pass


def parse_class_varfile(varfile: Path) -> dict:
    env = {}
    lines = varfile.read_text().splitlines()
    for lineno, orig_line in enumerate(lines):
        # strip off comments
        line = orig_line.split("#", 1)
        if len(line) == 2:
            line = line[0].rstrip()
        elif line[0] == "":
            line = ""
        else:
            line = line[0]

        if not line:
            continue

        line = line.split("=", 1)
        if len(line) == 2:
            k, v = line
            v = v.lstrip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]

            k = k.rstrip()
            if not k.startswith(" "):
                # TODO: should instead check if k starts with alphanumeric (or whatever is allowed)
                env[k] = v
                continue

        print(f"E: Cannot understand line {lineno} in {varfile}: {orig_line}")
        raise ClassFileParsingFailed()

    return env
