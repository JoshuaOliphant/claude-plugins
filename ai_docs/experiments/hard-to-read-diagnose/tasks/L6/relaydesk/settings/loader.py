"""Layered configuration.

Precedence, lowest to highest:

1. built-in defaults from :mod:`relaydesk.settings.schema`
2. ``config/relaydesk.toml`` (or the file named by ``--config`` /
   ``RELAYDESK_CONFIG``)
3. ``config/relaydesk.local.toml`` next to it, if present (per-machine
   tweaks; see ``relaydesk.local.toml.example``)
4. environment variables listed in the schema
5. explicit command-line overrides

Every layer is flattened to dotted keys before merging so a later layer only
replaces the keys it actually mentions.
"""

from __future__ import annotations

import logging
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import schema
from .coerce import SettingError, coerce

log = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("config") / "relaydesk.toml"
CONFIG_ENV = "RELAYDESK_CONFIG"


@dataclass
class Layer:
    name: str
    values: dict[str, object] = field(default_factory=dict)


def flatten(tree: Mapping[str, object], prefix: str = "") -> dict[str, object]:
    flat: dict[str, object] = {}
    for key, value in tree.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(flatten(value, dotted + "."))
        else:
            flat[dotted] = value
    return flat


def _toml_layer(name: str, path: Path) -> Layer:
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    values = flatten(data)
    unknown = sorted(k for k in values if k not in schema.BY_KEY)
    if unknown:
        raise SettingError(f"{path}: unknown setting(s): {', '.join(unknown)}")
    log.debug("loaded %d value(s) from %s", len(values), path)
    return Layer(name, values)


def local_override_path(config_path: Path) -> Path:
    return config_path.with_name(config_path.stem + ".local" + config_path.suffix)


def defaults_layer() -> Layer:
    return Layer("defaults", {s.key: s.default for s in schema.SETTINGS})


def env_layer(environ: Mapping[str, str]) -> Layer:
    values: dict[str, object] = {}
    for setting in schema.SETTINGS:
        if setting.env and setting.env in environ:
            values[setting.key] = environ[setting.env]
    return Layer("environment", values)


def cli_layer(overrides: Mapping[str, object] | None) -> Layer:
    values = {k: v for k, v in (overrides or {}).items() if v is not None}
    for key in values:
        schema.lookup(key)
    return Layer("command line", values)


class Settings:
    """Read-only view over the merged, coerced configuration."""

    def __init__(self, values: dict[str, object], root: Path, config_path: Path):
        self._values = values
        self.root = root
        self.config_path = config_path

    def get(self, key: str) -> object:
        return self._values[key]

    def path(self, key: str) -> Path:
        value = self._values[key]
        if not isinstance(value, Path):
            raise TypeError(f"{key} is not a path setting")
        return value if value.is_absolute() else self.root / value

    def section(self, name: str) -> dict[str, object]:
        prefix = name + "."
        return {k[len(prefix):]: v for k, v in self._values.items() if k.startswith(prefix)}

    def __getattr__(self, name: str) -> "_Section":
        if name.startswith("_") or name not in schema.SECTIONS:
            raise AttributeError(name)
        return _Section(self.section(name))

    def as_dict(self) -> dict[str, object]:
        return dict(self._values)


class _Section:
    def __init__(self, values: dict[str, object]):
        self.__dict__.update(values)


def resolve_config_path(root: Path, explicit: str | os.PathLike | None,
                        environ: Mapping[str, str]) -> Path:
    candidate = explicit or environ.get(CONFIG_ENV)
    path = Path(candidate) if candidate else DEFAULT_CONFIG
    return path if path.is_absolute() else root / path


def build_layers(root: Path, config_path: Path, environ: Mapping[str, str],
                 overrides: Mapping[str, object] | None) -> list[Layer]:
    layers = [defaults_layer()]
    if config_path.is_file():
        layers.append(_toml_layer("config file", config_path))
    else:
        log.warning("config file %s not found; using defaults", config_path)
    local = local_override_path(config_path)
    if local.is_file():
        layers.append(_toml_layer("local override", local))
    layers.append(env_layer(environ))
    layers.append(cli_layer(overrides))
    return layers


def merge(layers: list[Layer]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for layer in layers:
        for key, raw in layer.values.items():
            setting = schema.lookup(key)
            try:
                merged[key] = coerce(setting, raw)
            except SettingError as exc:
                raise SettingError(f"{exc} (from {layer.name})") from None
    return merged


def load_settings(root: Path, config: str | os.PathLike | None = None,
                  environ: Mapping[str, str] | None = None,
                  overrides: Mapping[str, object] | None = None) -> Settings:
    environ = os.environ if environ is None else environ
    config_path = resolve_config_path(root, config, environ)
    layers = build_layers(root, config_path, environ, overrides)
    return Settings(merge(layers), root, config_path)
