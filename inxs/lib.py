"""
This module contains common functions that can be used for either :class:`Rule` s' tests, as
handler functions or simple transformation steps.

Community contributions are highly appreciated, but it's hard to layout hard criteria for what
belongs here and what not. In doubt open a pull request with your proposal as far as it proved
functional to you, it doesn't need to be polished at that point.
"""


# TODO indicate use area in function's docstrings; and whether they return something


import logging
from typing import Callable

from lxml import builder, etree

from inxs import dot_lookup, lxml_utils, Ref, REF_IDENTIFYING_ATTRIBUTE

# helpers


logger = logging.getLogger(__name__)
dbg = logger.debug
nfo = logger.info


__all__ = []


def export(func):
    __all__.append(func.__name__)
    return func


@export
def is_Ref(obj):
    return hasattr(obj, REF_IDENTIFYING_ATTRIBUTE)


# the actual lib


@export
def append(name):
    """ Appends the result of the previous :term:`handler function` to the object referenced by
        ``name`` in the :term:`context` namespace.
    """
    def handler(context, previous_result):
        dot_lookup(context, name).append(previous_result)
        return previous_result
    return handler


@export
def cleanup_namespaces(root, previous_result):
    """ Cleanup the namespaces of the root element. This should always be used at the end of a
        transformation when elements' namespaces have been changed.
    """
    etree.cleanup_namespaces(root)
    return previous_result


@export
def clear_attributes(element, previous_result):
    """ Deletes all attributes of an element. """
    element.attrib.clear()
    return previous_result


@export
def concatenate(*parts):
    """ Concatenate the given parts which may be strings or callables returning such. """
    def handler(transformation) -> str:
        result = ''
        for part in parts:
            if callable(part):
                _part = part(transformation)
            elif isinstance(part, str):
                _part = part
            else:
                raise RuntimeError('Unhandled type: {}'.format(type(part)))
            result += _part
        return result
    return handler


@export
def debug_dump_document(name='tree'):
    """ Dumps all contents of the element refrenced by ``name`` from the
        :attr:`inxs.Transformation._available_symbols` to the log at info level. """
    def handler(transformation):
        nfo(etree.tostring(transformation._available_symbols[name]))
        return transformation.states.previous_result
    return handler


@export
def debug_message(msg):
    """ Logs the provided message at info level. """
    def handler(previous_result):
        nfo(msg)
        return previous_result
    return handler


@export
def debug_symbols(*names):
    """ Logs the representation strings of the objects referenced by ``names`` in
        :attr:`inxs.Transformation._available_symbols` at info level. """
    def handler(transformation):
        for name in names:
            nfo(transformation._available_symbols[name])
        return transformation.states.previous_result
    return handler


@export
def drop_siblings(left_or_right):
    """ Removes all elements ``left`` or ``right`` of the processed element depending which
        keyword was given. The same is applied to all ancestors. Think of it like cutting a hedge
        from one side. It can be used as a processing step to strip the document to a chunk
        between two elements that don't have the same parent node.
    """
    if left_or_right == 'left':
        preceding = True
    elif left_or_right == 'right':
        preceding = False
    else:
        raise RuntimeError("'left_or_right' must be 'left' or …")

    def processor(element):
        if lxml_utils.is_root_element(element):
            return

        for sibling in element.itersiblings(preceding=preceding):
            lxml_utils.remove_element(sibling)

        parent = element.getparent()
        if parent is not None:
            processor(parent)
    return processor


@export
def f(func, *args, **kwargs):
    """ Wraps the callable ``func`` which will be called as ``func(*args, **kwargs)``, the function
        and any argument can be given as :func:`inxs.Ref`. """
    def wrapper(transformation):
        if is_Ref(func):
            _func = func(transformation)
        else:
            _func = func
        _args = ()
        for arg in args:
            if is_Ref(arg):
                _args += (arg(transformation),)
            else:
                _args += (arg,)
        _kwargs = {}
        for key, value in kwargs.items():
            if is_Ref(value):
                _kwargs[key] = value(transformation)
            else:
                _kwargs[key] = value
        return _func(*_args, **_kwargs)
    return wrapper


@export
def get_attribute(name):
    """ Gets the value of the element's attribute named ``name``. """
    def evaluator(element):
        return element.attrib.get(name)
    return evaluator


@export
def get_localname(element):
    """ Gets the element's local tag name. """
    return etree.QName(element).localname


@export
def get_text(element):
    """ Returns the text of the matched element. """
    return element.text


@export
def get_variable(name):
    """ Gets the object referenced as ``name`` from the :term:`context`. It is then available as
        symbol ``previous_result``. """
    def handler(context):
        return dot_lookup(context, name)
    return handler


@export
def has_attributes(element, _):
    """ Returns ``True`` if the element has attributes. """
    return bool(element.attrib)


@export
def has_children(element, _):
    """ Returns ``True`` if the element has descendants. """
    return bool(len(element))


@export
def has_tail(element, _):
    """ Returns ``True`` if the element has a tail. """
    return bool(element.tail)


@export
def has_text(element, _):
    """ Returns ``True`` if the element has text content. """
    return bool(element.text)


