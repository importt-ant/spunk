from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class Resource(ABC):
    """Abstract base class for all infrastructure resources.

    All provider-specific resource classes ultimately inherit from this.
    ``declare()`` is intended for internal use by Service implementations
    — end users should not invoke it directly.
    """

    def __init__(self, resource_name: str, tenant_name: str, service_name: str) -> None:
        self.resource_name: str = resource_name
        self.tenant_name: str = tenant_name
        self.service_name: str = service_name

    @abstractmethod
    def declare(self) -> Any:
        """Declare this resource to the Pulumi stack.

        Constructs the underlying Pulumi resource object, registering it with
        the active Pulumi stack. Called internally by ``Service.provision()``.
        Do not call this directly from user/tenant code.
        """
        ...

    def accessor(self) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """Return ``(module_path, class_name, kwargs)`` for the generator, or ``None``.

        Concrete resource subclasses override this to declare which accessor
        class from ``spunk.accessors`` represents this resource at runtime,
        and with which constructor arguments.  Called by
        :func:`spunk.generator.generate` — do not call directly.
        """
        return None

    def to_manifest_entry(self) -> Optional[Dict[str, Any]]:
        """Return this resource's manifest dict entry, or ``None`` if it has no accessor.

        This is the single source of truth for the manifest schema at the
        resource level. :meth:`Tenant.to_manifest` calls this and filters out
        ``None`` values — do not call directly.

        The returned dict has the shape::

            {
                "resource_name":   "acme-items",
                "accessor_module": "spunk.accessors.aws.dynamodb_table",
                "accessor_class":  "DynamoDBTable",
                "kwargs":          {"resource_name": "acme-items", ...},
            }
        """
        result = self.accessor()
        if result is None:
            return None

        module_path, class_name, kwargs = result
        return {
            "resource_name": self.resource_name,
            "accessor_module": module_path,
            "accessor_class": class_name,
            "kwargs": kwargs,
        }
