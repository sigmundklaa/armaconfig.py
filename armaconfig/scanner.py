
import os, enum, collections

class EOL(IndexError): pass

class TokenType(enum.Enum):
    UNKNOWN = 0
    STRING = 1
    PREPRO = 2
    IDENTIFIER = 3
    EOL = 4
    ARROW_STRING = 5
    DOUBLE_HASH = 6

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

class TokenCollection(list):
    # TODO: Multiple units

    def __init__(self, *args, **kwargs):
        self.type = kwargs.pop('type', TokenType.UNKNOWN)

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

class Scanner:
    def __init__(self, unit):
        self._lines_buf = [] # Cache for peeking

        if isinstance(unit, (str, os.PathLike)):
            self._unit = unit
            self._stream = open(self._unit)
        else:
            self._stream = unit
            self._unit = self._stream.name

        self._lineno = 0
        self._cursor = 0

    def __del__(self):
        stream = getattr(self, '_stream', None)

        if stream and not stream.closed:
            stream.close()

    @property
    def line(self):
        return self._get_line(self._lineno)

    def _newline(self):
        if self._lines_buf: self._lines_buf.pop(0)

        self._lineno += 1
        
        if not self._lines_buf:
            self._add_lines(1)    

    def _add_lines(self, idx):
        # offset is index 0 in self._lines
        # 
        #   586          581                    3 ([581, 582, 583])
        # lineno - self._line_buf_offset > len(self._lines)
        #   586  -       581         = 5
        # 
        # for i from 0 to (5 - 3) + 1:
        #   add line
        #
        # adds 3 lines (0, 1 ,2)
        # adds 584, 585, 586
        for _ in range(idx):
            self._lines_buf.append(self._stream.readline())

    # 584 - 583
    # 1 >= 1
    # 1 - 1 + 1
    # 
    def _get_line(self, lineno):
        idx = lineno - self._lineno

        if idx >= len(self._lines_buf):
            self._add_lines((idx - len(self._lines_buf)) + 1)

        line = self._lines_buf[idx]

        #if line == '': raise EOL()

        return line

    def _advance(self, length=1):
        assert length >= 0, 'Can only advance forward (negative length given)'

        self._cursor += length
        
        line_length = len(self.line)

        if self._cursor >= line_length:
            self._newline()
            self._cursor = max(self._cursor - line_length, 0)

        #if self._lineno - self._line_buf_offset > len(self._lines):
            #raise StopIteration

        return self

    def _peek(self, length=1):
        line_length = len(self.line)

        if self._cursor + length > line_length:
            remainder = self._cursor + length - line_length
            seq = ''
            curline_idx = self._lineno

            while True:
                nxt_line = self._get_line(curline_idx + 1)
                line_len = len(nxt_line)

                # If length is 0, meaning EOF, break and raise EOL
                if not (line_len): break

                if remainder >= line_len:
                    seq += nxt_line
                else:
                    seq += nxt_line[:remainder]
                    
                    return self.line[self._cursor:] + seq

            raise EOL()

        return self.line[self._cursor:self._cursor + length]

    def _get_raw(self, length=1):
        seq = self._peek(length)

        self._advance(length)

        return seq

    def _find_delim(self, delim, advance=False):
        seq = ''
        length = len(delim)

        while self._peek(length) != delim:
            seq += self._get_raw(1)

        if advance:
            self._advance(length)

        return seq

    def _find_with_cb(self, callback, length=1, advance=False):
        seq = ''
        getter = self._get_raw if advance else self._peek
        is_peek = not advance

        check = getter(length)

        while callback(check):
            seq += check
            
            if is_peek:
                self._advance(1)

            check = getter(length)

        #if advance: self._advance(1)

        return seq

    def _get_string(self):
        """
        This method assumes that the first " has been found
        """
        def callback(char):
            if char == '"':
                if self._peek(1) != '"':
                    return False

                self._advance(1)

            return True

        return self._find_with_cb(callback, length=1, advance=True)

    def is_identifier_char(self, char):
        return char.isalnum() or char == '_'

    def _iter_chars(self):
        while True:
            yield self._get_raw()

    def __iter__(self):
        return self

    def __next__(self):
        return self.scan()

    def _make_token(self, *args, **kwargs):
        kwargs.setdefault('lineno', self._lineno + 1)
        kwargs.setdefault('colno', self._cursor + 1)
        kwargs.setdefault('unit', self._unit)

        return Token(*args, **kwargs)

    def scan(self, simple=False):
        char = self._get_raw()

        if char == '/' and ((peek := self._peek()) in ['/', '*']):
            if peek == '/':
                self._find_delim('\n', advance=True)
            else:
                self._find_delim('*/', advance=True)

            return self.scan()
        elif char == '#' and self._peek() == '#':
            self._advance(1)

            return self._make_token(TokenType.DOUBLE_HASH, '')
        elif char == '#' and not self.line[:self._cursor-1].strip():
            return self._make_token(TokenType.PREPRO, '')
        elif char == '"':
            return self._make_token(TokenType.STRING, '"{}"'.format(self._get_string()))
        elif char == '<':
            return self._make_token(TokenType.ARROW_STRING, self._find_with_cb(lambda x: x != '>', advance=True))
        elif not simple and self.is_identifier_char(char):
            return self._make_token(TokenType.IDENTIFIER, char + self._find_with_cb(self.is_identifier_char))
        else:
            return self._make_token(TokenType.UNKNOWN, char)
