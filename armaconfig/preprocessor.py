"""
The preprocessor acts as an optional layer between the main stream, and the source.
"""

import enum
from .exceptions import Unexpected, UnexpectedValue, UnexpectedType, EOL
from .utils import is_identifier_char

class Define:
    def __init__(self, preprocessor, name, args, chars):
        self.name = name
        self.args = args
        self.chars = chars
        self.preprocessor = preprocessor

    def __call__(self, *args):
        iterator = iter(self.chars)
        expect, got = len(self.args), len(args)
        buf = []

        if expect != got:
            raise Exception(f'{repr(self)}: Expected {expect} macro arguments, got {got}')

        for char in iterator:
            if char == '_' or char.isalpha():
                identifier = char
                is_joined = False

                for id_char in iterator:
                    if id_char == '#':
                        nxt = next(iterator)

                        # if two # follow eachother, that means continue the identifier
                        if nxt != '#':
                            buf.extend([id_char, nxt])
                            break
                        
                        is_joined = True
                    elif not is_identifier_char(id_char):
                        buf.append(id_char)
                        break
                    else:
                        identifier += id_char

                if not is_joined and identifier in self.preprocessor.defined:
                    # Check for args tho k chief
                    yield from self.preprocessor.defined[identifier]()

                else:
                    yield from iter(identifier)
            elif char == '#':
                # maybe just wrap everything in quotes
                pass
            else:
                yield char

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
        self.stream = self.scanner.streamset
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

        if self._in_ifdef and command in ('else', 'endif'):
            if command == 'else':
                self.should_return = not self.should_return
            else:
                self.should_return = True
                self._in_ifdef = False
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

            it = self.stream.iter_chars()
            chars = ''

            for char in it:
                if char == '\n': break
                elif char == '\\':
                    for find_newline in it:
                        if find_newline == '\n': break
                        elif not find_newline.isspace():
                            raise Exception('ok')
                    else:
                        raise Exception('Expected newline')
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
        elif char == '#':# and self.stream.line_empty:
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
                    return ''.join(list(self.defined[v]()))
                else:
                    return v

            raise UnexpectedType([self.Types.COMMAND, self.Types.COMMENT, self.Types.UNSPECIFIED], nxt)
        else:
            return self.process()
