from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """Abstract base class for all cloud provider wrappers.

    Wraps a Pulumi provider object, handling lazy instantiation so the
    underlying Pulumi package is only imported when the provider is first used.

    One instance should be shared across all resources that belong to the same
    provider account/region combination.
    """

    def __init__(self) -> None:
        self._provider: Any = None

    def get(self) -> Any:
        """Return the underlying Pulumi provider, creating it on first call."""
        if self._provider is None:
            self._provider = self._create()
        return self._provider

    @abstractmethod
    def _create(self) -> Any:
        """Instantiate and return the Pulumi provider object.

        Called once on the first ``get()`` call. Do not call directly.
        """
        ...
