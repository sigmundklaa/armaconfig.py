
from armaconfig import loads, load

TEST_FILE = 'files/test_config.hpp'

expected = {
    'number': 3,
    'string': 'Test string with "quotes"!',
    '_class': {
        'base_property': [
            'an array', 'with two elements'
        ]
    },
    'inherited': {
        'base_property': [
            'an array', 'with two elements'
        ],
        'new_property': 'this is a new property'
    }
}

def test_load():
    with open(TEST_FILE) as fp:
        data = load(fp)

    assert data == expected

def test_loads():
    with open(TEST_FILE) as fp:
        string = fp.read()

    loaded = loads(string)

    assert loaded == expected
