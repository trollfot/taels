# -*- coding: utf-8 -*-

from functools import partial
from .request import Request
from sanic.config import Config
from sanic.server import serve, serve_multiple, HttpProtocol, Signal
from sanic.websocket import WebSocketProtocol, ConnectionClosed
from ssl import create_default_context, Purpose


def run(host, port, request_handler, error_handler,
        ssl=None, sock=None, loop=None, debug=False,
        before_start=(), after_start=(),
        before_stop=(), after_stop=()):
    
    if isinstance(ssl, dict):
        # try common aliaseses
        cert = ssl.get('cert') or ssl.get('certificate')
        key = ssl.get('key') or ssl.get('keyfile')
        if cert is None or key is None:
            raise ValueError("SSLContext or certificate and key required.")
        context = create_default_context(purpose=Purpose.CLIENT_AUTH)
        context.load_cert_chain(cert, keyfile=key)
        ssl = context

    config = Config(load_env=True)
    server_settings = {
        'protocol': HttpProtocol,
        'request_class': Request,
        'is_request_stream': False,
        'host': host,
        'port': port,
        'sock': sock,
        'ssl': ssl,
        'signal': Signal(),
        'debug': debug,
        'request_handler': request_handler,
        'error_handler': error_handler,
        'request_timeout': config.REQUEST_TIMEOUT,
        'response_timeout': config.RESPONSE_TIMEOUT,
        'keep_alive_timeout': config.KEEP_ALIVE_TIMEOUT,
        'request_max_size': config.REQUEST_MAX_SIZE,
        'keep_alive': config.KEEP_ALIVE,
        'loop': loop,
        'before_start': before_start,
        'after_start': after_start,
        'before_stop': before_stop,
        'after_stop': after_stop,
        'register_sys_signals': True,
        'backlog': 100,
        'access_log': True,
        'websocket_max_size': config.WEBSOCKET_MAX_SIZE,
        'websocket_max_queue': config.WEBSOCKET_MAX_QUEUE,
        'graceful_shutdown_timeout': config.GRACEFUL_SHUTDOWN_TIMEOUT
    }
    serve(**server_settings)


def run_app(app, host="127.0.0.1", port=8000, sock=None, loop=None):

    run(
        host="0.0.0.0", port=8080,
        request_handler=app.request_handler,
        error_handler=app.error_handler,
        before_start=app.listeners['before_start'],
        after_start=app.listeners['after_start'],
        before_stop=app.listeners['before_stop'],
        after_stop=app.listeners['after_stop'],
        debug=app.debug,
        sock=None,
        loop=None,
    )
