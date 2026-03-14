"""Name-conversion utilities for the generator."""
from __future__ import annotations

import re


def to_snake_case(name: str) -> str:
    """Convert a PascalCase or camelCase name to ``snake_case``.

    Also normalises hyphens to underscores::

        to_snake_case("DynamoDBTable")  # "dynamo_db_table"
        to_snake_case("my-bucket")      # "my_bucket"
    """
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower().replace("-", "_")


def to_pascal_case(name: str) -> str:
    """Convert any casing to ``PascalCase``::

        to_pascal_case("my_service")   # "MyService"
        to_pascal_case("my-service")   # "MyService"
        to_pascal_case("MyService")    # "MyService"
    """
    return "".join(w.title() for w in to_snake_case(name).split("_"))
