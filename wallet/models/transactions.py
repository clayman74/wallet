from datetime import datetime

from marshmallow import Schema, fields
import sqlalchemy

from .base import create_table


INCOME_TRANSACTION = 'income'
EXPENSE_TRANSACTION = 'expense'
TRANSFER_TRANSACTION = 'transfer'
TRANSACTION_TYPES = (INCOME_TRANSACTION, EXPENSE_TRANSACTION,
                     TRANSFER_TRANSACTION)

transactions_table = create_table('transactions', (
    sqlalchemy.Column('account_id', sqlalchemy.Integer,
                      sqlalchemy.ForeignKey('accounts.id'), nullable=False),
    sqlalchemy.Column('category_id', sqlalchemy.Integer,
                      sqlalchemy.ForeignKey('categories.id'), nullable=False),
    sqlalchemy.Column('description', sqlalchemy.String(255)),
    sqlalchemy.Column('amount', sqlalchemy.Numeric(), nullable=False),
    sqlalchemy.Column('type', sqlalchemy.String(20), nullable=False,
                      index=True, default=EXPENSE_TRANSACTION),
    sqlalchemy.Column('created_on', sqlalchemy.DateTime(), nullable=False)
))

transaction_details_table = create_table('transaction_details', (
    sqlalchemy.Column('name', sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column('price_per_unit', sqlalchemy.Numeric()),
    sqlalchemy.Column('count', sqlalchemy.Numeric()),
    sqlalchemy.Column('total', sqlalchemy.Numeric()),
    sqlalchemy.Column('transaction_id', sqlalchemy.Integer(),
                      sqlalchemy.ForeignKey('transactions.id'), nullable=False)
))


def to_datetime(value):
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')


transactions_schema = {
    'id': {'type': 'integer'},
    'account_id': {'type': 'integer', 'coerce': int, 'required': True,
                   'empty': False},
    'category_id': {'type': 'integer', 'coerce': int, 'required': True,
                    'empty': False},
    'description': {'type': 'string', 'maxlength': 255, 'empty': True},
    'amount': {'type': 'number', 'coerce': float, 'required': True,
               'empty': False},
    'type': {'type': 'string', 'maxlength': 20, 'required': True,
             'empty': False, 'allowed': TRANSACTION_TYPES},
    'created_on': {'type': 'datetime', 'coerce': to_datetime, 'empty': True}
}

transaction_details_schema = {
    'id': {'type': 'integer'},
    'name': {'type': 'string', 'maxlength': 255, 'required': True},
    'price_per_unit': {'type': 'number', 'coerce': float, 'empty': True},
    'count': {'type': 'number', 'coerce': float, 'empty': True},
    'total': {'type': 'number', 'coerce': float, 'required': True},
    'transaction_id': {'type': 'integer', 'coerce': int, 'required': True},
}


class TransactionSerializer(Schema):
    id = fields.Integer()
    account_id = fields.Integer()
    category_id = fields.Integer()
    description = fields.String()
    amount = fields.Float()
    type = fields.String()
    created_on = fields.DateTime(format='%d-%m-%Y %X')


class TransactionDetailSerializer(Schema):
    id = fields.Integer()
    name = fields.String()
    price_per_unit = fields.Float()
    count = fields.Float()
    total = fields.Float()
