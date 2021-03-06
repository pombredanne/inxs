from types import SimpleNamespace

from lxml import builder, etree
from pytest import mark


from inxs import lib, Ref, Rule, Transformation
from tests import equal_subtree


def test_clear_attributes():
    element = etree.Element('root', {'foo': 'bar'})
    lib.clear_attributes(element, None)
    assert element.attrib == {}


def test_concatenate():
    transformation = SimpleNamespace(_available_symbols={'foo': 'bar'})
    assert lib.concatenate('foo', Ref('foo'))(transformation) == 'foobar'


def test_merge():
    source = etree.fromstring('<root><a><bb/></a><b/></root>')
    destination = etree.fromstring('<root><a><aa/></a><b/><c/></root>')
    expected = etree.fromstring('<root><a><aa/><bb/></a><b/><c/></root>')
    transformation = Transformation(lib.merge('source'), context={'source': source})
    equal_subtree(transformation(destination), expected)


@mark.parametrize('ns,expected', ((None, 'rosa'), ('spartakus', '{spartakus}rosa')))
def test_set_localname(ns, expected):
    if ns:
        kwargs = {'namespace': ns, 'nsmap': {None: ns}}
    else:
        kwargs = {}
    element = builder.ElementMaker(**kwargs).karl()

    lib.set_localname('rosa')(element, None)
    assert etree.QName(element).text == expected


def test_strip_attributes():
    element = etree.Element('root', {'a': 'a', 'b': 'b'})
    lib.strip_attributes('b')(element, None)
    assert element.attrib == {'a': 'a'}


def test_strip_namespace():
    namespace = 'http://www.example.org/ns/'
    e = builder.ElementMaker(namespace=namespace, nsmap={'x': namespace})
    root = e.div()
    t = Transformation(
        Rule(namespace, lib.strip_namespace)
    )
    result = t(root)
    assert result.tag == 'div'
