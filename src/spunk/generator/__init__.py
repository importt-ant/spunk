"""SDK generator for spunk.

Two public entry points:

* :func:`generate` — called via ``Tenant.generate()``. Converts live tenant
  objects to a manifest, then delegates to :func:`from_manifest`.
* :func:`from_manifest` — rebuilds the SDK from a manifest dict. Works
  entirely offline; no infrastructure code required.

Generated layout::

    infra/
        __init__.py          # from .acme import Acme; acme = Acme()
        acme/
            __init__.py      # class Acme: scheduler: Scheduler; ...
            scheduler.py     # class Scheduler: items_table: DynamoDBTable; ...

Internal pipeline (all steps in :mod:`spunk.generator`)::

    from_manifest()
        └── _build_service_data()     parse manifest → typed list
        └── validate_accessors()      pre-flight import check
        └── _write_package()          orchestrate writers
              ├── write_service_module()   per-service .py file
              ├── write_tenant_init()      tenant __init__.py
              └── write_root_init()        root __init__.py (idempotent)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._names import to_pascal_case, to_snake_case
from ._types import _ResourceEntry, _ServiceData
from ._validate import validate_accessors
from ._writers import write_root_init, write_service_module, write_tenant_init

if TYPE_CHECKING:
    from spunk.tenant import Tenant

__all__ = ["generate", "from_manifest", "to_snake_case", "to_pascal_case"]


def _build_service_data(manifest: dict) -> list[_ServiceData]:
    """Parse a manifest dict into the internal :data:`_ServiceData` list."""
    services: list[_ServiceData] = []
    for svc in manifest["services"]:
        resource_entries: list[_ResourceEntry] = [
            (
                r["accessor_module"],
                r["accessor_class"],
                r["kwargs"],
                r["instance_name"],
            )
            for r in svc["resources"]
        ]
        services.append((svc["snake"], svc["pascal"], resource_entries))
    return services


def _write_package(
    output_dir: str,
    tenant_name: str,
    services: list[_ServiceData],
) -> None:
    """Orchestrate the full write pipeline for one tenant."""
    validate_accessors(services)

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    tenant_snake = to_snake_case(tenant_name)
    tenant_pascal = to_pascal_case(tenant_name)
    tenant_dir = root / tenant_snake
    tenant_dir.mkdir(parents=True, exist_ok=True)

    for service_snake, service_pascal, resource_entries in services:
        write_service_module(tenant_dir, service_snake, service_pascal, resource_entries)

    write_tenant_init(tenant_dir, tenant_pascal, services)
    write_root_init(root, tenant_snake, tenant_pascal)


def generate(tenant: "Tenant", output_dir: str) -> None:
    """Generate a typed SDK package from a live :class:`~spunk.Tenant`.

    Converts the tenant to a manifest via :meth:`~spunk.Tenant.to_manifest`
    and delegates to :func:`from_manifest`, so both entry points share exactly
    one code path.
    """
    from_manifest(tenant.to_manifest(), output_dir)


def from_manifest(manifest: dict, output_dir: str) -> None:
    """Generate a typed SDK package from a stored manifest dict.

    No infrastructure code is required — the manifest is produced by
    :meth:`~spunk.Tenant.to_manifest` and can be fetched from S3 via
    :meth:`~spunk.Tenant.load_manifest`::

        manifest = Tenant.load_manifest(bucket="my-bucket", key="spunk/acme.json")
        from_manifest(manifest, "infra/")
    """
    services = _build_service_data(manifest)
    _write_package(output_dir, manifest["tenant"], services)
