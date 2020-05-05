
from typing import Union, Sequence, Any

def format_expected(e, got, got_repr):
    return 'Expected %s, got %s (%s)' % (e, got, got_repr)

class EOL(IndexError): pass

class Unexpected(Exception):
    def __init__(self, expected, got):
        super().__init__(format_expected(expected, got, repr(got)))

class UnexpectedType(TypeError, Unexpected):
    def __init__(self, expected, got):
        if isinstance(expected, (list, tuple)):
            expected = '<%s>' % (' | '.join([str(x) for x in expected]))
        else:
            expected = str(expected)

        message = format_expected(expected, str(got.type), repr(got))

        super().__init__(message)

class UnexpectedValue(ValueError, Unexpected):
    def __init__(self, expected, got):
        message = format_expected(repr(expected), repr(got.value), repr(got))

        super().__init__(message)
