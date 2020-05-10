
import abc
from .exceptions import EOL

def get_string(buf):
    """
    This function assumes that the first " has been found
    """
    def callback(char):
        if char == '"':
            if buf.peek(1) != '"':
                return False

            buf.advance(1)

        return True

    return buf.find_with_cb(callback, length=1, advance=True)


class Buf(abc.ABC):
    """
    Helper class that provides methods for reading chars from a buffer.
    """
    def __init__(self):
        self._buf = []

    @abc.abstractmethod
    def _fill_buf(self, length=1): pass

    def _peek_raw(self, length=1):
        self._fill_buf(length)

        slice_ = self._buf[:length]

        return slice_

    def peek(self, *args, **kwargs):
        return self._peek_raw(*args, **kwargs)

    def advance(self, length=1):
        self._fill_buf(length)

        del self._buf[:length]

    def get(self, length=1):
        seq = self.peek(length)

        if length and not seq:
            raise EOL()

        self.advance(length)

        return seq

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self.get(1)
        except EOL:
            raise StopIteration

class Charbuf(Buf):
    def peek(self, *args, **kwargs):
        return ''.join(super().peek(*args, **kwargs))

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
                self.advance(length)

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

class Strbuf(Charbuf):
    def __init__(self, iterator):
        self.iterator = iterator

        super().__init__()

    def _fill_buf(self, length=1):
        for _ in range(length - len(self._buf)):
            try:
                self._buf.append(next(self.iterator))
            except StopIteration:
                return
