import asyncio
import functools

from cerberus import Validator
from psycopg2 import ProgrammingError, IntegrityError
from aiohttp import web
import ujson

from ..exceptions import DatabaseError, SerializationError, ValidationError


def response(content: str, **kwargs) -> web.Response:
    return web.Response(body=content.encode('utf-8'), **kwargs)


def json_response(data: dict, **kwargs) -> web.Response:
    kwargs.setdefault('content_type', 'application/json')
    return web.Response(body=ujson.dumps(data).encode('utf-8'), **kwargs)


async def get_payload(request: web.Request) -> dict:
    """
    Extract payload from request by Content-Type in headers.

    Method is a coroutine.
    """
    if 'application/json' in request.content_type:
        payload = await request.json()
    else:
        payload = await request.post()
    return dict(payload)


def handle_response(f):
    @functools.wraps(f)
    async def wrapper(*args):
        internal_error = json_response({
            'errors': {'server': 'Internal error'}
        }, status=500)

        request = args[-1]

        try:
            response = await f(*args)
        except ValidationError as exc:
            return json_response({'errors': exc.errors}, status=400)
        except Exception as exc:
            if isinstance(exc, (web.HTTPClientError, )):
                raise

            if request.app.raven:
                # send error to sentry
                request.app.raven.captureException()
            return internal_error

        if isinstance(response, web.Response):
            return response

        return json_response(response)
    return wrapper


def reverse_url(request, route, parts=None):
    if not parts:
        path = request.app.router[route].url()
    else:
        path = request.app.router[route].url(parts=parts)

    return '{scheme}://{host}{path}'.format(scheme=request.scheme,
                                            host=request.host, path=path)


def allow_cors(headers=None, methods=None):
    def decorator(f):
        @functools.wraps(f)
        async def wrapper(*args):
            if asyncio.iscoroutinefunction(f):
                coro = f
            else:
                coro = asyncio.coroutine(f)
            request = args[-1]

            exclude_headers = set(name.upper() for name in {
                'Cache-Control', 'Content-Language', 'Content-Type', 'Expires',
                'Last-Modified', 'Pragma', 'Content-Length'
            })

            allow_methods = ['OPTIONS']
            if methods:
                allow_methods.extend([name.upper() for name in methods])

            response = await coro(*args)

            response.headers.update({
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': ', '.join(allow_methods)
            })

            if 'Origin' in request.headers:
                response.headers.update({
                    'Access-Control-Allow-Origin': request.headers['Origin']
                })

                expose_headers = {name for name in response.headers
                                  if name.upper() not in exclude_headers}
                if expose_headers:
                    response.headers.update({
                        'Access-Control-Expose-Headers': ', '.join(
                            expose_headers)
                    })

                if 'Access-Control-Request-Headers' in request.headers:
                    response.headers.update({
                        'Access-Control-Allow-Headers': request.headers.get(
                            'Access-Control-Request-Headers')
                    })
            return response
        return wrapper
    return decorator


class BaseHandler(object):
    decorators = tuple()
    endpoints = tuple()

    async def get_payload(self, request: web.Request) -> dict:
        if 'application/json' in request.headers.get('CONTENT-TYPE'):
            payload = await request.json()
        else:
            payload = await request.post()
        return dict(payload)

    def response(self, content: str, **kwargs) -> web.Response:
        return web.Response(body=content.encode('utf-8'), **kwargs)

    def json_response(self, content: dict, **kwargs) -> web.Response:
        kwargs.setdefault('content_type', 'application/json')
        return self.response(ujson.dumps(content), **kwargs)


