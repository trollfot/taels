# -*- coding: utf-8 -*-

import os
import logging.config

from collections import namedtuple
from functools import partial, wraps
from collections import deque
from inspect import isawaitable

from taels_server import server
from taels_server.config import Config as BASE_CONFIG
from taels_server.protocols.http import HttpProtocol
from taels_server.http.response import text, HTTPResponse, StreamingHTTPResponse
from taels_server.http.handlers import ErrorHandler
from taels_server.http.request import Request
from taels_server.http.exceptions import HTTPException, ServerError
from taels_server.log import logger, error_logger, LOGGING_CONFIG_DEFAULTS


def server_configuration(
        app, listeners=None, host=None, port=None, ssl=None, sock=None,
        loop=None, protocol=HttpProtocol, backlog=100,
        register_sys_signals=True, run_async=False, access_log=True,
        debug=False, auto_reload=False):
    """Run the HTTP Server and listen until keyboard interrupt or term
    signal. On termination, drain connections before closing.
    :param host: Address to host on
    :param port: Port to host on
    :param ssl: SSLContext, or location of certificate and key
                for SSL encryption of worker(s)
    :param sock: Socket for the server to accept connections from
    :param backlog:
    :param debug:
    :param register_sys_signals:
    :param protocol: Subclass of asyncio protocol class
    :return: Nothing
    """   

    if not (bool(sock) ^ bool(host)):
        raise RuntimeError('Define either sock or host, not both.')
    elif sock is None:
        host, port = host or "127.0.0.1", port or 8000

    if isinstance(ssl, dict):
        # try common aliaseses
        cert = ssl.get('cert') or ssl.get('certificate')
        key = ssl.get('key') or ssl.get('keyfile')
        if cert is None or key is None:
            raise ValueError("SSLContext or certificate and key required.")
        context = create_default_context(purpose=Purpose.CLIENT_AUTH)
        context.load_cert_chain(cert, keyfile=key)
        ssl = context

    server_settings = {
        'protocol': protocol,
        'host': host,
        'port': port,
        'sock': sock,
        'ssl': ssl,
        'debug': debug,
        'loop': loop,
        'register_sys_signals': register_sys_signals,
        'backlog': backlog,
        'access_log': access_log,
        'listeners': listeners,
        'request_class': app.request_class,
        'is_request_stream': app.is_request_stream,
        'request_handler': app.request_handler,
        'error_handler': app.error_handler,
        'request_timeout': app.config.REQUEST_TIMEOUT,
        'response_timeout': app.config.RESPONSE_TIMEOUT,
        'keep_alive_timeout': app.config.KEEP_ALIVE_TIMEOUT,
        'request_max_size': app.config.REQUEST_MAX_SIZE,
        'keep_alive': app.config.KEEP_ALIVE,
        'websocket_max_size': app.config.WEBSOCKET_MAX_SIZE,
        'websocket_max_queue': app.config.WEBSOCKET_MAX_QUEUE,
        'websocket_read_limit': app.config.WEBSOCKET_READ_LIMIT,
        'websocket_write_limit': app.config.WEBSOCKET_WRITE_LIMIT,
        'graceful_shutdown_timeout': app.config.GRACEFUL_SHUTDOWN_TIMEOUT
    }

    if run_async:
        server_settings['run_async'] = True

    # Serve
    if host and port and os.environ.get('SERVER_RUNNING') != 'true':
        proto = "http"
        if ssl is not None:
            proto = "https"
        logger.info('Goin\' Fast @ {}://{}:{}'.format(proto, host, port))

    return server_settings


Handler = namedtuple('handler', ['callable', 'order', 'type'])


