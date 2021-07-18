import functools
import io
from datetime import date
from typing import Any, Dict, Generic, Type, TypeVar

from aiohttp import web
from aiohttp_micro.web.handlers import json_response
from aiohttp_micro.web.handlers.openapi import ParameterIn, ParametersSchema
from marshmallow import fields, post_load, pre_dump, Schema, ValidationError

from wallet.core.entities import Payload, Period  # noqa: F401


PT = TypeVar("PT", bound="Payload")


class CommonParameters(ParametersSchema):
    in_ = ParameterIn.header

    request_id = fields.Str(data_key="X-Request-ID", description="Incoming request ID")
    correlation_id = fields.Str(missing="", data_key="X-Correlation-ID", description="Incoming parent request ID")


class CollectionFiltersSchema(ParametersSchema):
    """Collection filters."""

    in_ = ParameterIn.query

    offset = fields.Int(default=0, missing=0, description="Offset from collection beginning")
    limit = fields.Int(default=10, missing=10, description="Number of items per page")


class PayloadSchema(Schema, Generic[PT]):
    payload_cls: Type[PT]

    @post_load
    def build_payload(self, payload: Dict[str, Any], **kwargs) -> PT:
        return self.payload_cls(**payload)


class PeriodSchema(Schema):
    begin = fields.Date(format="iso", data_key="from", required=True)
    end = fields.Date(format="iso", data_key="to", required=True)

    @post_load
    def make_period(self, data: Dict[str, date], **kwargs) -> Period:
        return Period(begin=data["begin"], end=data["end"])

    @pre_dump
    def serialize(self, period: Period, **kwargs) -> Dict[str, str]:
        return {"begin": period.begin, "end": period.end}


async def get_payload(request: web.Request) -> Dict[str, Any]:
    if "application/json" in request.content_type:
        payload = await request.json()
    elif "multipart/form-data" in request.content_type:
        reader = await request.multipart()

        payload = {}
        while True:
            field = await reader.next()  # noqa: B305

            if not field:
                break

            if field.filename:
                buff = io.StringIO()
                while True:
                    chunk = await field.read_chunk()  # 8192 bytes by default.
                    if not chunk:
                        break

                    buff.write(chunk.decode("utf-8"))

                payload[field.name] = buff.getvalue()
            else:
                payload[field.name] = await field.read(decode=True)
    else:
        payload = await request.post()
    return dict(payload)


def validate_payload(schema_cls: Type[Schema], inject_user: bool = False):
    def wrapper(f):
        @functools.wraps(f)
        async def wrapped(request: web.Request) -> web.Response:
            payload = await get_payload(request)

            try:
                schema = schema_cls()

                if inject_user:
                    schema.context["user"] = request["user"]

                document = schema.load(payload)
            except ValidationError as exc:
                return json_response({"errors": exc.messages}, status=422)

            return await f(document, request)

        return wrapped

    return wrapper


def serialize(schema_cls: Schema, status: int = 200):
    def wrapper(f):
        @functools.wraps(f)
        async def wrapped(request: web.Request, *args, **kwargs):
            response = await f(request, *args, **kwargs)

            if isinstance(response, web.Response):
                return response
            else:
                schema = schema_cls()
                return json_response(schema.dump(response), status=status)

        return wrapped

    return wrapper
