"""
The preprocessor acts as an optional layer between the main stream, and the source.
"""

import enum
from .exceptions import Unexpected, UnexpectedValue, UnexpectedType, EOL
from .utils import is_identifier_char

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
        self.stream = self.scanner.streamset
        self.defined = {}
        self.data = []

    def _comp_expect(self, expect, got):
        if expect is not None and expect != got:
            raise Unexpected(expect, got)

    def _process_command(self):
        _, command = token = self._next(self.Types.IDENTIFIER)

        if command == 'define':
            # add to .defined, return nothing
            self.stream.find_with_cb(lambda x: x != '\n')
            return ''
        elif command == 'include':
            _, path = self._next(self.Types.INCL_STRING)

            if all(x in ('"', '>', '<') for x in (path[0], path[-1])):
                path = path[1:-1]

            path = path.replace('\\', '/')
            # add stream, return nothing

            return ''
        elif command in ('ifdef', 'ifndef'):
            # bro idk
            raise Exception()
        elif command == 'undef':
            # remove from .defined, return nothing
            return ''
        else:
            raise UnexpectedValue(['define', 'include', 'ifdef', 'ifndef', 'undef'], token)

    def _next(self, expect=None):
        def default():
            self._comp_expect(expect, None)

            return self.scanner.make_token(self.Types.UNSPECIFIED, char)

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
        elif char == '#':# and not self.stream.line[:self.stream._cursor-1].strip():
            self._comp_expect(expect, self.Types.COMMAND)

            # if the character is #, and everything before the current character is a whitespace
            return self.scanner.make_token(self.Types.COMMAND, None)
        elif char == '_' or char.isalpha():
            self._comp_expect(expect, self.Types.IDENTIFIER)

            # get the identifier, check if it is a macro.
            # if it is a macro, return a token for it,
            # if not, return the default
            identifier = char + self.stream.peek_cb(is_identifier_char)

            if identifier in self.defined or expect == self.Types.IDENTIFIER:
                self.stream.advance(len(identifier))

                return self.scanner.make_token(self.Types.IDENTIFIER, identifier)

            return default()
        elif char in ('"', '<'):
            self._comp_expect(expect, self.Types.INCL_STRING)

            if char == '<':
                value = self.stream.find_with_cb(lambda x: x != '>', advance=True)
            else:
                value = self.stream.get_string()

            return self.scanner.make_token(self.Types.INCL_STRING, value)
        else:
            return default()

    def process(self):
        t, v = nxt = self._next()

        if t == self.Types.COMMENT:
            if self.opts.get('include_commments', False):
                self.data.append(nxt)
                
                # Return a space instead of an empty string, this is so that
                # the stream does not raise EOL from this sequence
                return ' '

            # Skip the comment, move to the next one
            return self.process()
        elif t == self.Types.COMMAND:
            return self._process_command()
        elif t == self.Types.UNSPECIFIED:
            return v
        else:
            raise UnexpectedType([self.Types.COMMAND, self.Types.COMMENT, self.Types.UNSPECIFIED], nxt)
