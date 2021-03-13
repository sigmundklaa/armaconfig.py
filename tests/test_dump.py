
from armaconfig import dump, dumps

TEST_FILE = 'files/test_config.hpp'


def test_dumps():
    expected = '''num = 3;
class sub_dict {
    content = "This is a ""sub"" dictionary";
};
array[] = {
    3,
    "str",
    1
};
string = "This is """"a ""string""";'''

    config = {
        'num': 3,
        'sub_dict': {
            'content': 'This is a \"sub\" dictionary'
        },
        'array': [
            3,
            'str',
            True
        ],
        'string': 'This is \"\"a \"string\"'
    }

    assert dumps(config, indent=4) == expected
