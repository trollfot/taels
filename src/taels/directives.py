# -*- coding: utf-8 -*-
"""Some directives to link components
"""

from grokker import validator, Directive, ArgsDirective
from cromlech.browser.interfaces import IRequest, IView, ISlot
from zope.interface.interfaces import IInterface


def freeze(component, name, value):
    setattr(component, name, frozenset(value))


def class_or_interface_validator(directive_name, value):
    if (not validator.isclass(value) and
        not IInterface.providedBy(value)):
        raise validator.GrokkerValidationError(
            "The '%s' directive can only be called with a "
            "class or an interface." % directive_name)


def class_or_interface_extends(extension_core):

    def class_or_interface_extends_validator(directive_name, value):

        if IInterface.providedBy(value):
            if not value.isOrExtends(extension_core):
                raise validator.GrokkerValidationError(
                    "%r is not a valid `%s` interface." % (
                        value, extension_core.__name__))
        elif not extension_core.implementedBy(value):
            raise validator.GrokkerValidationError(
                "%r must implement the `%s` interface." % (
                    value, extension_core.__name__))

    return class_or_interface_extends_validator



request = Directive(
    'request', 'cromlech',
    validator=class_or_interface_extends(IRequest))


context = Directive(
    'context', 'cromlech', validator=class_or_interface_validator)


view = Directive(
    'view', 'cromlech',
    validator=class_or_interface_extends(IView))


slot = Directive(
    'slot', 'cromlech',
    validator=class_or_interface_extends(ISlot))


order = Directive(
    'order', 'cromlech',
    validator=validator.int_validator)


title = Directive(
    'title', 'cromlech',
    validator=validator.str_validator)


description = Directive(
    'description', 'cromlech',
    validator=validator.str_validator)


traversable = ArgsDirective(
    'traversable', 'dawnlight',
    validator=validator.str_validator, set_policy=freeze)
