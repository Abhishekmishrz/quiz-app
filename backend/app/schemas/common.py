"""Shared schema primitives: PyObjectId and a generic PagedResponse."""
from typing import Any, Generic, List, TypeVar

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

T = TypeVar("T")


class PyObjectId(str):
    """Pydantic v2 compatible ObjectId <-> str field type.

    Validates that incoming values are valid ObjectIds (accepting either an
    `ObjectId` instance or its string form) and always serializes to str, so
    API responses never leak raw BSON types.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> str:
            if isinstance(value, ObjectId):
                return str(value)
            if isinstance(value, str):
                try:
                    ObjectId(value)
                except (InvalidId, TypeError):
                    raise ValueError(f"'{value}' is not a valid ObjectId")
                return value
            raise ValueError(f"Cannot convert {type(value)} to ObjectId")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema_: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "example": "5f8d0d55b54764421b7156a3"}


class PagedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope used by list endpoints."""

    items: List[T]
    total: int
    limit: int
    offset: int
