"""A small service container.

Services are registered as factories and built on first use. A factory
receives the container so it can resolve its own dependencies, which keeps
wiring in one place (see :mod:`stockflow.bootstrap`) and lets tests swap a
single service without rebuilding the rest.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict

from stockflow.domain.errors import UnknownServiceError

Factory = Callable[["ServiceContainer"], Any]


class ServiceContainer:
    def __init__(self) -> None:
        self._factories: Dict[str, Factory] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def register(self, name: str, factory: Factory) -> None:
        with self._lock:
            self._factories[name] = factory
            self._instances.pop(name, None)

    def register_instance(self, name: str, instance: Any) -> None:
        with self._lock:
            self._factories[name] = lambda _c: instance
            self._instances[name] = instance

    def has(self, name: str) -> bool:
        return name in self._factories

    def is_built(self, name: str) -> bool:
        return name in self._instances

    def get(self, name: str) -> Any:
        instance = self._instances.get(name)
        if instance is not None:
            return instance
        factory = self._factories.get(name)
        if factory is None:
            raise UnknownServiceError(name)
        # Factories resolve their own dependencies through get(), so the
        # lock is only taken to publish the finished instance.
        instance = factory(self)
        with self._lock:
            self._instances[name] = instance
        return instance

    def reset(self, name: str | None = None) -> None:
        with self._lock:
            if name is None:
                self._instances.clear()
            else:
                self._instances.pop(name, None)

    def names(self) -> list[str]:
        return sorted(self._factories)