class HandlersRegistry:

    def __init__(self):
        self.middlewares = {}
        self.listeners = {}
    
    def add_handler(self, collection, type, callable, order=None):
        handler = Handler(callable=callable, order=order, type=type)
        handlers = collection.setdefault(type, [])
        if not handler in handlers:
            handlers.append(handler)
            return True
        return False

    def get_handlers(self, collection, type, reverse=False):
        def getKey(handler):
            return handler.order
        handlers = collection.get(type, None)
        if handlers is None:
            return []

        if not reverse:
            return sorted(handlers, key=getKey)
        return reversed(sorted(handlers, key=getKey))

    def add_listener(self, event, handler, order=None):
        self.add_handler(self.listeners, event, handler, order)

    def add_middleware(self, type, handler, order=None):
        self.add_handler(self.middlewares, type, handler, order)
    
    def get_listeners(self, event, reverse=False):
        return (
            handler.callable for handler in
            self.get_handlers(self.listeners, event, reverse=reverse))

    def get_middlewares(self, type, reverse=False):
        return (
            handler.callable for handler in
            self.get_handlers(self.middlewares, type, reverse=reverse))

    def listener(self, event, order=None):
        """Listener decorator.
        """
        def register_listener(handler):
            self.add_handler(self.listeners, event, handler, order)
            return handler
        return register_listener
        
    def middleware(self, type, order=None):
        """Listener decorator.
        """
        def register_middleware(handler):
            self.add_handler(self.middlewares, type, handler, order)
            return handler
        return register_middleware

    async def run_middlewares(self, type, *args, **kwargs):
        default = kwargs.pop('default', None)
        reverse = kwargs.pop('reverse', None)
        middlewares = self.get_middlewares(type, reverse=reverse)
        if middlewares:
            for middleware in middlewares:
                response = middleware(*args, **kwargs)
                if isawaitable(response):
                    response = await response
                if response:
                    # If there's any response, we break the loop and return.
                    return response
        return default


class Taels(HandlersRegistry):

    def __init__(
            self, name,
            websocket_enabled=False, request_class=Request,
            error_handler=None, config=None):
        super().__init__()
        self.__name__ = name
        self.is_request_stream = False
        self.error_handler = error_handler or ErrorHandler()
        self.config = config or BASE_CONFIG()
        self.websocket_enabled = websocket_enabled
        self.request_class = request_class

    async def request_handler(self, request, write_callback, stream_callback):
        """Take a request from the HTTP Server and return a response object
        to be sent back The HTTP Server only expects a response object, so
        exception handling must be done here
        :param request: HTTP Request object
        :param write_callback: Synchronous response function to be
            called with the response as the only argument
        :param stream_callback: Coroutine that handles streaming a
            StreamingHTTPResponse if produced by the handler.
        :return: Nothing
        """
        try:
            request.app = self
            response = await self.run_middlewares('request', request)
            if response is None:
                response = text('FIX ME')
                if isawaitable(response):
                    response = await response
        except Exception as e:
            try:
                response = self.error_handler.response(request, e)
                if isawaitable(response):
                    response = await response
            except Exception as e:
                if isinstance(e, HTTPException):
                    response = self.error_handler.default(request=request,
                                                          exception=e)
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
                response = await self.run_middlewares(
                    'response', request, response,
                    default=response, reverse=True)

            except BaseException:
                error_logger.exception(
                    'Exception occurred in one of response middleware handlers'
                )

        # pass the response to the correct callback
        if isinstance(response, StreamingHTTPResponse):
            await stream_callback(response)
        else:
            write_callback(response)

    def run(self, workers=1, auto_reload=False, **kwargs):
        configuration = server_configuration(
            self, listeners=self.listeners, **kwargs)
        try:
            if workers == 1:
                if auto_reload and os.name != 'posix':
                    # This condition must be removed after implementing
                    # auto reloader for other operating systems.
                    raise NotImplementedError
            
                if auto_reload and \
                   os.environ.get('SERVER_RUNNING') != 'true':
                    reloader_helpers.watchdog(2)
                else:
                    server.serve(**configuration)
            else:
                server.serve_multiple(configuration, workers)
        except BaseException:
            error_logger.exception(
                'Experienced exception while trying to serve')
            raise
        finally:
            logger.info("Server Stopped")
