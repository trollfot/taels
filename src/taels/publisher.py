# -*- coding: utf-8 -*-

import crom
import dawnlight

from copy import copy
from crom.registry import Registry
from dawnlight import ResolveError
from dawnlight.interfaces import IConsumer
from grokker import validator, ArgsDirective
from sanic.request import Request
from sanic.response import BaseHTTPResponse as Response
from urllib.parse import unquote
from zope.interface import Interface
from zope.location import ILocation, LocationProxy, locate
from .directives import traversable
from .interfaces import IResponseFactory, ITraverser, IView


shortcuts = {
    '@@': dawnlight.VIEW,
    }


dawnlight_components = Registry()
_marker = object()


@crom.subscription
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.order(1100)
@crom.registry(dawnlight_components)
async def attribute_consumer(request, obj, stack):
    traversables_attrs = traversable.get(obj)
    if traversables_attrs:
        ns, name = stack[0]
        if ns == dawnlight.DEFAULT and name in traversables_attrs:
            attr = getattr(obj, name, _marker)
            if attr is not _marker:
                _ = stack.popleft()
                return True, attr, stack
    return False, obj, stack


@crom.subscription
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.order(1000)
@crom.registry(dawnlight_components)
async def item_consumer(request, obj, stack):
    if hasattr(obj, '__getitem__'):
        ns, name = stack[0]
        if ns == dawnlight.DEFAULT:
            try:
                item = obj[name]
                _ = stack.popleft()
                return True, item, stack
            except (KeyError, TypeError):
                pass
    return False, obj, stack


@crom.subscription
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.order(900)
@crom.registry(dawnlight_components)
async def traverser_consumer(request, obj, stack):
    ns, name = stack[0]
    traverser = ITraverser(obj, request, name=ns, default=None)
    if traverser is not None:
        item = traverser.traverse(ns, name)
        if item is not None:
            _ = stack.popleft()
            return True, item, stack
    return False, obj, stack


async def model_lookup(request, obj, stack):
    unconsumed = copy(stack)  # using copy. py3.5+ can use stack.copy()
    consumers = IConsumer.subscription(
        obj, lookup=dawnlight_components, subscribe=False)
    
    while unconsumed:
        for consumer in consumers:
            found, obj, unconsumed = await consumer(request, obj, unconsumed)
            if found:
                break
        else:
            # nothing could be consumed
            return obj, unconsumed
    return obj, unconsumed


def view_lookup(lookup):
    async def resolve_view(request, obj, stack):
        default_fallback = False
        unconsumed_amount = len(stack)
        if unconsumed_amount > 1:
            raise ResolveError(
                "Can't resolve view: stack is not fully consumed.")

        if unconsumed_amount == 0:
            default_fallback = True
            ns, name = dawnlight.VIEW, 'index'
        elif unconsumed_amount == 1:
            ns, name = stack[0]
            if ns not in (dawnlight.DEFAULT, dawnlight.VIEW):
                raise ResolveError(
                    "Can't resolve view: namespace %r is not supported." % ns)

        view = await lookup(request, obj, name)
        if view is None:
            if default_fallback:
                raise ResolveError(
                    "Can't resolve view: no default view on %r." % obj)
            else:
                if ns == dawnlight.VIEW:
                    raise ResolveError(
                        "Can't resolve view: no view `%s` on %r." % (name, obj))
                raise ResolveError(
                    "%r is neither a view nor a model." % name)
        return view
    return resolve_view


class Publisher:

    def __init__(self, model_lookup, view_lookup):
        self.model_lookup = model_lookup
        self.view_lookup = view_lookup

    async def publish(self, request, root):
        path = unquote(request.path)
        stack = dawnlight.parse_path(path, shortcuts)

        model, crumbs = await self.model_lookup(request, root, stack)
        if isinstance(model, Response):
            # The found object can be returned safely.
            return model

        if IResponseFactory.providedBy(model):
            return await model()

        # The model needs an renderer
        component = await self.view_lookup(request, model, crumbs)

        if component is None:
            raise PublicationError('%r can not be rendered.' % model)

        # This renderer needs to be resolved into an IResponse
        factory = IResponseFactory(component)
        return await factory()

    async def __call__(self, request, root):
        try:
            response = await self.publish(request, root)
            return response
        except Exception as exc:
            errorview = IResponseFactory(request, exc, default=None)
            if errorview is not None:
                return errorview()
            raise exc
