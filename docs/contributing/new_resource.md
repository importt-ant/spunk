# Adding a New Resource Class

This document explains the patterns used across all existing resource classes
so new ones are consistent. It is intentionally descriptive rather than
prescriptive — follow the spirit, not just the letter.

---

## Anatomy of a resource

Every resource lives in two places:

```
src/spunk/resources/aws/<name>.py   ← Pulumi builder  (provisioning time)
src/spunk/accessors/aws/<name>.py   ← boto3 accessor  (runtime)
```

The file names must match exactly — the convention-based `accessor()` on
`AWSResource` derives the accessor module path by replacing `.resources.` with
`.accessors.` in the builder's module path and stripping the `Builder` suffix
from the class name. If the names do not match you must override `accessor()`
manually (see [SESIdentityBuilder](#override-accessor) for an example).

---

## File naming

| What | Convention | Example |
|---|---|---|
| Multi-word AWS service | `snake_case` | `dynamodb_table.py`, `s3_bucket.py` |
| AWS service + sub-resource | `<service>_<subresource>.py` | `ses_identity.py` |
| Single-word service | just the service name | `(hypothetical) queue.py` |

Use the most specific name that unambiguously describes the resource, not the
service family. Prefer `ses_identity` over `ses` because SES has multiple
distinct provisionable things (identity, template, config set…).

---

## The builder class

### Inheritance and class name

```python
class DynamoDBTableBuilder(AWSResource):
class S3BucketBuilder(AWSResource):
class SESIdentityBuilder(AWSResource):
```

- Always extend `AWSResource` (not `Resource` directly).
- Name: `<PascalCaseResourceName>Builder`. The `Builder` suffix is stripped by
  the convention-based `accessor()` to find the matching accessor class.
- If the accessor class name cannot be derived this way (e.g. `SESIdentity`
  from `SESIdentityBuilder` — different word count), override `accessor()`
  explicitly (see below).

### Imports

```python
from __future__ import annotations                  # always first

from typing import Dict, List, Literal, Optional, TYPE_CHECKING

from .aws_resource import AWSResource
from ...providers.aws import AWSProvider

if TYPE_CHECKING:                                   # heavy imports — lazy at runtime
    import pulumi_aws as aws
```

- `pulumi_aws` goes inside `TYPE_CHECKING` only. The actual `import` happens
  inside `declare()` so the module can be imported without Pulumi installed
  (e.g. for accessor-only environments).
- Only import what you use. `TYPE_CHECKING` is not for all imports, just Pulumi
  and any other runtime-heavy dependency.

### `__init__`

```python
def __init__(
    self,
    resource_name: str,
    tenant_name: str,
    service_name: str,
    provider: AWSProvider,
) -> None:
    super().__init__(resource_name, tenant_name, service_name, provider)

    self._billing_mode: Literal["PAY_PER_REQUEST", "PROVISIONED"] = "PAY_PER_REQUEST"
    self._hash_key: Optional[str] = None
    self._attributes: List[Dict] = []
```

- Signature is always the same four params — do not add extra constructor
  arguments. Configuration goes through builder methods.
- Call `super().__init__()` first, always.
- Declare all mutable state as private (`_` prefix) with type annotations.
- Set sensible defaults so the simplest case requires no builder calls beyond
  providing the resource name (e.g. `_block_public_access = True` on S3).

---

## Builder methods

Builder methods accumulate configuration and always return `self` typed as the
concrete class. Pick the prefix based on what the method does:

| Prefix | Use for | Example |
|---|---|---|
| `with_` | Enabling a feature or setting a single scalar option | `with_hash_key("id")`, `with_versioning()` |
| `add_` | Appending to a list (can be called multiple times) | `add_gsi(...)`, `add_cors_rule(...)` |
| `as_` | Selecting a mutually exclusive mode | `as_email()`, `as_domain()` |
| `enable_` | Boolean toggle (alternative to `with_` for flags) | `enable_versioning()` |

Rules:
- Always return `"ClassName"` (quoted forward reference), not `AWSResource` or
  `self`.
- Validate inputs eagerly when a combination is illegal. Raise `ValueError` with
  a message that names the resource and describes the exact constraint:
  ```python
  if projection_type == "INCLUDE" and not non_key_attributes:
      raise ValueError(
          "non_key_attributes must be provided when projection_type is 'INCLUDE'"
      )
  ```
- Do not perform any AWS API calls inside builder methods — they are pure
  configuration.
- Keep optional parameters at the end with `Optional[T] = None`.

---

## `declare()`

```python
def declare(self) -> "aws.dynamodb.Table":
    """Declare the DynamoDB table to the Pulumi stack.

    Internal — invoked by ``Service.provision()``.
    """
    import pulumi
    import pulumi_aws as aws

    # validate prerequisites
    if not self._hash_key:
        raise ValueError(f"DynamoDBTable '{self.resource_name}': hash key must be set")

    # build the primary resource
    table = aws.dynamodb.Table(
        self.resource_name,
        billing_mode=self._billing_mode,
        hash_key=self._hash_key,
        tags=self._tags,
        opts=pulumi.ResourceOptions(provider=self.provider.get()),
    )

    # conditionally attach sub-resources
    if self._versioning_enabled:
        aws.s3.BucketVersioningV2(f"{self.resource_name}-versioning", ...)

    return table
```

Rules:
- `import pulumi` and `import pulumi_aws as aws` go **inside** `declare()`,
  not at module level.
- Always pass `opts=pulumi.ResourceOptions(provider=self.provider.get())` to
  the primary resource.
- Pass `self._tags` to every resource that accepts tags.
- Sub-resources (versioning, CORS, public-access block, DKIM…) are named
  `f"{self.resource_name}-<suffix>"` to keep Pulumi names unique and readable.
- Sub-resources get the same `opts`.
- Return the primary resource object. The return type annotation uses the
  `TYPE_CHECKING` import: `-> "aws.dynamodb.Table"`.
- Validate any configuration that cannot be checked in the builder (e.g.
  something that requires two fields to be consistent) at the top of
  `declare()` before creating anything.
- Docstring: one line + `Internal — invoked by ``Service.provision()``.`

---

## `accessor()` — convention vs. override

### Convention-based (default)

`AWSResource.accessor()` automatically derives the accessor descriptor:

```
spunk.resources.aws.dynamodb_table.DynamoDBTableBuilder
→ spunk.accessors.aws.dynamodb_table.DynamoDBTable
```

This works when:
1. The builder file name matches the accessor file name.
2. The accessor class name equals the builder class name minus `Builder`.

If both conditions hold, **do not override `accessor()`**.

### Override

Override when the accessor constructor signature differs from the default
`(resource_name, region, profile)` kwargs, or when the naming convention
cannot bridge the two names:

```python
def accessor(self) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """Explain why the default convention does not apply."""
    return (
        "spunk.accessors.aws.ses_identity",   # explicit module
        "SESIdentity",                         # explicit class
        {
            "identity": self.resource_name,    # custom kwargs
            "region": self.provider.region,
            "profile": self.provider.profile,
        },
    )
```

The returned dict becomes the `**kwargs` passed to the accessor constructor
in the generated SDK. Every key must match the accessor's `__init__` signature.

Return `None` if the resource has no meaningful runtime accessor
(e.g. an IAM role, a VPC). The generator will skip it silently.

---

## Exporting the new class

After creating the file, add the class to two `__init__.py` files:

**`src/spunk/resources/aws/__init__.py`**
```python
from .my_new_resource import MyNewResourceBuilder
# add to __all__ as well
```

**`src/spunk/resources/__init__.py`** — no changes needed; it re-exports `aws`
as a submodule, so `from spunk.resources.aws import MyNewResourceBuilder` works
automatically.

---

## Quick checklist

- File: `src/spunk/resources/aws/<service_name>.py`
- Matching accessor file: `src/spunk/accessors/aws/<service_name>.py`
- Class: `<PascalCase>Builder(AWSResource)`
- `from __future__ import annotations` at top
- `pulumi_aws` inside `TYPE_CHECKING` only
- `__init__` calls `super().__init__(...)` and stores all config as `_private` typed attrs
- All builder methods return `"ClassName"` and return `self`
- `declare()` imports pulumi locally, passes `provider.get()` and `self._tags`
- `accessor()` overridden only if convention breaks; otherwise omitted
- Class exported from `resources/aws/__init__.py`
