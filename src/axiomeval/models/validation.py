"""Small domain invariants, independent of YAML and the command line."""
from axiomeval.errors import ValidationError


def text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a nonempty string")
    return value.strip()


def tools(value: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValidationError("tools must be a tuple of strings")
    normalized = tuple(text(item, "tool") for item in value)
    if len(set(normalized)) != len(normalized):
        raise ValidationError("tools must not contain duplicates")
    return tuple(sorted(normalized))
