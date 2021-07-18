from logging import Logger
from typing import AsyncGenerator

from wallet.core.entities import Statistics, StatisticsFilters
from wallet.core.services.statistics import StatisticsService
from wallet.core.storage import Storage


class StatisticsUseCase:
    def __init__(self, storage: Storage, logger: Logger) -> None:
        self.storage = storage
        self.service = StatisticsService(storage=storage, logger=logger)

    async def execute(self, filters: StatisticsFilters) -> AsyncGenerator[Statistics, None]:
        async for statistics in self.service.get_statistics(filters=filters):
            yield statistics
