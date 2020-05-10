"""
The preprocessor acts as an optional layer between the main stream, and the source.
"""

import enum
from .exceptions import Unexpected, UnexpectedValue, UnexpectedType, EOL
from .utils import is_identifier_char
from .buf import Strbuf, get_string

class Define:
    def __init__(self, preprocessor, name, args, chars):
        self.name = name
        self.args = args
        self.chars = chars
        self.preprocessor = preprocessor

    def __call__(self, *args):
        def resolve_arg(identifier):
            if identifier not in self.args:
                return identifier

            return args[self.args.index(identifier)]

        def _process_buf(buf):
            for char in buf:
                if is_identifier_char(char):
                    identifier = resolve_arg(char + buf.find_with_cb(is_identifier_char))
                    is_joined = False

                    while buf.peek(2) == '##':
                        buf.advance(2)

                        if buf.peek(1) == '#': break

                        is_joined = True
                        identifier += resolve_arg(buf.find_with_cb(is_identifier_char))

                    if not is_joined and identifier in self.preprocessor.defined:
                        # Check for args tho k chief
                        yield from self.preprocessor.defined[identifier].resolve(Strbuf(_process_buf(buf)))

                    else:
                        yield from iter(identifier)
                elif char == '#':
                    # just wrap everything in quotes
                    yield '"'
                    yield from _process_buf(buf)
                    yield '"'
                else:
                    yield char

        buf = Strbuf(iter(self.chars))
        expect, got = len(self.args), len(args)

        if expect != got:
            raise Exception(f'{repr(self)}: Expected {expect} macro arguments, got {got}')

        return _process_buf(buf)

    def resolve(self, buf):
        args = []
        current = ''

        if buf.peek(1) == '(':
            buf.advance(1)

            for char in buf:
                if char in ',)':
                    args.append(current)
                    current = ''

                    if char == ')':
                        break
                elif is_identifier_char(char):
                    identifier = char + buf.find_with_cb(is_identifier_char)

                    if identifier in self.preprocessor.defined:
                        stmt = self.preprocessor.defined[identifier]

                        current += ''.join(list(stmt.resolve(buf)))
                    else:
                        current += identifier
                else:
                    current += char

        return self.__call__(*args)

    def __repr__(self):
        return f'{type(self).__name__}: {self.name}({",".join(self.args)})'

class Preprocessor:
    class Types(enum.Enum):
        COMMENT = 1
        COMMAND = 2
        IDENTIFIER = 3
        INCL_STRING = 4
        UNSPECIFIED = 5

    def __init__(self, scanner, **opts):
        self.opts = opts
        self.scanner = scanner
        self.stream = self.scanner.stream
        self.defined = {}
        self.data = []

        # Used for ifdefs, should_return is set to false when in false ifdef statement
        self._in_ifdef = False
        self.should_return = True

    def _comp_expect(self, expect, got):
        if expect is not None and expect != got:
            raise Unexpected(expect, got)

    def _process_command(self):
        _, command = token = self._next(self.Types.IDENTIFIER)

        # if we're in an ifdef, we are searching for else or endif
        if self._in_ifdef and command in ('else', 'endif'):
            if command == 'endif':
                self.should_return = True
                self._in_ifdef = False
            else:
                self.should_return = not self.should_return

            return

        # if we're in an ifdef, and we did not get else or endif,
        # we return if self.should_return is set to false
        elif not self.should_return:
            return

        elif command == 'define':
            # add to .defined, return empty
            _, macro = self._next(self.Types.IDENTIFIER)
            args = []

            if self.stream.peek(1) == '(':
                self.stream.advance(1)

                while True:
                    nxt = self.stream.find_with_cb(is_identifier_char)

                    if nxt: args.append(nxt)

                    seperator = self.stream.get(1)

                    if seperator == ',': continue
                    elif seperator == ')': break
                    else: raise Unexpected([',', ')'], seperator)

            buf = Strbuf(self.stream)
            chars = ''

            for char in buf:
                if char == '\n': break
                elif char == '\\':
                    until_newline = buf.find_delim('\n', True)

                    if until_newline.strip():
                        raise Unexpected('whitespace, newline', until_newline)
                else:
                    chars += char

            self.defined[macro] = Define(self, macro, args, chars)

        elif command == 'include':
            # add stream, return empty
            _, path = self._next(self.Types.INCL_STRING)

            if all(x in ('"', '>', '<') for x in (path[0], path[-1])):
                path = path[1:-1]

            path = path.replace('\\', '/')

            self.stream.add_stream(path)
        elif command in ('ifdef', 'ifndef'):
            if self._in_ifdef:
                raise Exception('Nested ifdef/ifndef is not supported')

            _, macro = self._next(self.Types.IDENTIFIER)
            is_defined = macro in self.defined

            self.should_return = is_defined if command == 'ifdef' else not is_defined
            self._in_ifdef = True
        elif command == 'undef':
            # remove from .defined, return empty
            _, macro = self._next(self.Types.IDENTIFIER)

            if macro in self.defined:
                del self.defined[macro]
        else:
            raise UnexpectedValue(['define', 'include', 'ifdef', 'ifndef', 'undef'], token)

    def _next(self, expect=None):
        def default(payload):
            self._comp_expect(expect, None)

            return self.scanner.make_token(self.Types.UNSPECIFIED, payload)

        char = self.stream.get(1)

        try:
            peek = self.stream.peek(1)
        except EOL:
            peek = None

        if char == '/' and (peek in ('/', '*')):
            if peek == '/':
                value = self.stream.find_delim('\n', advance=True)
            else:
                value = self.stream.find_delim('*/', advance=True)

            return self.scanner.make_token(self.Types.COMMENT, value)
        elif char == '#':# and self.stream.line_empty:
            self._comp_expect(expect, self.Types.COMMAND)

            # if the character is #, and everything before the current character is a whitespace
            return self.scanner.make_token(self.Types.COMMAND, None)
        elif char == '_' or char.isalpha():
            self._comp_expect(expect, self.Types.IDENTIFIER)

            # get the identifier, check if it is a macro.
            # if it is a macro, return a token for it,
            # if not, return the default
            identifier = char + self.stream.find_with_cb(is_identifier_char, advance=False)

            if identifier in self.defined or expect == self.Types.IDENTIFIER:
                return self.scanner.make_token(self.Types.IDENTIFIER, identifier)

            return default(identifier)
        elif char in ('"', '<') and expect == self.Types.INCL_STRING:
            if char == '<':
                value = self.stream.find_with_cb(lambda x: x != '>', advance=True)
            else:
                value = get_string(self.stream)

            return self.scanner.make_token(self.Types.INCL_STRING, value)
        elif char.isspace() and expect is not None:
            return self._next(expect)
        else:
            return default(char)

    def process(self):
        t, v = nxt = self._next()

        if t == self.Types.COMMAND:
            self._process_command()

            return ''
        elif self.should_return:
            if t == self.Types.COMMENT:
                if self.opts.get('include_commments', False):
                    self.data.append(nxt)
                    
                    # Return a space instead of an empty string, this is so that
                    # the stream does not raise EOL from this sequence
                    return ' '

                # Skip the comment, move to the next one
                return self.process()
            elif t == self.Types.UNSPECIFIED:
                return v
            elif t == self.Types.IDENTIFIER:
                if v in self.defined:
                    return ''.join([x for x in self.defined[v].resolve(self.stream)])
                else:
                    return v

            raise UnexpectedType([self.Types.COMMAND, self.Types.COMMENT, self.Types.UNSPECIFIED], nxt)
        else:
            return ''
