from functools import cache

@cache
def minimum_edit_distance(a: str, b: str, m=None, n=None) -> int:
    if m is None:
        m, n = len(a),  len(b)
    if m == 0:
        return n
    elif n == 0:
        return m
    elif a[m - 1] == b[n - 1]:
        return minimum_edit_distance(a, b, m - 1, n - 1)
    else:
        return 1 + min(
            minimum_edit_distance(a, b, m, n - 1),
            minimum_edit_distance(a, b, m - 1, n),
            minimum_edit_distance(a, b, m - 1, n - 1)
        )