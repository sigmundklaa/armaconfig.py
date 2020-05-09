
import os, abc, enum, collections
from .preprocessor import Preprocessor
from .exceptions import EOL, Unexpected, UnexpectedType, UnexpectedValue
from .utils import is_identifier_char
from .buf import Charbuf, Buf

# Default name for streams with no `.name` (e.g. StringIO)
DEFAULT_STREAM_NAME = 'anonymous'

_Token = collections.namedtuple('Token', [
    'type',
    'value',
    'lineno',
    'colno',
    'unit'
])

class Token(_Token):
    def __iter__(self):
        return iter((self.type, self.value))

    def _asdict(self):
        return {f: getattr(self, f) for f in self._fields}

    @classmethod
    def from_token(cls, token, *args, **kwargs):
        td = token._asdict()
        td.update(**kwargs)

        return cls(*args, **td)

class Streambuf(Charbuf):
    CHAR_TUPLE = collections.namedtuple('CHAR_TUPLE', ['char', 'line', 'col', 'unit'])

    def __init__(self, stream=None):
        self.streams = []
        self.line_empty = True

        if stream is not None:
            if isinstance(stream, list):
                for i in stream:
                    self.add_stream(i)
            else:
                self.add_stream(stream)

        super().__init__()

    @property
    def current(self):
        return self.streams[-1]

    def add_stream(self, stream):
        if isinstance(stream, (str, os.PathLike)):
            stream = open(stream)

        self.streams.append({
            'iowrapper': stream,
            'line': 0,
            'col': 0,
            'name': getattr(stream, 'name', DEFAULT_STREAM_NAME)
        })

    def make_token(self, *args, **kwargs):
        stream = self.current

        kwargs.setdefault('lineno', stream['line'] + 1)
        kwargs.setdefault('colno', stream['col'] + 1)
        kwargs.setdefault('unit', stream['name'])

        return Token(*args, **kwargs)

    def __read(self):
        stream = self.current

        char = stream['iowrapper'].read(1)
        char_tuple = self.CHAR_TUPLE(char, stream['line'], stream['col'], stream['name'])

        if not char:
            self._eol_reached()

            return self.__read()
        elif char == '\n':
            stream['line'] += 1
            stream['col'] = 0

        return char

    def _fill_buf(self, length):
        chars = [self.__read() for _ in range(length - len(self._buf))]

        self._buf.extend(chars)

        return ''.join(chars)

    def _eol_reached(self):
        if len(self.streams) <= 1:
            raise EOL()

        self.streams.pop()

class InterScanner(Charbuf):
    def __init__(self, stream, **kwargs):
        self.stream = Streambuf(stream)
        self.preprocessor = Preprocessor(self, **kwargs)

        super().__init__()

    def _fill_buf(self, length):
        while len(self._buf) < length:
            self._buf.extend([x for x in self.preprocessor.process()])

    def __getattr__(self, *args, **kwargs):
        return getattr(self.stream, *args, *kwargs)

class Scanner(Buf):
    class Types(enum.Enum):
        IDENTIFIER = 1
        SYMBOL = 2
        UNSPECIFIED = 3

    def __init__(self, stream=None, preprocess=True, **kwargs):
        if preprocess:
            self.stream = InterScanner(stream, **kwargs)
        else:
            self.stream = Streambuf(stream)

        super().__init__()

    def _fill_buf(self, length):
        for _ in range(length - len(self._buf)):
            self._buf.append(next(self))

    def __iter__(self):
        return self

    def __next__(self):
        return self.next_token()

    def sequence(self, length, expect_typ=None, expect_val=None, **kwargs):
        def _get_expect(expect, idx):
            try:
                return expect[idx]
            except (IndexError, TypeError):
                return None

        return [
            self.next_token(
                expect_typ=_get_expect(expect_typ, idx),
                expect_val=_get_expect(expect_val, idx)
            )
            for idx in range(length)    
        ]

    def next_token(self, include_ws=False, expect_typ=None, expect_val=None):
        try:
            token = next(self.scan())
        except StopIteration:
            raise EOL()

        def _compare_expect(err, expect, got):
            if expect is not None:
                if isinstance(expect, (list, tuple)):
                    valid = got in expect
                else:
                    valid = got == expect

                if not valid:
                    raise err(expect, token)

        if not include_ws and token.type == self.Types.UNSPECIFIED and token.value.isspace():
            return self.next_token(include_ws, expect_typ, expect_val)

        _compare_expect(UnexpectedType, expect_typ, token.type)
        _compare_expect(UnexpectedValue, expect_val, token.value)

        return token

    def scan(self):
        for char in self.stream:
            if is_identifier_char(char):
                yield self.stream.make_token(self.Types.IDENTIFIER, char + self.stream.find_with_cb(is_identifier_char))
            elif char in ('=', ';', '{', '}', '[', ']' ':'):
                yield self.stream.make_token(self.Types.SYMBOL, char)
            else:
                yield self.stream.make_token(self.Types.UNSPECIFIED, char)
