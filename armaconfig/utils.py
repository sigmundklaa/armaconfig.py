
def is_identifier_char(char, first_strict=False):
    if first_strict:
        # If the first in the identifier
        return char.isalpha() or char == '_'

    return char.isalnum() or char == '_'
