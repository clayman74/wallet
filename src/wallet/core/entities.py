from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

import pendulum  # type: ignore
from passport.domain import User

from wallet.core.tools import month_range


@dataclass
class Entity:
    key: int = field(default=0, init=False)

    def __post_init__(self):
        pass


@dataclass
class Payload:
    user: User


@dataclass
class Filters:
    user: User


@dataclass
class Balance(Entity):
    month: date
    expenses: Decimal = field(default=Decimal("0.0"))
    incomes: Decimal = field(default=Decimal("0.0"))
    rest: Decimal = field(default=Decimal("0.0"))


class OperationType(Enum):
    income = "income"
    expense = "expense"


@dataclass
class EntityWithBalance(Entity):
    balance: Dict[date, Balance] = field(default_factory=dict, init=False)

    def __post_init__(self):
        super().__post_init__()

        if not self.balance:
            month = pendulum.today().start_of("month").date()

            self.balance[month] = Balance(month=month)

    def add_operation(
        self,
        amount: Decimal,
        operation_type: OperationType,
        created_on: datetime,
    ) -> None:
        operation_month = pendulum.instance(created_on).start_of("month").date()

        rest = None
        for month in month_range(operation_month):
            if month in self.balance:
                balance = self.balance[month]
            else:
                balance = Balance(month=month)

            if rest is None:
                rest = balance.rest

            if month == operation_month:
                if operation_type == OperationType.expense:
                    balance.expenses += amount
                elif operation_type == OperationType.income:
                    balance.incomes += amount

            rest = rest + balance.incomes - balance.expenses
            balance.rest = rest

            self.balance[month] = balance

    def drop_operation(
        self,
        amount: Decimal,
        operation_type: OperationType,
        created_on: datetime,
    ) -> None:
        operation_month = pendulum.instance(created_on).start_of("month").date()

        rest = None
        for month in month_range(operation_month):
            if month in self.balance:
                balance = self.balance[month]
            else:
                balance = Balance(month=month)

            if rest is None:
                rest = balance.rest

            if month == operation_month:
                if operation_type == OperationType.expense:
                    balance.expenses -= amount
                    rest += amount
                elif operation_type == OperationType.income:
                    balance.incomes -= amount
                    rest -= amount

            rest = rest + balance.incomes - balance.expenses
            balance.rest = rest

            self.balance[month] = balance


@dataclass
class Account(EntityWithBalance):
    name: str
    user: User


@dataclass
class AccountPayload(Payload):
    name: str


@dataclass
class AccountFilters(Filters):
    name: Optional[str] = None


@dataclass
class Tag(EntityWithBalance):
    name: str
    user: User


@dataclass
class TagPayload(Payload):
    name: str


@dataclass
class TagFilters(Filters):
    name: Optional[str] = None


@dataclass
class Category(EntityWithBalance):
    name: str
    user: User
    tags: List[Tag] = field(default_factory=list)


@dataclass
class CategoryPayload(Payload):
    name: str
    tags: List[int] = field(default_factory=list)


@dataclass
class CategoryFilters(Filters):
    name: Optional[str] = None


@dataclass
class Operation(Entity):
    amount: Decimal
    description: str
    account: Account
    category: Category
    user: User
    operation_type: OperationType = OperationType.expense
    tags: List[Tag] = field(default_factory=list)
    created_on: datetime = field(init=False)


@dataclass
class OperationPayload(Payload):
    amount: Decimal
    account: int
    category: int
    operation_type: OperationType
    description: str = ""
    tags: List[int] = field(default_factory=list)


@dataclass
class OperationFilters(Filters):
    month: Optional[date] = None
    account: Optional[Account] = None
    category: Optional[Category] = None
    tags: List[Tag] = field(default_factory=list)