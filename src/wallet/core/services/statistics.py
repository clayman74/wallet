from typing import AsyncGenerator

from wallet.core.entities import Statistics, StatisticsFilters
from wallet.core.services import Service


class StatisticsService(Service):
    async def get_statistics(self, filters: StatisticsFilters) -> AsyncGenerator[Statistics, None]:
        async for statistics in self._storage.statistics.fetch_statistics(filters=filters):
            yield statistics
