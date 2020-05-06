
import os, abc, enum, collections
from .preprocessor import Preprocessor
from .exceptions import EOL
from .utils import is_identifier_char
from .buf import Charbuf, Buf

# Default name for streams with no `.name` (e.g. StringIO)
DEFAULT_STREAM_NAME = 'anonymous'

class TokenFlag(enum.Flag):
    UNSPECIFIED = 0x00
    PREPRO_ONLY = 0x01 # Tokens that are meant for preprocessor only
    CONFIG_ONLY = 0x02 # Tokens that are meant for config only (e.g. cant be used as macro)
    PREPRO_CMD = 0x04
    IDENTIFIER = 0x08
    IDENTIFIER_JOINED = 0x10
    STRING = 0x20
    EOF = 0x40
    COMMENT = 0x80

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
        def _get_first(tk):
            if isinstance(tk, TokenCollection):
                return _get_first(tk[0])
            
            return tk

        td = _get_first(token)._asdict()
        td.update(**kwargs)

        return cls(*args, **td)

class TokenCollection(list):
    # TODO: Multiple units

    def __init__(self, *args, **kwargs):
        self.type = kwargs.pop('type', TokenFlag.UNSPECIFIED)

        super().__init__(*args, **kwargs)

    def __getattr__(self, attr):
        if attr in ('colno', 'lineno', 'unit'):
            try:
                return getattr(self[0], attr)
            except IndexError:
                pass

        raise NotImplementedError(attr)

    @property
    def value(self):
        return ''.join([str(x.value) for x in self])


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

class Scanner(Charbuf):
    class Types(enum.Enum):
        IDENTIFIER = 1
        SYMBOL = 2
        UNSPECIFIED = 3

    def __init__(self, stream=None, preprocess=True, pp_args={}):
        self.stream = Streambuf(stream)

        if preprocess:
            self.preprocessor = Preprocessor(self, **pp_args)
        else:
            self.preprocessor = None

        super().__init__()

    def _fill_buf(self, length):
        while len(self._buf) < length:
            self._buf.extend([x for x in self.preprocessor.process()])

    def _iter_chars(self):
        while True:
            yield self.get(1)

    def __iter__(self):
        return self

    def __next__(self):
        return self.scan()

    def make_token(self, *args, **kwargs):
        stream = self.stream.current

        kwargs.setdefault('lineno', stream['line'] + 1)
        kwargs.setdefault('colno', stream['col'] + 1)
        kwargs.setdefault('unit', stream['name'])

        return Token(*args, **kwargs)

    def scan(self):
        for char in self._iter_chars():
            if is_identifier_char(char):
                yield self.make_token(self.Types.IDENTIFIER, char + self.find_with_cb(is_identifier_char))
            elif char in ('=', ';', '{', '}' '[', ']' ':'):
                yield self.make_token(self.Types.SYMBOL, char)
            else:
                yield self.make_token(self.Types.UNSPECIFIED, char)
