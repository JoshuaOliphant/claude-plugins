"""Loading of the bundled report templates."""

from __future__ import annotations

import os
from functools import lru_cache
from string import Template

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")


class TemplateNotFound(LookupError):
    pass


@lru_cache(maxsize=None)
def load_templates(directory: str = TEMPLATE_DIR) -> dict[str, Template]:
    templates: dict[str, Template] = {}
    with os.scandir(directory) as it:
        entries = sorted(it, key=lambda e: e.name)
    for entry in entries:
        if not entry.is_file() or not entry.name.endswith(".tmpl"):
            continue
        name = entry.name[: -len(".tmpl")]
        with open(entry.path, encoding="utf-8") as fh:
            templates[name] = Template(fh.read())
    return templates


def get_template(name: str, directory: str = TEMPLATE_DIR) -> Template:
    try:
        return load_templates(directory)[name]
    except KeyError:
        raise TemplateNotFound(f"no template named {name!r} in {directory}") from None


def render(name: str, **values) -> str:
    return get_template(name).safe_substitute(**values)
