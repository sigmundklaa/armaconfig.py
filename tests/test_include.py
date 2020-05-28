
from armaconfig import load

with open('files/test_include_master.hpp') as fp:
    assert load(fp) == {'test': {'a': 3}}
