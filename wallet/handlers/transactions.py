import asyncio
from datetime import datetime
from aiohttp import web

from cerberus import Validator

from ..models.accounts import accounts_table
from ..models.categories import categories_table
from ..models.transactions import (transactions_table, transactions_schema,
                                   TransactionSerializer,
                                   transaction_details_table,
                                   transaction_details_schema,
                                   TransactionDetailSerializer)
from . import base


serializer = TransactionSerializer(exclude=('created_on', ))
details_serializer = TransactionDetailSerializer()

get_transactions = base.get_collection(transactions_table, serializer,
                                       'transactions')
get_transaction = base.get_resource(transactions_table, serializer,
                                    'transaction')
remove_transaction = base.delete_resource(transactions_table, 'transaction')


@base.create_resource(transactions_table, serializer, 'transaction')
@asyncio.coroutine
def create_transaction(request, payload):
    validator = Validator(schema=transactions_schema)
    if not validator.validate(payload):
        return None, validator.errors

    document = validator.document
    document.setdefault('created_on', datetime.now())

    errors = {}
    with (yield from request.app.engine) as conn:
        query = accounts_table.select().where(
            accounts_table.c.id == document.get('account_id'))
        account = yield from conn.scalar(query)

        if not account:
            errors.update(account_id='Account does not exists.')

        query = categories_table.select().where(
            categories_table.c.id == document.get('category_id'))
        category = yield from conn.scalar(query)

        if not category:
            errors.update(category_id='Category does not exists.')

    return document, errors


@base.update_resource(transactions_table, serializer, 'transaction')
@asyncio.coroutine
def update_transaction(request, payload, instance):
    validator = Validator(schema=transactions_schema)
    if not validator.validate(instance):
        return None, validator.errors

    errors = {}
    if 'account_id' in payload.keys() or 'category_id' in payload.keys():
        with (yield from request.app.engine) as conn:
            if 'account_id' in payload.keys():
                query = accounts_table.select().where(
                    accounts_table.c.id == payload.get('account_id'))
                account = yield from conn.scalar(query)

                if not account:
                    errors.update(account_id='Account does not exists.')

            if 'category_id' in payload.keys():
                query = categories_table.select().where(
                    categories_table.c.id == payload.get('category_id'))
                category = yield from conn.scalar(query)

                if not category:
                    errors.update(category_id='Category does not exists.')

    return validator.document, errors


get_details = base.get_collection(transaction_details_table,
                                  details_serializer,
                                  'details')
get_detail = base.get_resource(transaction_details_table, details_serializer,
                               'detail')
remove_detail = base.delete_resource(transaction_details_table, 'detail')


@base.create_resource(transaction_details_table, details_serializer, 'detail')
@asyncio.coroutine
def create_detail(request, payload):
    transaction_id = request.match_info('transaction_id')
    with (yield from request.app.engine) as conn:
        query = transaction_details_table.select().where(
            transaction_details_table.c.id == transaction_id)
        transaction = yield from conn.scalar(query)

    if not transaction:
        return web.HTTPNotFound(text='Transaction not found')

    validator = Validator(schema=transaction_details_schema)
    if not validator.validate(payload):
        return None, validator.errors

    return validator.document, None


@base.update_resource(transaction_details_table, details_serializer, 'detail')
@asyncio.coroutine
def update_detail(request, payload, instance):
    transaction_id = request.match_info('transaction_id')
    with (yield from request.app.engine) as conn:
        query = transaction_details_table.select().where(
            transaction_details_table.c.id == transaction_id)
        transaction = yield from conn.scalar(query)

    if not transaction:
        return web.HTTPNotFound(text='Transaction not found')

    validator = Validator(schema=transaction_details_schema)
    if not validator.validate(instance):
        return None, validator.errors

    return validator.document, None
