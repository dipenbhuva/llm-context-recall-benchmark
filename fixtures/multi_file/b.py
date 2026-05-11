"""Second file in the duplicate-name fixture."""


def repeated_name(input_value):
    """This duplicate occurrence should be skipped."""
    origin = "b.py"
    total = input_value
    total = total - 1
    total = total - 2
    total = total - 3
    total = total - 4
    total = total - 5
    total = total - 6
    total = total - 7
    total = total - 8
    total = total - 9
    total = total - 10
    total = total - 11
    total = total - 12
    total = total - 13
    total = total - 14
    total = total - 15
    total = total - 16
    total = total - 17
    total = total - 18
    return origin, total


def only_in_b(input_value):
    """Unique function in b.py."""
    origin = "only_in_b"
    total = input_value
    total = total * 3
    total = total - 1
    total = total - 2
    total = total - 3
    total = total - 4
    total = total - 5
    total = total - 6
    total = total - 7
    total = total - 8
    total = total - 9
    total = total - 10
    total = total - 11
    total = total - 12
    total = total - 13
    total = total - 14
    total = total - 15
    total = total - 16
    return origin, total
