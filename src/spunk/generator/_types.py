"""Shared type aliases used across the generator package."""
from __future__ import annotations

# (accessor_module, accessor_class, kwargs, instance_name)
type _ResourceEntry = tuple[str, str, dict, str]

# (service_snake, service_pascal, resource_entries)
type _ServiceData = tuple[str, str, list[_ResourceEntry]]
