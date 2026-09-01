"""Base schema enforcing the API's camelCase JSON convention.

Python fields stay snake_case (PEP 8); the wire format is camelCase via an alias
generator. `populate_by_name=True` also accepts snake_case input, and FastAPI
serializes responses by alias (camelCase) by default.
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
