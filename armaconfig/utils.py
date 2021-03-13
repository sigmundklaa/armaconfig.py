
def is_identifier_char(char, first_strict=False):
    if first_strict:
        # If the first in the identifier
        return char.isalpha() or char == '_'

    return char.isalnum() or char == '_'


# i stole this from https://stackoverflow.com/questions/22994656/how-to-check-if-an-item-is-the-last-one-of-iteration
def tag_last(iterable):
    """
    Given some iterable, returns (last, item), where last is only
    true if you are on the final iteration.
    """

    iterator = iter(iterable)
    gotone = False
    try:
        lookback = next(iterator)
        gotone = True
        while True:
            cur = next(iterator)
            yield False, lookback
            lookback = cur
    except StopIteration:
        if gotone:
            yield True, lookback
        return
