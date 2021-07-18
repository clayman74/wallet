from decimal import Decimal
from typing import AsyncGenerator, Dict

import sqlalchemy
from sqlalchemy.orm import Query  # type: ignore
from sqlalchemy.sql import func

from wallet.core.entities import OperationType, Period, Statistics, StatisticsFilters
from wallet.core.storage.statistics import StatisticsRepo
from wallet.storage.base import DBRepo
from wallet.storage.operations import operations


class StatisticsDBRepo(DBRepo, StatisticsRepo):
    def _get_query(self, *, filters: StatisticsFilters) -> Query:
        return (
            sqlalchemy.select(
                [
                    operations.c.account_id.label("account"),
                    func.sum(operations.c.amount)
                    .filter(operations.c.type == OperationType.expense.value)
                    .label("expenses"),
                    func.sum(operations.c.amount)
                    .filter(operations.c.type == OperationType.income.value)
                    .label("incomes"),
                ]
            )
            .where(
                sqlalchemy.and_(
                    operations.c.user == filters.user.key,
                    operations.c.created_on >= filters.period.begin,
                    operations.c.created_on <= filters.period.end,
                )
            )
            .group_by(operations.c.account_id)
        )

    def _process_row(self, row: Dict[str, Decimal], period: Period) -> Statistics:
        return Statistics(period=period, account=row["account"], expenses=row["expenses"], incomes=row["incomes"])

    async def fetch_statistics(self, filters: StatisticsFilters) -> AsyncGenerator[Statistics, None]:
        query = self._get_query(filters=filters)

        async for row in self._database.iterate(query=query):
            yield self._process_row(row, period=filters.period)
