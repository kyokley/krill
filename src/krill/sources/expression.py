from functools import singledispatch


class _Expr:
    def __call__(self):
        return traverse(self, build_expr)

    def __str__(self):
        return traverse(self, print_expr)


class FilterExpr(_Expr):
    def __init__(self, filter):
        self.filter = filter.strip()


class QuotedFilterExpr(FilterExpr):
    def __init__(self, filter):
        self.filter = filter.strip().strip("'")


class _BinaryExpr(_Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def comparator(self, left, right):
        raise NotImplementedError


class AndExpr(_BinaryExpr):
    def comparator(self, left, right):
        return left and right


class OrExpr(_BinaryExpr):
    def comparator(self, left, right):
        return left or right


class NotExpr(_Expr):
    def __init__(self, inner):
        self.inner = inner


@singledispatch
def traverse(expr, func):
    raise NotImplementedError


@singledispatch
def build_expr(expr, *funcs):
    raise NotImplementedError


@singledispatch
def print_expr(expr, *funcs):
    raise NotImplementedError
