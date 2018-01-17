# -*- coding: utf-8 -*-

from .interfaces import IRequest
from sanic.request import Request as BaseRequest
from zope.interface import implementer


@implementer(IRequest)
class Request(BaseRequest):
    __slots__ = (
        'app', 'headers', 'version', 'method', '_cookies', 'transport',
        'body', 'parsed_json', 'parsed_args', 'parsed_form', 'parsed_files',
        '_ip', '_parsed_url', 'uri_template', 'stream', '_remote_addr',
        '_socket', '_port', 'security_policy', 'principal',
    )

    def __init__(self, *args, **kwargs):
        super(Request, self).__init__(*args, **kwargs)
        self.principal = None
        self.security_policy = None
