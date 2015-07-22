import asyncio
from datetime import datetime

import pytest

from wallet.models import accounts, auth, categories, transactions

from tests.conftest import async_test
from . import BaseHandlerTest


class BaseTransactionTest(BaseHandlerTest):

    @asyncio.coroutine
    def prepare_owner(self, app):
        owner = {'login': 'John', 'password': 'top_secret',
                 'created_on': datetime.now()}
        return (yield from self.create_instance(app, auth.users_table, owner))

    @asyncio.coroutine
    def prepare_account(self, app, account):
        raw = dict(**account)
        if not account.get('owner_id'):
            owner_id = yield from self.prepare_owner(app)
            raw.setdefault('owner_id', owner_id)

        raw.update(created_on=datetime.now())
        raw['id'] = yield from self.create_instance(
            app, accounts.accounts_table, raw)

        return raw

    @asyncio.coroutine
    def prepare_category(self, app, category):
        raw = dict(**category)
        if not category.get('owner_id'):
            owner_id = yield from self.prepare_owner(app)
            raw.setdefault('owner_id', owner_id)

        raw['id'] = yield from self.create_instance(
            app, categories.categories_table, raw)

        return raw

    @asyncio.coroutine
    def prepare_transaction(self, app, transaction):
        raw = dict(**transaction)
        owner_id = yield from self.prepare_owner(app)

        raw_account = {'name': 'Debit card', 'original_amount': 3000.0,
                       'current_amount': 0.0, 'owner_id': owner_id}
        account = yield from self.prepare_account(app, account=raw_account)

        raw_category = {'name': 'Food', 'type': categories.EXPENSE_CATEGORY,
                        'owner_id': owner_id}
        category = yield from self.prepare_category(app, category=raw_category)

        raw.update(created_on=datetime.now(), account_id=account.get('id'),
                   category_id=category.get('id'))
        raw['id'] = yield from self.create_instance(
            app, transactions.transactions_table, raw
        )

        return raw


class TestTransactionCollection(BaseTransactionTest):

    @pytest.mark.handlers
    @pytest.mark.transactions
    @pytest.mark.parametrize('endpoint', (
        'api.get_transactions',
        'api.create_transaction'
    ))
    def test_endpoints_exists(self, application, endpoint):
        assert endpoint in application.router

    @pytest.mark.handlers
    @pytest.mark.transactions
    @async_test(attach_server=True)
    def test_get_success(self, application, db, **kwargs):
        server = kwargs.get('server')
        endpoint = 'api.get_transactions'

        transaction = {'description': 'Meal', 'amount': 300.0,
                       'created_on': datetime.now()}
        expected = yield from self.prepare_transaction(application, transaction)
        del expected['created_on']

        with (yield from server.response_ctx('GET', endpoint)) as resp:
            assert resp.status == 200

            response = yield from resp.json()
            assert 'transactions' in response
            assert [expected, ] == response['transactions']

    @pytest.mark.handlers
    @pytest.mark.transactions
    @pytest.mark.parametrize('params', (
        {'json': False},
        {'json': True}
    ))
    @async_test(attach_server=True)
    def test_create_success(self, application, db, params, **kwargs):
        server = kwargs.get('server')
        endpoint = 'api.create_transaction'

        owner_id = yield from self.prepare_owner(application)

        raw_account = {'name': 'Debit card', 'original_amount': 3000.0,
                       'current_amount': 0.0, 'owner_id': owner_id}
        account = yield from self.prepare_account(application, raw_account)

        raw_category = {'name': 'Food', 'type': categories.EXPENSE_CATEGORY,
                        'owner_id': owner_id}
        category = yield from self.prepare_category(application, raw_category)

        transaction = {'description': 'Meal', 'amount': 300.0,
                       'account_id': account.get('id'),
                       'category_id': category.get('id')}

        expected = {'id': 1, 'description': 'Meal', 'amount': 300.0,
                    'account_id': account.get('id'),
                    'category_id': category.get('id')}

        params.update(endpoint=endpoint, data=transaction)
        with (yield from server.response_ctx('POST', **params)) as response:
            assert response.status == 201

            response = yield from response.json()
            assert 'transaction' in response
            assert expected == response['transaction']


class TestTransactionResource(BaseTransactionTest):
    transaction = {'description': 'Meal', 'amount': 300.0}

    @pytest.mark.handlers
    @pytest.mark.transactions
    @pytest.mark.parametrize('endpoint', (
        'api.get_transaction',
        'api.update_transaction',
        'api.remove_transaction'
    ))
    def test_endpoint_exists(self, application, endpoint):
        assert endpoint in application.router

    @pytest.mark.handlers
    @pytest.mark.transactions
    @async_test(attach_server=True)
    def test_get_success(self, application, db, **kwargs):
        server = kwargs.get('server')
        endpoint = 'api.get_transaction'

        expected = yield from self.prepare_transaction(application,
                                                       self.transaction)
        del expected['created_on']

        params = {
            'endpoint': endpoint,
            'endpoint_params': {'instance_id': expected.get('id')}
        }
        with (yield from server.response_ctx('GET', **params)) as response:
            assert response.status == 200

            data = yield from response.json()
            assert 'transaction' in data
            assert expected == data['transaction']

    @pytest.mark.handlers
    @pytest.mark.transactions
    @async_test(attach_server=True)
    def test_update_success(self, application, db, **kwargs):
        server = kwargs.get('server')
        endpoint = 'api.update_transaction'

        expected = yield from self.prepare_transaction(application,
                                                       self.transaction)
        expected['amount'] = 310.0
        del expected['created_on']

        params = {
            'endpoint': endpoint,
            'endpoint_params': {'instance_id': expected.get('id')},
            'data': {'amount': 310.0},
            'json': True
        }
        with (yield from server.response_ctx('PUT', **params)) as resp:
            assert resp.status == 200

            response = yield from resp.json()
            assert 'transaction' in response
            assert expected == response['transaction']

    @pytest.mark.handlers
    @pytest.mark.transactions
    @async_test(attach_server=True)
    def test_remove_success(self, application, db, **kwargs):
        server = kwargs.get('server')
        endpoint = 'api.remove_transaction'

        expected = yield from self.prepare_transaction(application,
                                                       self.transaction)
        params = {
            'endpoint': endpoint,
            'endpoint_params': {'instance_id': expected.get('id')}
        }
        with (yield from server.response_ctx('DELETE', **params)) as response:
            assert response.status == 200

        with (yield from application.engine) as conn:
            query = transactions.transactions_table.count().where(
                transactions.transactions_table.c.id == expected.get('id'))
            count = yield from conn.scalar(query)
            assert count == 0
