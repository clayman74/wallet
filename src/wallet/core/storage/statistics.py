from typing import AsyncGenerator

from wallet.core.entities import Statistics, StatisticsFilters
from wallet.core.storage.base import Repo


class StatisticsRepo(Repo[Statistics, StatisticsFilters]):
    async def fetch_statistics(self, filters: StatisticsFilters) -> AsyncGenerator[Statistics, None]:
        raise NotImplementedError()
