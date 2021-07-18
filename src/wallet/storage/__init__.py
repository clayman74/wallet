from databases import Database

from wallet.core.storage import Storage
from wallet.storage.accounts import AccountDBRepo
from wallet.storage.categories import CategoryDBRepo
from wallet.storage.operations import OperationDBRepo
from wallet.storage.statistics import StatisticsDBRepo


class DBStorage(Storage):
    def __init__(self, database: Database) -> None:
        self.accounts = AccountDBRepo(database=database)
        self.categories = CategoryDBRepo(database=database)
        self.operations = OperationDBRepo(database=database)
        self.statistics = StatisticsDBRepo(database=database)
