from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key


def convert_decimals(obj: Any) -> Any:
    """Recursively convert DynamoDB ``Decimal`` values to ``int`` or ``float``."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj


class DynamoDBTable:
    """Runtime accessor for a provisioned DynamoDB table.

    Instantiated by generated SDK code — do not construct manually in most
    cases; use the generated module-level instance instead::

        import infra
        infra.acme.scheduler.items_table.add({"id": "1", "name": "hello"})
    """

    def __init__(
        self,
        resource_name: str,
        region: str,
        profile: Optional[str] = None,
    ) -> None:
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        dynamodb = session.resource("dynamodb", region_name=region)
        self._table = dynamodb.Table(resource_name)
    
    # TODO: function names aren't great
    def add(self, item: Dict) -> None:
        """Insert or replace an item (None values and empty strings are stripped)."""
        cleaned = {k: v for k, v in item.items() if v is not None and v != ""}
        self._table.put_item(Item=cleaned)

    # TODO: figure out some way to point to the id field
    def get(self, id: str) -> Dict:
        """Retrieve an item by primary key ``id``."""
        response = self._table.get_item(Key={"id": id})
        item = response.get("Item")
        if item is None:
            raise KeyError(f"Item with id '{id}' not found.")
        return item

    def update(self, id: str, update_expression: str, expression_values: Dict) -> None:
        """Update an item using a DynamoDB update expression."""
        cleaned = {k: v for k, v in expression_values.items() if v is not None and v != ""}
        self._table.update_item(
            Key={"id": id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=cleaned,
        )

    def delete(self, id: str) -> None:
        """Delete an item by primary key ``id``."""
        self._table.delete_item(Key={"id": id})

    def query(self, field: str, value: str) -> List[Dict]:
        """Query items by a GSI field (exact match).

        Assumes a GSI named ``<field>-index``.
        """
        index_name = f"{field}-index"
        response = self._table.query(
            IndexName=index_name,
            KeyConditionExpression=Key(field).eq(value),
        )
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = self._table.query(
                IndexName=index_name,
                KeyConditionExpression=Key(field).eq(value),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        return items

    # TODO: missing pagination support for very large tables
    def scan(self, limit: Optional[int] = None) -> List[Dict]:
        """Scan all items in the table, optionally capping the result count."""
        response = self._table.scan(Limit=limit) if limit else self._table.scan()
        items = response.get("Items", [])
        if limit is None:
            while "LastEvaluatedKey" in response:
                response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))
        return items

    # TODO: should be removed entirely, force the user to do scan,
    # making them more aware of the cost implications of counting items in DynamoDB
    def count(self) -> int:
        """Return the total number of items in the table."""
        response = self._table.scan(Select="COUNT")
        total = response.get("Count", 0)
        while "LastEvaluatedKey" in response:
            response = self._table.scan(
                Select="COUNT",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            total += response.get("Count", 0)
        return total
