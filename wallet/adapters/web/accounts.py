from typing import Any, Dict

from aiohttp import web

from wallet.adapters.web import get_instance_id, get_payload, json_response
from wallet.adapters.web.users import user_required
from wallet.domain.entities import Account
from wallet.services.accounts import AccountQuery, AccountsService, AccountValidator
from wallet.storage import DBStorage


def serialize_account(instance: Account) -> Dict[str, Any]:
    balance = instance.balance[0]

    return {
        "id": instance.key,
        "name": instance.name,
        "balance": {
            "incomes": float(balance.incomes),
            "expenses": float(balance.expenses),
            "rest": float(balance.rest),
        },
    }


@user_required
async def register(request: web.Request) -> web.Response:
    validator = AccountValidator()

    payload = await get_payload(request)
    document = validator.validate_payload(payload)

    async with request.app["db"].acquire() as conn:
        storage = DBStorage(conn)

        service = AccountsService(storage)
        account = await service.register(name=document["name"], user=request["user"])

    return json_response({"account": serialize_account(account)}, status=201)


@user_required
async def search(request: web.Request) -> web.Response:
    async with request.app["db"].acquire() as conn:
        storage = DBStorage(conn)

        query = AccountQuery(user=request["user"])
        accounts = await storage.accounts.find(query=query)

    return json_response({"accounts": [serialize_account(account) for account in accounts]})


async def get_account(request: web.Request, storage: DBStorage, key: str) -> Account:
    query = AccountQuery(user=request["user"], key=get_instance_id(request, key))
    accounts = await storage.accounts.find(query=query)

    if not accounts:
        raise web.HTTPNotFound()

    return accounts[0]


@user_required
async def balance(request: web.Request) -> web.Response:
    async with request.app["db"].acquire() as conn:
        storage = DBStorage(conn)

        account = await get_account(request, storage, "account_key")

    response = {
        "balance": [
            {
                "incomes": float(item.incomes),
                "expenses": float(item.expenses),
                "rest": float(item.rest),
                "month": item.month.strftime("%Y-%m-%d"),
            }
            for item in account.balance
        ]
    }

    return json_response(response)


@user_required
async def update(request: web.Request) -> web.Response:
    validator = AccountValidator()

    payload = await get_payload(request)
    document = validator.validate_payload(payload)

    async with request.app["db"].acquire() as conn:
        storage = DBStorage(conn)

        account = await get_account(request, storage, "account_key")
        if "name" in document:
            account.name = document["name"]
            await storage.accounts.update(account, fields=("name",))

    return web.Response(status=204)


@user_required
async def remove(request: web.Request) -> web.Response:
    async with request.app["db"].acquire() as conn:
        storage = DBStorage(conn)

        account = await get_account(request, storage, "account_key")
        await storage.accounts.remove(account)

    return web.Response(status=204)