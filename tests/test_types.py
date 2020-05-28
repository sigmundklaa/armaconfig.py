
import pytest
from armaconfig import loads
from armaconfig.exceptions import Unexpected


def test_array_oned():
    assert loads('oned[] = {1, two, 3, "4", 5 six seven};') == {
        'oned': [1, 'two', 3, 4, '5 six seven']
    }


def test_array_multi():
    assert loads('multi[] = {1, {2, 3}, {{4, 5, 6 seven, {}}}};') == {
        'multi': [
            1,
            [2, 3],
            [
                [4, 5, "6 seven", []]
            ]
        ]
    }


def test_array_symbol():
    with pytest.raises(Unexpected):
        loads('array[] = 1;')

    assert loads('string = {"array"};') == {'string': '{array}'}


def test_string_quoted():
    assert loads('quoted = "quoted string";') == {'quoted': 'quoted string'}


def test_string_unquoted():
    assert loads('unquoted = unquoted string;') == {
        'unquoted': 'unquoted string'}


def test_string_joined():
    assert (
        loads('joined = unquoted and "quoted" strings "joined" together;') ==
        {'joined': 'unquoted and quoted strings joined together'})


def test_string_escaped():
    assert (
        loads('escaped = "this ""string"" is ""escaped"".";') ==
        {'escaped': 'this "string" is "escaped".'})
