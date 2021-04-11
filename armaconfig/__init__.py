
import io

from .config import (
    encode,
    decode
)

from .entry import PreproBuf


def dump(obj, fp, *args, **kwargs):
    for x in encode(obj, *args, **kwargs):
        fp.write(x)

    return fp


def dumps(obj, *args, **kwargs):
    fp = dump(obj, io.StringIO(), *args, **kwargs)
    read = fp.getvalue()
    fp.close()

    return read


def load(fp, *args, **kwargs):
    return decode(fp, *args, **kwargs)


def loads(string, *args, **kwargs):
    return load(io.StringIO(string), *args, **kwargs)


def preprocess(stream, **kwargs):
    return PreproBuf(stream, **kwargs)


def preprocess_s(string, **kwargs):
    return PreproBuf(io.StringIO(string), **kwargs)
