
import os, abc, enum, collections
from .preprocessor import Preprocessor
from .exceptions import EOL
from .utils import is_identifier_char

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



class Charbuf(abc.ABC):
    """
    Helper class that provides methods for reading chars from a buffer.
    """

    @property
    @abc.abstractmethod
    def buf(self): pass

    @abc.abstractmethod
    def _fill_buf(self, length=1): pass

    def peek(self, length=1):
        self._fill_buf(length)

        slice_ = self.buf[:length]

        return ''.join(slice_)

    def advance(self, length=1):
        del self.buf[:length]

    def get(self, length=1):
        seq = self.peek(length)

        self.advance(length)

        return seq

    def find_delim(self, delim, advance=False):
        seq = ''
        length = len(delim)

        while self.peek(length) != delim:
            seq += self.get(1)

        if advance:
            self.advance(length)

        return seq

    def find_with_cb(self, callback, length=1, advance=False):
        # TODO: Ensure this does not raise EOL
        seq = ''
        getter = self.get if advance else self.peek
        is_peek = not advance

        check = getter(length)

        while callback(check):
            seq += check
            
            if is_peek:
                self.advance(1)

            check = getter(length)

        return seq

    def peek_cb(self, callback, length=1):
        seq = ''
        offset = 0
        check = self.peek(length)

        while callback(check):
            offset += 1
            seq += check
            check = self.peek(offset + length)[offset:]

        return seq

    def get_string(self):
        """
        This method assumes that the first " has been found
        """
        def callback(char):
            if char == '"':
                if self.peek(1) != '"':
                    return False

                self.advance(1)

            return True

        return self.find_with_cb(callback, length=1, advance=True)


class StreamSet(Charbuf):
    STREAM_TUPLE = collections.namedtuple('STREAM_TUPLE', ['iowrapper', 'line', 'col', 'name'])
    buf = []

    def __init__(self, stream=None):
        self.streams = []

        if stream is not None:
            if isinstance(stream, list):
                for i in stream:
                    self.add_stream(i)
            else:
                self.add_stream(stream)

    @property
    def current(self):
        return self.streams[-1]

    def add_stream(self, stream):
        self.streams.append({
            'iowrapper': stream,
            'line': 0,
            'col': 0,
            'name': getattr(stream, 'name', DEFAULT_STREAM_NAME)
        })

    def __read(self):
        stream = self.current

        char = stream['iowrapper'].read(1)

        if not char:
            self._eol_reached()

            return self.__read()
        elif char == '\n':
            stream['line'] += 1
            stream['col'] = 0

        return char

    def _fill_buf(self, length):
        chars = [self.__read() for _ in range(length - len(self.buf))]

        self.buf.extend(chars)

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

    buf = []

    def __init__(self, stream=None, preprocess=True, pp_args={}):
        self.streamset = StreamSet(stream)

        if preprocess:
            self.preprocessor = Preprocessor(self, **pp_args)
        else:
            self.preprocessor = None

    def _fill_buf(self, length):
        while len(self.buf) <= length:
            self.buf.extend([x for x in self.preprocessor.process()])

    def iter_chars(self):
        while True:
            yield self.get(1)

    def __iter__(self):
        return self

    def __next__(self):
        return self.scan()

    def make_token(self, *args, **kwargs):
        stream = self.streamset.current

        kwargs.setdefault('lineno', stream['line'] + 1)
        kwargs.setdefault('colno', stream['col'] + 1)
        kwargs.setdefault('unit', stream['name'])

        return Token(*args, **kwargs)

    def scan(self):
        for char in self.iter_chars():
            if is_identifier_char(char):
                yield self.make_token(self.Types.IDENTIFIER, char + self.find_with_cb(is_identifier_char))
            elif char in ('=', ';', '{', '}' '[', ']' ':'):
                yield self.make_token(self.Types.SYMBOL, char)
            else:
                yield self.make_token(self.Types.UNSPECIFIED, char)
