
# TODO: Use trees instead of lists of tokens

import os, enum, collections
from pathlib import Path

from .entry import Scanner, Token, EOL
from .exceptions import UnexpectedType, UnexpectedValue

class NodeType(enum.Enum):
    CLASS = 1
    PROPERTY = 2

Node = collections.namedtuple('Node', ['type', 'args'])

class Parser:
    def __init__(self, unit):
        self._scanner = Scanner(unit)

    def _get_until(self, delim=';', token=None, **kwargs):
        seq = []
        token = token or self._scanner.next_token(include_ws=True, **kwargs)

        while not token.value or token.value not in delim:
            seq.append(token)

            token = self._scanner.next_token(include_ws=True, **kwargs)

        return seq, token

    def _parse_array(self):
        seperators = (',', ';', '}')

        def __next():
            _, v = token = next(self._scanner)

            if v == '{':
                return __parse(), next(self._scanner)
            else:
                coll, s = self._get_until(seperators, token)
                
                return ''.join([x.value for x in coll]), s

        def __parse():
            s = None
            output = []

            while True:
                seq, s = __next()
                output.append(seq)

                if s.value in seperators:
                    if s.value == '}': break
                else:
                    raise UnexpectedValue(seperators, s)

            return output

        self._scanner.next_token(expect_val='{')
        
        collection = __parse()

        self._scanner.next_token(expect_val=';')

        return collection

    def _parse_one(self, token=None):
        t, val = token = token or next(self._scanner)

        if t == self._scanner.Types.IDENTIFIER:
            if val == 'class':
                _, name = self._scanner.next_token(expect_typ=[self._scanner.Types.IDENTIFIER])
                _, v = valuetoken = self._scanner.next_token(expect_typ=[self._scanner.Types.SYMBOL])

                if v == ':':
                    inherits, opener = (
                        x.value
                        for x in self._scanner.sequence(
                            2,
                            expect_typ=[self._scanner.Types.IDENTIFIER, self._scanner.Types.SYMBOL]
                        )
                    )
                else:
                    inherits, opener = None, v

                if opener != '{': raise UnexpectedValue(expected=['{'], got=valuetoken)

                def _iter():
                    token = next(self._scanner)

                    while not (token.type == self._scanner.Types.SYMBOL and token.value == '}'):
                        yield self._parse_one(token)
                        token = next(self._scanner)

                    self._scanner.next_token(expect_val=';')

                return Node(NodeType.CLASS, (name, inherits, _iter()))
            else:
                name = val
                _, next_val = val_token = self._scanner.next_token(expect_typ=self._scanner.Types.SYMBOL)
                is_array = False

                if next_val == '[':
                    self._scanner.sequence(2, expect_val=[']', '='])

                    is_array = True
                elif next_val != '=':
                    raise UnexpectedValue(expected='=', got=val_token)

                if is_array:
                    property_value = self._parse_array()
                else:
                    property_value = ''.join([x.value for x in self._get_until(';')[0]])

                return Node(NodeType.PROPERTY, (name, property_value))
        elif t == self._scanner.Types.UNSPECIFIED and val == ';':
            return self._parse_one()
        else:
            raise UnexpectedType(expected=self._scanner.Types.IDENTIFIER, got=token)

    def parse(self):
        while True:
            try:
                yield self._parse_one()
            except EOL:
                return
