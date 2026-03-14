from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

# TODO: json structure can be moved here, so we can export as json

class Resource(ABC):
    """Abstract base class for all infrastructure resources.

    All provider-specific resource classes ultimately inherit from this.
    ``__call__`` is intended for internal use by Service implementations
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
