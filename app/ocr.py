"""Tag-number normalization."""


def normalize_tag(tag: str) -> str:
    """Strip non-digits, preserve leading zeros."""
    return "".join(c for c in tag if c.isdigit())
