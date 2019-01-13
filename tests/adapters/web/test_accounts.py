from decimal import Decimal

import pytest  # type: ignore

from tests.adapters.web import assert_valid_response, prepare_payload
from tests.storage import prepare_accounts
from wallet.domain import Account, Balance


account_schema = {
    "required": True,
    "type": "dict",
    "schema": {
        "id": {"required": True, "type": "integer"},
        "name": {"required": True, "type": "string"},
        "balance": {
            "required": True,
            "type": "dict",
            "schema": {
                "incomes": {"required": True, "type": "float"},
                "expenses": {"required": True, "type": "float"},
                "rest": {"required": True, "type": "float"},
            },
        },
    },
}


class TestRegisterAccount:
    @pytest.mark.integration
    @pytest.mark.parametrize("json", (True, False))
    async def test_unauthorized(self, fake, aiohttp_client, app, passport, json):
        app["passport"] = passport
        client = await aiohttp_client(app)

        url = app.router.named_resources()["api.accounts.register"].url_for()
        payload, headers = prepare_payload({"name": fake.credit_card_provider()}, json=json)
        resp = await client.post(url, data=payload, headers=headers)

        await assert_valid_response(resp, status=401)

    @pytest.mark.integration
    @pytest.mark.parametrize("json", (True, False))
    async def test_success(self, fake, aiohttp_client, app, passport, json):
        app["passport"] = passport
        client = await aiohttp_client(app)

        url = app.router.named_resources()["api.accounts.register"].url_for()
        payload, headers = prepare_payload(
            {"name": fake.credit_card_provider()}, {"X-ACCESS-TOKEN": "token"}, json=json
        )
        resp = await client.post(url, data=payload, headers=headers)

        await assert_valid_response(
            resp,
            status=201,
            content_type="application/json; charset=utf-8",
            schema={"account": account_schema},
        )

    @pytest.mark.integration
    @pytest.mark.parametrize("json", (True, False))
    async def test_duplicate(self, fake, aiohttp_client, app, passport, json, user, account):
        app["passport"] = passport
        client = await aiohttp_client(app)

        name = fake.credit_card_number()
        account.name = name

        async with app["db"].acquire() as conn:
            await prepare_accounts(conn, [account])

        url = app.router.named_resources()["api.accounts.register"].url_for()
        payload, headers = prepare_payload({"name": name}, {"X-ACCESS-TOKEN": "token"}, json=json)
        resp = await client.post(url, data=payload, headers=headers)

        await assert_valid_response(resp, status=422)


class TestSearchAccounts:
    @pytest.mark.integration
    async def test_unauthorized(self, fake, aiohttp_client, app, passport):
        app["passport"] = passport
        client = await aiohttp_client(app)

        url = app.router.named_resources()["api.accounts"].url_for()
        resp = await client.get(url, headers={"Content-Type": "application/json"})

        await assert_valid_response(resp, status=401)

    @pytest.mark.integration
    async def test_success(self, fake, aiohttp_client, month, app, passport, user):
        app["passport"] = passport
        client = await aiohttp_client(app)

        accounts = [
            Account(key=0, name=fake.credit_card_number(), user=user, balance=[
                Balance(rest=Decimal("-838.00"), expenses=Decimal("838.00"), month=month)
            ]),
            Account(key=0, name=fake.credit_card_number(), user=user, balance=[
                Balance(month=month)
            ])
        ]

        async with app["db"].acquire() as conn:
            await prepare_accounts(conn, accounts)

        url = app.router.named_resources()["api.accounts"].url_for()
        resp = await client.get(url, headers={"X-ACCESS-TOKEN": "token"})

        await assert_valid_response(
            resp,
            content_type="application/json; charset=utf-8",
            schema={"accounts": {"required": True, "type": "list", "schema": account_schema}},
        )


class TestUpdateAccount:
    @pytest.mark.integration
    @pytest.mark.parametrize("json", (True, False))
    async def test_unauthorized(self, fake, aiohttp_client, app, passport, json):
        app["passport"] = passport
        client = await aiohttp_client(app)

        url = app.router.named_resources()["api.accounts.update"].url_for(account_key="1")
        payload, headers = prepare_payload({"name": fake.credit_card_provider()}, json=json)
        resp = await client.put(url, data=payload, headers=headers)

        await assert_valid_response(resp, status=401)

    @pytest.mark.integration
    @pytest.mark.parametrize("json", (True, False))
    async def test_missing(self, fake, aiohttp_client, app, passport, json):
        app["passport"] = passport
        client = await aiohttp_client(app)

        url = app.router.named_resources()["api.accounts.update"].url_for(account_key="1")
        payload, headers = prepare_payload(
            {"name": fake.credit_card_provider()}, {"X-ACCESS-TOKEN": "token"}, json
        )
        resp = await client.put(url, data=payload, headers=headers)

        await assert_valid_response(resp, status=404)

    @pytest.mark.integration
    @pytest.mark.parametrize("json", (True, False))
    async def test_success(self, fake, aiohttp_client, app, passport, json, user, account):
        app["passport"] = passport
        client = await aiohttp_client(app)

        async with app["db"].acquire() as conn:
            await prepare_accounts(conn, [account])

        url = app.router.named_resources()["api.accounts.update"].url_for(account_key=str(account.key))
        payload, headers = prepare_payload(
            {"name": fake.credit_card_provider()}, {"X-ACCESS-TOKEN": "token"}, True
        )
        resp = await client.put(url, data=payload, headers=headers)

        await assert_valid_response(resp, status=204)


class TestRemoveAccount:
    @pytest.mark.integration
    async def test_unauthorized(self, fake, aiohttp_client, app, passport):
        app["passport"] = passport
        client = await aiohttp_client(app)

        url = app.router.named_resources()["api.accounts.remove"].url_for(account_key="1")
        resp = await client.delete(url)

        await assert_valid_response(resp, status=401)

    @pytest.mark.integration
    async def test_missing(self, fake, aiohttp_client, app, passport):
        app["passport"] = passport
        client = await aiohttp_client(app)

        url = app.router.named_resources()["api.accounts.remove"].url_for(account_key="1")
        resp = await client.delete(url, headers={"X-ACCESS-TOKEN": "token"})

        await assert_valid_response(resp, status=404)

    @pytest.mark.integration
    async def test_success(self, fake, aiohttp_client, app, passport, user, account):
        app["passport"] = passport
        client = await aiohttp_client(app)

        async with app["db"].acquire() as conn:
            await prepare_accounts(conn, [account])

        url = app.router.named_resources()["api.accounts.remove"].url_for(account_key=str(account.key))
        resp = await client.delete(url, headers={"X-ACCESS-TOKEN": "token"})

        await assert_valid_response(resp, status=204)
