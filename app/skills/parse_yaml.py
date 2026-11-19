import yaml


def parse_frontmatter(text: str) -> dict | None:
    """Return the YAML mapping between the first two '---' lines, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for end, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":  # first closing marker only
            raw = "\n".join(lines[1:end])
            break
    else:  # no closing marker
        return None

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def parse_body(text: str) -> str:
    lines = text.splitlines()
    body = text  # default: no frontmatter, or it never closes
    if lines and lines[0].strip() == "---":
        for end, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body = "\n".join(lines[end + 1 :])
                break
    return body.strip()
