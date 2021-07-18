from wallet.core.storage.accounts import AccountRepo
from wallet.core.storage.categories import CategoryRepo
from wallet.core.storage.operations import OperationRepo
from wallet.core.storage.statistics import StatisticsRepo
from wallet.core.storage.tags import TagRepo


class Storage:
    accounts: AccountRepo
    categories: CategoryRepo
    operations: OperationRepo
    statistics: StatisticsRepo
    tags: TagRepo
