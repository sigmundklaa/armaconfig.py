
from collections import OrderedDict, namedtuple, abc
from .analyse import Parser, NodeType
from .entry import DEFAULT_STREAM_NAME
from .utils import tag_last

ValueNode = namedtuple('ValueNode', ['name', 'value'])


class Encoder:
    def __init__(self, indent=None):
        self._indent = indent
        self._indent_lvl = 0

    def _make_indent(self, pre=None, post=None):
        if not self._indent:
            return

        if pre is not None:
            yield pre

        yield (' ' * self._indent * self._indent_lvl)

        if post is not None:
            yield post

    def _encode_one(self, node):
        if isinstance(node, Config):
            yield 'class %s' % node.name

            if node.inherits:
                yield ' : ' + node.inherits.name

            self._indent_lvl += 1

            yield ' {'
            yield from self._make_indent(pre='\n')
            yield from self.encode(node.values_raw())

            self._indent_lvl -= 1

            yield from self._make_indent(pre='\n')
            yield '};'
        elif isinstance(node, ValueNode):
            yield node.name

            is_array = isinstance(node.value, (list, tuple))

            if is_array:
                yield '[]'

            yield ' = '
            yield from self._encode_one(node.value)
            yield ';'
        elif isinstance(node, (list, tuple)):
            yield '{'

            if node:
                is_first = True
                self._indent_lvl += 1

                for x in node:
                    if not is_first:
                        yield ','

                    yield from self._make_indent(pre='\n')
                    yield from self._encode_one(x)

                    is_first = False

                self._indent_lvl -= 1

                yield from self._make_indent('\n')
            yield '}'
        elif isinstance(node, str):
            yield '"%s"' % node.replace('"', '""')
        elif isinstance(node, bool):
            yield str(int(node))
        else:
            yield str(node)

    def encode(self, iterable):
        for is_last, x in tag_last(iterable):
            yield from self._encode_one(x)

            if not is_last:
                yield from self._make_indent(pre='\n')


def encode(node, *args, **kwargs):
    include_self = kwargs.pop('include_self', False)
    encoder = Encoder(*args, **kwargs)

    if not isinstance(node, Config):
        if isinstance(node, dict):
            node = Config.from_dict(DEFAULT_STREAM_NAME, node)
            include_self = False
        elif not include_self:
            raise TypeError(
                'expected dict, config, got %s' % (str(type(node))))

    if include_self:
        return encoder._encode_one(node)

    return encoder.encode(node.values_raw())


def decode(unit, *args, **kwargs):
    parser = Parser(unit, *args, **kwargs)
    base_config = Config(getattr(unit, 'name', DEFAULT_STREAM_NAME))

    configs = [base_config]

    def _clean_value(value):
        if isinstance(value, list):
            return [_clean_value(x) for x in value
                    if not isinstance(x, str) or x.strip()]
        else:
            value = value.strip()

            try:
                return bool(['false', 'true'].index(value))
            except ValueError:
                pass

            # TODO: Maybe move this to its own function,
            # as it can be used in the preprocessor's include statement
            if value and value[0] == '"' and value[-1] == '"':
                value = value[1:len(value) - 1]

            try:
                new_val = float(value)

                if new_val.is_integer():
                    new_val = int(new_val)

                return new_val
            except ValueError:
                return value

    def _decode_iter(iterator):
        for nodetype, nodeargs in iterator:
            if nodetype == NodeType.CLASS:
                name, inherits, iter_ = nodeargs
                config = Config(name, inherits, configs[-1])

                configs[-1].add(config)
                configs.append(config)

                _decode_iter(iter_)
            elif nodetype == NodeType.PROPERTY:
                name, value = nodeargs

                configs[-1].add(ValueNode(name, _clean_value(value)))

        configs.pop()

    _decode_iter(parser.parse())

    return base_config


class Config(abc.MutableMapping, dict):
    """
    A `Config` object acts as a proxy to an ordered dict.
    The dict contains the keys and values that the config consists of.

    For example, consider the following Arma 3 Config class:

    class MyClass {
        string_value = "This is a string";
        array_value[] = {"This", "is", "an", "array};
    };

    When the above is represented as a dictionary,
    it would look something like this:

    {
        'MyClass': {
            'string_value': 'This is a string',
            'array_value': ['This', 'is', 'an', 'array']
        }
    }
    """
    @classmethod
    def from_dict(self, name, dict_, **kwargs):
        conf = Config(name, **kwargs)

        for k, v in dict_.items():
            if isinstance(v, dict) and not isinstance(v, Config):
                node = Config.from_dict(k, v, parent=conf)
            elif isinstance(v, (Config, ValueNode)):
                node = v
            elif isinstance(v, (str, int, float, complex, list)):
                node = ValueNode(k, v)
            else:
                raise TypeError(str(type(v)))

            conf.add(node)

        return conf

    def to_dict(self):
        out = {}

        for k in self:
            item = self[k]

            if isinstance(item, Config):
                out[k] = item.to_dict()
            else:
                out[k] = item

        return out

    def __init__(self, name, inherits=None, parent=None):
        self.name = name
        self.parent = parent

        if inherits:
            try:
                self.inherits = self.parent.get_config(inherits)
            except KeyError:
                raise ValueError(
                    'Attempted to inherit non-existing config (%s)' % inherits)
        else:
            self.inherits = None

        self._dict = OrderedDict()

    def add(self, node):
        if node.name in self.iter_self():
            raise ValueError('%s already defined' % node.name)

        self[node.name] = node

    def pop(self, key):
        return self._dict.pop(self._keytransform(key))

    def get_config(self, k):
        try:
            config = self[k]

            if not isinstance(config, Config):
                raise TypeError()

            return config
        except KeyError:
            if self.parent:
                return self.parent.get_config(k)

            raise

    def iter_self(self):
        return iter(self._dict)

    def items_raw(self):
        for key in self.iter_self():
            yield key, self._get_raw(key)

    def values_raw(self):
        for key in self.iter_self():
            yield self._get_raw(key)

    def _get_raw(self, item):
        item = self._keytransform(item)

        try:
            return self._dict[item]
        except KeyError:
            if self.inherits:
                return self.inherits._get_raw(item)

            raise

    def _keytransform(self, key):
        return key.lower()

    def __iter__(self):
        if self.inherits:
            yield from self.inherits

        yield from self.iter_self()

    def __repr__(self):
        return self._dict.__repr__()

    def __getitem__(self, item):
        raw = self._get_raw(item)

        if isinstance(raw, ValueNode):
            return raw.value

        return raw

    def __setitem__(self, item, value):
        if not isinstance(value, (Config, ValueNode)):
            if isinstance(value, dict):
                conf = Config(item, None, self)
                self._dict[self._keytransform(item)] = conf

                for k, v in value.items():
                    conf[k] = v

                return
            else:
                value = ValueNode(item, value)

        self._dict[self._keytransform(item)] = value

    def __delitem__(self, item):
        del self._dict[self._keytransform(item)]

    def __len__(self):
        return len(self._dict)
