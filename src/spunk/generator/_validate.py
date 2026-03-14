"""Pre-write validation pass for generated SDK packages."""
from __future__ import annotations

import importlib

from ._types import _ServiceData


def validate_accessors(services: list[_ServiceData]) -> None:
    """Verify every accessor ``(module, class)`` pair is importable.

    Runs before any files are written so the caller sees all failures at once
    rather than discovering them one by one mid-write.

    Raises:
        ImportError: If one or more accessors cannot be resolved, with a
            message listing every failed entry.
    """
    errors: list[str] = []

    for _service_snake, _service_pascal, resource_entries in services:
        for module_path, class_name, _, instance_name in resource_entries:
            try:
                mod = importlib.import_module(module_path)
            except ImportError as exc:
                errors.append(
                    f"  {instance_name}: cannot import '{module_path}': {exc}"
                )
                continue
            if not hasattr(mod, class_name):
                errors.append(
                    f"  {instance_name}: '{module_path}' has no class '{class_name}'"
                )

    if errors:
        raise ImportError("Accessor validation failed:\n" + "\n".join(errors))
