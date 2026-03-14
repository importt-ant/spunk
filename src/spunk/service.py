from __future__ import annotations

from typing import Any, List, Type
from abc import ABC, abstractmethod

from .resources import Resource


class Service(ABC):
    """Base class for all infrastructure services.

    Only ``resources()`` must be implemented. ``name()`` defaults to the class
    name and ``dependencies()`` defaults to an empty list — override either
    when needed.

    Example::

        class MyService(Service):
            def dependencies(self) -> List[Type[Service]]:
                return [OtherService]

            def resources(self, provider) -> List[Resource]:
                return [
                    DynamoDBTable(f"{self._tenant_name}-items", self._tenant_name, self.name(), provider)
                    .with_hash_key("id")
                    .add_attribute("id", "S"),
                ]
    """

    def __init__(self, tenant_name: str) -> None:
        self._tenant_name: str = tenant_name

    def name(self) -> str:
        """Return the service name. Defaults to the class name."""
        return type(self).__name__

    def dependencies(self) -> List[Type["Service"]]:
        """Return the list of service types this service depends on.

        Override to declare dependencies::

            def dependencies(self):
                return [OtherService]
        """
        return []

    def has_dependencies(self, services: List["Service"]) -> bool:
        """Return True if every dependency type has an instance in ``services``."""
        available = {type(s) for s in services}
        return all(dep in available for dep in self.dependencies())

    def missing_dependencies(self, services: List["Service"]) -> List[Type["Service"]]:
        """Return the dependency types not satisfied by ``services``."""
        available = {type(s) for s in services}
        return [dep for dep in self.dependencies() if dep not in available]

    @abstractmethod
    def resources(self, provider: Any) -> List[Resource]:
        """Return the list of configured resource builders for this service.

        Use ``self.tenant_name`` to scope resource names to the current tenant.
        Each entry should be a fully-configured ``Resource`` subclass instance
        (e.g. ``DynamoDBTable``, ``S3Bucket``).
        """
        ...

    def provision(self, provider: Any) -> None:
        """Declare all resources for this service to the Pulumi stack.

        Called internally by ``Tenant.deploy()`` — do not call directly.
        """
        for resource in self.resources(provider):
            resource.declare()