@export
def init_elementmaker(name: str = 'e', **kwargs):
    """ Adds a :class:`lxml.builder.ElementMaker` as ``name`` to the context. ``kwargs`` for its
        initialization can be passed.
    """
    if 'namespace' in kwargs and 'nsmap' not in kwargs:
        kwargs['nsmap'] = {None: kwargs['namespace']}

    def wrapped(context, previous_result):
        setattr(context, name, builder.ElementMaker(**kwargs))
        return previous_result
    return wrapped


@export
def lowercase(previous_result):
    """ Processes ``previous_result`` to be all lower case. """
    return previous_result.lower()


@export
def merge(src='previous_result', dst='root'):
    """ A wrapper around :func:`inxs.lxml_util.merge_nodes` that passes the objects
        referenced by ``src`` and ``dst``.
    """
    def handler(transformation):
        _src = transformation._available_symbols[src]
        _dst = transformation._available_symbols[dst]
        assert etree.QName(_src).text == etree.QName(_dst).text, \
            f'{etree.QName(_src).text} != {etree.QName(_dst).text}'
        lxml_utils.merge_nodes(_src, _dst)
    return handler


@export
def pop_attribute(name):
    """ Pops the element's attribute named ``name``. """
    def handler(element):
        return element.attrib.pop(name)
    return handler


@export
def put_variable(name, value=Ref('previous_result')):
    """ Puts the ``previous_result`` as ``name`` to the :term:`context` namespace. """
    def callable_handler(transformation):
        setattr(transformation.context, name, value())
        return transformation.states.previous_result

    def callable_handler_dot_lookup(transformation):
        setattr(dot_lookup(transformation.context, name), value())
        return transformation.states.previous_result

    def ref_handler(transformation):
        setattr(transformation.context, name, value(transformation))
        return transformation.states.previous_result

    def ref_handler_dot_lookup(transformation):
        setattr(dot_lookup(transformation.context, name), value(transformation))
        return transformation.states.previous_result

    def simple_handler(transformation):
        setattr(transformation.context, name, value)
        return transformation.states.previous_result

    def simple_handler_dot_lookup(transformation):
        setattr(dot_lookup(transformation.context, name), value)
        return transformation.states.previous_result

    if is_Ref(value):
        if '.' in name:
            return ref_handler_dot_lookup
        return ref_handler
    elif callable(value):
        if '.' in name:
            return callable_handler_dot_lookup
        return callable_handler
    elif '.' in name:
        return simple_handler_dot_lookup
    else:
        return simple_handler


@export
def remove_elements(references, keep_children=False, clear_ref=True):
    """ Removes all elements from the document that are referenced in a list that is available
        as ``references``. ``keep_children`` is passed to :func:`inxs.lxml_utils.remove_element`.
        The reference list is cleared afterwards if ``clear_ref`` is ``True``.
    """
    def handler(transformation):
        elements = transformation._available_symbols[references]
        for element in elements:
            lxml_utils.remove_element(element, keep_children=keep_children)
        if clear_ref:
            elements.clear()
        return transformation.states.previous_result
    return handler


@export
def resolve_xpath_to_element(*names):
    """ Resolves the objects from the context (which are supposed to be XPath expressions)
        referenced by ``names`` with the *one* element that the XPaths yield or ``None``. This is
        useful when a copied tree is processed and 'XPath pointers' are passed to the
        :term:`context` when a :class:`inxs.Transformation` is called.
    """
    def resolver(context, transformation):
        for name in names:
            xpath = getattr(context, name)
            if not xpath:
                setattr(context, name, None)
                continue
            resolved_elements = transformation.xpath_evaluator(xpath)
            if not resolved_elements:
                setattr(context, name, None)
            elif len(resolved_elements) == 1:
                setattr(context, name, resolved_elements[0])
            else:
                raise RuntimeError('More than one element matched {}'.format(xpath))
        return transformation.states.previous_result
    return resolver


@export
def set_localname(name):
    """ Sets the element's localname to ``name``. """
    def handler(element, previous_result):
        namespace = etree.QName(element).namespace
        if namespace is None:
            qname = etree.QName(name)
        else:
            qname = etree.QName(namespace, name)
        element.tag = qname.text
        return previous_result
    return handler


@export
def set_text(text):
    """ Sets the element's text to the one provided as ``text``."""
    def handler(element, previous_result):
        element.text = text
        return previous_result
    return handler


@export
def sorter(name: str = 'previous_result', key: Callable = lambda x: x):
    """ Sorts the object referenced by ``name`` in the :term:`context` using ``key`` as
        :term:`key function`.
    """
    def handler(context):
        return sorted(getattr(context, name), key=key)
    return handler


@export
def strip_attributes(*names):
    """ Strips all attributes with the keys provided as ``names`` from the element. """
    def handler(element, previous_result):
        for name in names:
            element.attrib.pop(name, None)
        return previous_result
    return handler


@export
def strip_namespace(element, previous_result):
    """ Removes the namespace from the element.
        When used, :func:`cleanup_namespaces` should be applied at the end of the transformation.
    """
    element.tag = etree.QName(element).localname
    return previous_result


@export
def sub(*args, **kwargs):
    """ A wrapper around :func:`inxs.lxml_utils.subelement` for usage as
        :term:`handler function`. """
    return f(lxml_utils.subelement, *args, **kwargs)


@export
def text_is(text):
    """ Tests whether the evaluated element's text matches ``text``. """
    def evaluator(element, _):
        return element.text == text
    return evaluator
