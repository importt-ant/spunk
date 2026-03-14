"""File-writing helpers for the generated SDK package.

Each function is responsible for exactly one output file (or one logical unit):

* :func:`write_service_module`  — ``acme/scheduler.py``
* :func:`write_tenant_init`     — ``acme/__init__.py``
* :func:`write_root_init`       — ``__init__.py`` (root, idempotent)
"""
from __future__ import annotations

from pathlib import Path

from ._types import _ResourceEntry, _ServiceData


def write_service_module(
    tenant_dir: Path,
    service_snake: str,
    service_pascal: str,
    resource_entries: list[_ResourceEntry],
) -> None:
    """Write ``<tenant_dir>/<service_snake>.py``.

    Produces a class with typed attributes and an ``__init__`` that
    instantiates each accessor::

        class Scheduler:
            items_table: DynamoDBTable

            def __init__(self) -> None:
                self.items_table = DynamoDBTable(resource_name='...', region='...')
    """
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


def write_tenant_init(
    tenant_dir: Path,
    tenant_pascal: str,
    services: list[_ServiceData],
) -> None:
    """Write ``<tenant_dir>/__init__.py``.

    Produces a tenant class that groups all service instances::

        class Acme:
            scheduler: Scheduler

            def __init__(self) -> None:
                self.scheduler = Scheduler()
    """
    lines: list[str] = ["from __future__ import annotations\n"]

    if services:
        lines.append("\n")
        for service_snake, service_pascal, _ in services:
            lines.append(f"from .{service_snake} import {service_pascal}\n")

    lines.append(f"\n\nclass {tenant_pascal}:\n")

    if services:
        for service_snake, service_pascal, _ in services:
            lines.append(f"    {service_snake}: {service_pascal}\n")
        lines.append("\n    def __init__(self) -> None:\n")
        for service_snake, service_pascal, _ in services:
            lines.append(f"        self.{service_snake} = {service_pascal}()\n")
    else:
        lines.append("    pass\n")

    (tenant_dir / "__init__.py").write_text("".join(lines))


def write_root_init(
    root: Path,
    tenant_snake: str,
    tenant_pascal: str,
) -> None:
    """Append a tenant import + instance line to ``<root>/__init__.py``.

    Idempotent — skips lines that are already present, so calling this for
    multiple tenants accumulates rather than overwrites::

        from .acme import Acme
        acme = Acme()
        from .billing import Billing
        billing = Billing()
    """
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
