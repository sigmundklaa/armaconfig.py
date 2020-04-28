
import io

from .config import *
from .analyser import *
from .exceptions import *
from .scanner import *
from .stream import *

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
