
import functools
from armaconfig import loads

def equal_loads(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        string, expect = f(*args, **kwargs)

        assert loads(string) == expect
    return wrapper

@equal_loads
def test_simpledefine():
    return '#define X 3\nproperty = X;', {'property': 3}

@equal_loads
def test_multiline():
    test = '''#define X \
        3

        val = X;
        '''

    return test, {
        'val': 3
    }

@equal_loads
def test_ifdef():
    test = '''
#ifdef X
#define Y 3
#else
#define Y 2
#endif

#ifdef Y
#define X 1
#else
#define X 2
#endif

arr[] = {Y, X};
    '''

    return test, {
        'arr': [2, 1]
    }

@equal_loads
def test_ifndef():
    test = '''
#ifndef X
#define Y 2
#else
#define Y 3
#endif

#ifndef Y
#define X 2
#else
#define X 1
#endif

arr[] = {Y, X};
    '''

    return test, {
        'arr': [2, 1]
    }

@equal_loads
def test_xmacro():
    test = '''
#define LIST \
    X(1) \
    X(2) \
    X(3)

#define X(num) value_##num = num;
LIST
#undef X
    '''

    return test, {
        'value_1': 1,
        'value_2': 2,
        'value_3': 3
    }
