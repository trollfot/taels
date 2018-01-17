# -*- coding: utf-8 -*-

from zope.interface import Attribute, Interface
from zope.interface.common.mapping import IMapping


class IPredicate(Interface):
    """A predicate is a component registered based on the implementedBy
    and not the providedBy. Example : an adapter or a subscription for
    a class.
    """
    pass


class ISession(IMapping):
    """A session mapping, used to handle session datas.
    """
    pass


class IRequest(Interface):
    """A request represents the application input medium: the HTTP request.
    This kind of request is usually used by webservices, websites or
    other interoperable applications/components.
    """
    pass


class IResponse(Interface):
    pass


class IResponseFactory(Interface):
    """A response factory.
    """

    def __call__():
        """Returns a IResponse object.
        """


class IView(Interface):
    """Indicates that a component is a view.

    The publisher tries to adapt the context and request
    to an IView. After this, the publisher will try to
    adapt the resulting IView to IResponseFactory.

    The component that implements this interface will therefore have
    to implement IResponseFactory or alternatively an adapter should
    exist that knows how to convert this component to an IResponseFactory.
    """


class IRenderable(Interface):
    """A view-like object that uses a two-phase strategy for rendering.

    When a renderable is rendered, first the update method is called
    to prepare it for rendering. After this, the render method is used
    to actually render the view. The render method returns either a
    unicode string with the rendered content, or an IResponse object.
    """

    def update():
        """Prepares the rendering.
        """

    def render():
        """Returns the raw data.
        """


class ISlot(Interface):
    """A group-like item that acts like a components' hub.
    """


class IViewSlot(ISlot, IRenderable):
    """A fragment of a view, acting as an aggregator of sub-renderers.
    """
    view = Attribute("Renderer on which the slot is called.")


class ILayout(Interface):
    """A layout serves as a content decoration. Mainly used to maintain
    a site identity, it can be used as a simple renderer. Its `render`
    method uses the `content` argument as the content to be wrapped.
    """

    def __call__(content, **layout_environ):
        """Wraps the content into a 'decoration'. The `layout_environ`
        dict can contain additional data helping to render this component.
        """


class IForm(Interface):
    """Forms specific attributes.
    """
    postOnly = Attribute(
        u"Boolean indicating whether we only accept Post requests")
    formMethod = Attribute(u"Form method as a string")
    enctype = Attribute(u"Encoding type")


class ITemplate(Interface):
    """a template
    """

    def render(component, translate=None, **namespace):
        """Renders the given component.
        """


class IURL(Interface):
    """Component in charge of computing and object URL.
    """

    def __str__():
        """Returns the URL if possible. Else, it raises a ValueError,
        precising what is missing for the resolution.
        """


class ITraverser(Interface):
    """An interface to traverse using a namespace eg. ++mynamespace++myid
    """

    def traverse(namespace, identifier):
        """Do the traversing of namespace searching for identifier
        """


class IPublisher(Interface):
    """Defines the component in charge of the publication process.
    It usually returns an `IResponse` object.
    """


class IPublicationRoot(Interface):
    """Marker interface for the root of the publication process.
    This marker is usually applied by the publisher or the process
    that start the publication.

    This marker can be used to stop the iteration when calculating
    the lineage of an object in the application tree.
    """
