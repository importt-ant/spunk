import json
from typing import List, Dict, Any

from .tenant import Tenant


def summarize(tenants: List[Tenant]) -> Dict[str, Any]:
    """Return a JSON-serialisable summary of the given tenants."""
    return {
        "total_tenants": len(tenants),
        "tenants": [
            {
                "name": tenant.name,
                "services": [
                    {
                        "name": service.name(),
                        "dependencies": [d.__name__ for d in service.dependencies()],
                    }
                    for service in tenant.services
                ],
            }
            for tenant in tenants
        ],
    }


def print_summary(tenants: List[Tenant]) -> None:
    """Print a human-readable summary of the given tenants."""
    for tenant in tenants:
        service_names = ", ".join(s.name() for s in tenant.services)
        print(f"  {tenant.name}: {service_names}")


def write_summary(tenants: List[Tenant], filepath: str = "infra-summary.json") -> None:
    """Write a JSON summary of the given tenants to a file."""
    with open(filepath, "w") as f:
        json.dump(summarize(tenants), f, indent=2)
    print(f"Summary written to {filepath}")
