
import pytest
from armaconfig import loads
from armaconfig.exceptions import UnexpectedType, UnexpectedValue


def test_missing_eq():
    with pytest.raises(UnexpectedValue):
        loads('prop } "3";')


def test_class_opener():
    with pytest.raises(UnexpectedValue):
        loads('class test [property = 3;};')


def test_class_closer():
    with pytest.raises(UnexpectedType):
        loads('class test {property = 3;];')


def test_array_opener():
    with pytest.raises(UnexpectedValue):
        loads('array[] = [2, 1};')
