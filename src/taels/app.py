# -*- coding: utf-8 -*-

from functools import partial
from collections import deque
from sanic.handlers import ErrorHandler
from sanic.response import HTTPResponse, StreamingHTTPResponse
from sanic.exceptions import SanicException
from sanic.log import logger, error_logger, LOGGING_CONFIG_DEFAULTS
from inspect import isawaitable


class Taels:

    def __init__(self, name, router=None, publisher=None, debug=True):
        self.name = name
        self.router = router
        self.publisher = publisher
        self.error_handler = ErrorHandler()
        self.debug = debug
        self.websocket_enabled = False

        self.listeners = {
            'after_start': deque(),
            'after_stop': deque(),
            'before_start': deque(),
            'before_stop': deque(),
        }

        self.subscribers = {
            'request': deque(),
            'response': deque(),
        }

    def register_listener(self, target, handler):
        listeners = self.listeners.get(target)
        if listeners is None:
            raise KeyError(
                '{} is not a valid listener key.'.format(target))
        if target.startswith('after'):
            listeners.appendleft(partial(handler, self))
        else:
            listeners.append(partial(handler, self))

    def register_subscribers(self, target, handler):
        subscribers = self.subscribers.get(target)
        if subscribers is None:
            raise KeyError(
                '{} is not a valid subscription key.'.format(target))
        if target.startswith('after'):
            subscribers.appendleft(handler)
        else:
            subscribers.append(handler)

    async def notify(self, target, *args, **kwargs):
        default = kwargs.get('default', None)
        if target in self.subscribers and self.subscribers[target]:
            for susbcription in self.subscribers[target]:
                result = susbcription(*args, **kwargs)
                if isawaitable(result):
                    result = await result
                    if result is not None:
                        return result
        return default

    async def request_handler(self, request, write_callback, stream_callback):
        try:
            request.app = self            
            response = await self.notify('request', self, request)
            if response is None:
                if self.router is not None:
                    # do routing
                    pass

                if self.publisher is not None:
                    response = self.publisher(request)
                    if isawaitable(response):
                        response = await response

        except Exception as e:
            try:
                response = self.error_handler.response(request, e)
                if isawaitable(response):
                    response = await response
            except Exception as e:
                if isinstance(e, SanicException):
                    response = self.error_handler.default(
                        request=request, exception=e)
                elif self.debug:
                    response = HTTPResponse(
                        "Error while handling error: {}\nStack: {}".format(
                            e, format_exc()), status=500)
                else:
                    response = HTTPResponse(
                        "An error occurred while handling an error",
                        status=500)
        finally:
            try:
                response = await self.notify(
                    'response', self, response, default=response)
            except BaseException:
                error_logger.exception(
                    'Exception occurred in one of response middleware handlers'
                )

        # pass the response to the correct callback
        if isinstance(response, StreamingHTTPResponse):
            await stream_callback(response)
        else:
            write_callback(response)