class BaseAPIHandler(BaseHandler):
    limit = None

    collection_name = ''
    resource_name = ''

    table = None
    schema = None
    serializer = None

    def get_collection_query(self, request):
        return self.table.select()

    def get_instance_query(self, request, instance_id):
        return self.table.select().where(self.table.c.id == instance_id)

    def get_instance_id(self, request):
        instance_id = request.match_info['instance_id']

        try:
            instance_id = int(instance_id)
        except ValueError:
            raise web.HTTPBadRequest(
                text="%s invalid instance id" % instance_id)
        else:
            return instance_id

    @asyncio.coroutine
    def get_collection(self, request):
        instances = []
        with (yield from request.app.engine) as conn:
            query = self.get_collection_query(request)
            if self.limit:
                query = query.limit(self.limit)
            result = yield from conn.execute(query)

            if result.returns_rows:
                rows = yield from result.fetchall()
                instances = [dict(zip(row.keys(), row.values()))
                             for row in rows]
        return instances

    @asyncio.coroutine
    def create_instance(self, request, document) -> tuple:
        with (yield from request.app.engine) as conn:
            try:
                query = self.table.insert().values(**document)
                uid = yield from conn.scalar(query)
            except IntegrityError as exc:
                return None, {'IntegrityError': exc.args[0]}
            except ProgrammingError as exc:
                return None, {'ProgrammingError': exc.args[0]}
            else:
                document.update(id=uid)
                return document, {}

    async def after_create_instance(self, request, instance):
        pass

    @asyncio.coroutine
    def get_instance(self, request, instance_id):
        instance = None

        with (yield from request.app.engine) as conn:
            query = self.get_instance_query(request, instance_id)
            result = yield from conn.execute(query)

            row = yield from result.fetchone()

            if row:
                instance = dict(zip(row.keys(), row.values()))

        return instance

    @asyncio.coroutine
    def update_instance(self, request, payload, document):
        with (yield from request.app.engine) as conn:
            try:
                query = self.table.update().where(self.table.c.id == document.get('id')).values(**payload)
                result = yield from conn.execute(query)
            except IntegrityError as exc:
                return None, {'IntegrityError': exc.args[0]}
            except ProgrammingError as exc:
                return None, {'ProgrammingError': exc.args[0]}
            else:
                if result.rowcount:
                    return document, {}
                else:
                    raise web.HTTPNotFound(
                        text='%s not found' % self.resource_name)

    async def after_update_instance(self, request, instance, before):
        pass

    @asyncio.coroutine
    def remove_instance(self, request, instance):
        with (yield from request.app.engine) as conn:
            query = self.table.delete().where(self.table.c.id == instance['id'])
            result = yield from conn.execute(query)
        if not result.rowcount:
            raise web.HTTPNotFound(text='%s not found' % self.resource_name)

    async def after_remove_instance(self, request, instance):
        pass

    async def validate_payload(self, request, payload, instance=None):
        schema = self.schema
        if instance:
            schema = {}
            for key in iter(payload.keys()):
                schema[key] = self.schema[key]

        validator = Validator(schema=schema)
        if instance:
            validator.allow_unknown = True

        if not validator.validate(instance or payload):
            return None, validator.errors

        return validator.document, None

    @allow_cors(methods=('GET', ))
    async def get(self, request):
        if 'instance_id' in request.match_info:
            instance_id = self.get_instance_id(request)
            instance = await self.get_instance(request, instance_id)

            if instance:
                resource, errors = self.serializer.dump(instance, many=False)
                response = {self.resource_name: resource}
            else:
                raise web.HTTPNotFound(text='%s not found' % self.resource_name)
        else:
            instances = await self.get_collection(request)
            collection, errors = self.serializer.dump(instances, many=True)

            response = {
                self.collection_name: collection,
                'meta': {'total': len(collection)}
            }

            if self.limit:
                response['meta']['limit'] = self.limit

        return self.json_response(response)

    @asyncio.coroutine
    async def post(self, request):
        payload = await self.get_payload(request)

        document, errors = await self.validate_payload(request, payload)
        if errors:
            return self.json_response({'errors': errors}, status=400)

        instance, errors = await self.create_instance(request, document)
        if errors:
            return self.json_response({'errors': errors}, status=400)

        await self.after_create_instance(request, instance)

        response, errors = self.serializer.dump(instance, many=False)
        return self.json_response({self.resource_name: response}, status=201)

    @asyncio.coroutine
    async def put(self, request):
        instance_id = self.get_instance_id(request)
        original = await self.get_instance(request, instance_id)
        if not original:
            raise web.HTTPNotFound(text='%s not found' % self.resource_name)

        payload = await self.get_payload(request)
        instance = original.copy()
        instance.update(**payload)

        document, errors = await self.validate_payload(request, payload,
                                                            instance)
        if errors:
            return self.json_response({'errors': errors}, status=400)

        instance, errors = await self.update_instance(request, payload,
                                                           document)
        if errors:
            return self.json_response({'errors': errors}, status=400)

        await self.after_update_instance(request, instance, original)

        response, errors = self.serializer.dump(instance, many=False)
        return self.json_response({self.resource_name: response})

    @allow_cors(methods=('DELETE', ))
    async def delete(self, request):
        instance_id = self.get_instance_id(request)
        instance = await self.get_instance(request, instance_id)
        if not instance:
            raise web.HTTPNotFound(text='%s not found' % self.resource_name)

        await self.remove_instance(request, instance)
        await self.after_remove_instance(request, instance)

        return web.Response(text='removed')
