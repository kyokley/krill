import re

from functools import singledispatch


class _Expr:
    def build(self):
        return traverse(self, build_expr)

    def __str__(self):
        return traverse(self, print_expr)


class FilterExpr(_Expr):
    def __init__(self, token):
        self.filter = token[0].strip()


class QuotedFilterExpr(FilterExpr):
    def __init__(self, token):
        self.filter = token[0].strip().strip("'")


class _BinaryExpr(_Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class AndExpr(_BinaryExpr):
    pass


class OrExpr(_BinaryExpr):
    pass


class _UnaryExpr(_Expr):
    def __init__(self, inner):
        self.inner = inner


class NotExpr(_UnaryExpr):
    pass


@singledispatch
def traverse(expr, func):
    raise NotImplementedError


@singledispatch
def build_expr(expr, *funcs):
    raise NotImplementedError


@singledispatch
def print_expr(expr, *funcs):
    raise NotImplementedError


@traverse.register(FilterExpr)
def _(expr, func):
    return func(expr, expr.filter)


@traverse.register(_BinaryExpr)
def _(expr, func):
    left = traverse(expr.left, func)
    right = traverse(expr.right, func)
    return func(expr, left, right)


@traverse.register(_UnaryExpr)
def _(expr, func):
    return func(expr, expr.inner)


@build_expr.register(FilterExpr)
def filter_val(_, value):
    regex = re.compile(value, re.IGNORECASE)

    def func(text):
        match = regex.search(text)
        if match:
            return (True, set([regex]))
        else:
            return (False, set())

    return func


@build_expr.register(AndExpr)
def and_val(_, left, right):
    def func(text):
        left_output = left(text)
        right_output = right(text)

        output = left_output[0] and right_output[0]
        matches = set()

        if output:
            matches.update(left_output[1], right_output[1])
        return (output, matches)

    return func


@build_expr.register(OrExpr)
def or_val(_, left, right):
    def func(text):
        left_output = left(text)
        right_output = right(text)

        output = left_output[0] or right_output[0]
        matches = set()

        if left_output[1]:
            matches.update(left_output[1])

        if right_output[1]:
            matches.update(right_output[1])

        return (output, matches)

    return func


@build_expr.register(NotExpr)
def not_val(_, func):
    def not_func(text):
        inner_output = func(text)

        output = not inner_output[0]
        matches = set()

        return (output, matches)

    return not_func


@print_expr.register(FilterExpr)
def print_filter_val(expr, value):
    return f'{expr.__class__.__name__}({value})'


@print_expr.register(_BinaryExpr)
def print_binary_val(expr, left, right):
    return f'{expr.__class__.__name__}({left}, {right})'


@print_expr.register(_UnaryExpr)
def print_unary_val(expr, inner):
    return f'{expr.__class__.__name__}({inner})'
