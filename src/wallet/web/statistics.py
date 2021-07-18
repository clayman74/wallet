from datetime import date
from http import HTTPStatus
from typing import Dict

from aiohttp import web
from aiohttp_micro.web.handlers import json_response
from aiohttp_micro.web.handlers.openapi import OpenAPISpec, ParameterIn, ParametersSchema, ResponseSchema
from marshmallow import fields, post_load, pre_load, Schema
from passport.client import user_required

from wallet.core.entities import StatisticsFilters
from wallet.core.use_cases.statistics import StatisticsUseCase
from wallet.storage import DBStorage
from wallet.web import CommonParameters, PeriodSchema


class StatisticsFilterSchema(ParametersSchema):
    """Filter statistics."""

    in_: ParameterIn.query

    period = fields.Nested(PeriodSchema, required=True, description="Period")

    @pre_load
    def prepare_filters(self, data, **kwargs):
        return {"period": {"from": data["from"], "to": data["to"]}}

    @post_load
    def make_filters(self, data: Dict[str, date], **kwargs) -> StatisticsFilters:
        return StatisticsFilters(user=self.context["user"], period=data["period"])


class StatisticsSchema(Schema):
    """Get statistics per period."""

    period = fields.Nested(PeriodSchema, required=True, description="Period")
    account = fields.Int(required=True, description="Account")
    expenses = fields.Str(places=2, required=True, description="Period expenses")
    incomes = fields.Str(places=2, required=True, description="Period incomes")


class StatisticsResponseSchema(ResponseSchema):
    """Get statistics info."""

    statistics = fields.List(fields.Nested(StatisticsSchema))


@user_required()
async def stats(request: web.Request) -> web.Response:
    """Get statistics info."""

    filters_schema = StatisticsFilterSchema()
    filters_schema.context["user"] = request["user"]
    filters = filters_schema.load(data=request.query)

    use_case = StatisticsUseCase(storage=DBStorage(request.app["db"]), logger=request.app["logger"])
    statistics = [s async for s in use_case.execute(filters=filters)]

    schema = StatisticsResponseSchema()
    return json_response(schema.dump({"statistics": statistics}))


stats.spec = OpenAPISpec(
    operation="getStatistics",
    parameters=[CommonParameters, StatisticsFilterSchema],
    responses={
        HTTPStatus.OK: StatisticsResponseSchema,
        # HTTPStatus.UNAUTHORIZED: ErrorSchema,
        # HTTPStatus.FORBIDDEN: ErrorSchema,
    },
    security="TokenAuth",
    tags=["statistics"],
)
