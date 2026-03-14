"""Code generator for spunk.

Two entry points:

* :func:`generate` — walks live tenant/service/resource objects and writes
  the typed SDK package. Called from ``Tenant.generate()``.
* :func:`from_manifest` — reads a manifest dict (as produced by
  ``Tenant.to_manifest()``) and writes the same package without requiring
  the original infrastructure code. Called from ``spunk gen``.

Generated layout::

    infra/
        __init__.py          # from .acme import Acme; acme = Acme()
        acme/
            __init__.py      # class Acme: scheduler: Scheduler; ...
            scheduler.py     # class Scheduler: items_table: DynamoDBTable; ...
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tenant import Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_snake_case(name: str) -> str:
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower().replace("-", "_")


def _to_pascal_case(name: str) -> str:
    return "".join(w.title() for w in _to_snake_case(name).split("_"))


def _ensure_package(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


# ServiceData: (service_snake, service_pascal, resource_entries)
# resource_entries: list of (module_path, class_name, kwargs, instance_name)
type _ResourceEntry = tuple[str, str, dict, str]
type _ServiceData = tuple[str, str, list[_ResourceEntry]]


def _write_package(
    output_dir: str,
    tenant_name: str,
    services: list[_ServiceData],
) -> None:
    """Write the typed SDK package to disk from pre-extracted service data.

    Shared by :func:`generate` and :func:`from_manifest`.
    """
    root = Path(output_dir)
    _ensure_package(root)

    tenant_snake = _to_snake_case(tenant_name)
    tenant_pascal = _to_pascal_case(tenant_name)
    tenant_dir = root / tenant_snake
    _ensure_package(tenant_dir)

    for service_snake, service_pascal, resource_entries in services:
        lines: list[str] = ["from __future__ import annotations\n"]
        if resource_entries:
            lines.append("\n")
            seen: set[tuple[str, str]] = set()
            for module_path, class_name, _, _ in resource_entries:
                if (module_path, class_name) not in seen:
                    lines.append(f"from {module_path} import {class_name}\n")
                    seen.add((module_path, class_name))
        lines.append(f"\n\nclass {service_pascal}:\n")
        if resource_entries:
            for _, class_name, _, instance_name in resource_entries:
                lines.append(f"    {instance_name}: {class_name}\n")
            lines.append("\n    def __init__(self) -> None:\n")
            for _, class_name, kwargs, instance_name in resource_entries:
                kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
                lines.append(f"        self.{instance_name} = {class_name}({kwargs_str})\n")
        else:
            lines.append("    pass\n")
        (tenant_dir / f"{service_snake}.py").write_text("".join(lines))

    # tenant __init__.py
    tenant_lines: list[str] = ["from __future__ import annotations\n"]
    if services:
        tenant_lines.append("\n")
        for service_snake, service_pascal, _ in services:
            tenant_lines.append(f"from .{service_snake} import {service_pascal}\n")
    tenant_lines.append(f"\n\nclass {tenant_pascal}:\n")
    if services:
        for service_snake, service_pascal, _ in services:
            tenant_lines.append(f"    {service_snake}: {service_pascal}\n")
        tenant_lines.append("\n    def __init__(self) -> None:\n")
        for service_snake, service_pascal, _ in services:
            tenant_lines.append(f"        self.{service_snake} = {service_pascal}()\n")
    else:
        tenant_lines.append("    pass\n")
    (tenant_dir / "__init__.py").write_text("".join(tenant_lines))

    # root __init__.py
    root_init = root / "__init__.py"
    existing = root_init.read_text() if root_init.exists() else ""
    import_line = f"from .{tenant_snake} import {tenant_pascal}\n"
    instance_line = f"{tenant_snake} = {tenant_pascal}()\n"
    additions = "".join([
        import_line if import_line not in existing else "",
        instance_line if instance_line not in existing else "",
    ])
    if additions:
        if existing and not existing.endswith("\n"):
            existing += "\n"
        root_init.write_text(existing + additions)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(tenant: "Tenant", output_dir: str) -> None:
    """Generate a typed SDK package by walking live tenant objects.

    Called by ``Tenant.generate()``. Requires the original infrastructure
    code. For offline generation from a stored manifest use
    :func:`from_manifest`.
    """
    services: list[_ServiceData] = []
    for service, provider in tenant._services:
        service_snake = _to_snake_case(service.name())
        service_pascal = _to_pascal_case(service.name())
        resource_entries: list[_ResourceEntry] = []
        for resource in service.resources(provider):
            result = resource.accessor()
            if result is None:
                continue
            module_path, class_name, kwargs = result
            resource_entries.append((
                module_path, class_name, kwargs,
                _to_snake_case(resource.resource_name),
            ))
        services.append((service_snake, service_pascal, resource_entries))
    _write_package(output_dir, tenant.name, services)


def from_manifest(manifest: dict, output_dir: str) -> None:
    """Generate a typed SDK package from a stored manifest dict.

    The manifest is produced by ``Tenant.to_manifest()`` and retrieved from
    S3 via ``Tenant.load_manifest()``. No infrastructure code is required::

        manifest = Tenant.load_manifest(bucket="my-bucket", key="spunk/acme.json")
        from_manifest(manifest, "infra/")
    """
    services: list[_ServiceData] = []
    for svc in manifest["services"]:
        resource_entries: list[_ResourceEntry] = [
            (r["accessor_module"], r["accessor_class"], r["kwargs"], r["instance_name"])
            for r in svc["resources"]
        ]
        services.append((svc["snake"], svc["pascal"], resource_entries))
    _write_package(output_dir, manifest["tenant"], services)
