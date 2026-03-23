from slugify import slugify as _slugify


def generate_slug(text: str) -> str:
    return _slugify(text, separator="-", lowercase=True)
