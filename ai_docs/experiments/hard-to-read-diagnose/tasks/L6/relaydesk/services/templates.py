"""Message templates.

Templates are plain ``string.Template`` files named ``<name>.txt`` in the
templates directory.  A file with the same name under ``templates/overrides``
takes precedence, which lets a deployment reword a message without touching
the stock copy.  The first line of a template is the title, the rest is the
body.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import Template


class TemplateNotFound(LookupError):
    pass


@dataclass(frozen=True)
class MessageTemplate:
    name: str
    source: Path
    title: Template
    body: Template

    def render(self, fields: dict[str, str]) -> tuple[str, str]:
        return self.title.safe_substitute(fields), self.body.safe_substitute(fields).strip()


class TemplateStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self._cache: dict[str, MessageTemplate] = {}

    def search_path(self) -> list[Path]:
        return [self.directory / "overrides", self.directory]

    def _locate(self, name: str) -> Path:
        for folder in self.search_path():
            candidate = folder / f"{name}.txt"
            if candidate.is_file():
                return candidate
        raise TemplateNotFound(f"no template named {name!r} in {self.directory}")

    def get(self, name: str) -> MessageTemplate:
        if name not in self._cache:
            path = self._locate(name)
            text = path.read_text(encoding="utf-8")
            title, _, body = text.partition("\n")
            self._cache[name] = MessageTemplate(name, path, Template(title.strip()),
                                                Template(body))
        return self._cache[name]

    def available(self) -> list[str]:
        names: set[str] = set()
        for folder in self.search_path():
            if folder.is_dir():
                names.update(p.stem for p in folder.glob("*.txt"))
        return sorted(names)
