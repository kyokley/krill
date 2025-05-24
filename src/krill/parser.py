# Based on https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm
import re

from functools import singledispatch
from krill.lexer import AND, FILTER, LPAREN, NOT, OR, QUOTED_FILTER, RPAREN


class Expr:
    def build(self):
        return traverse(self, build_expr)

    def __str__(self):
        return traverse(self, print_expr)


class FilterExpr(Expr):
    def __init__(self, filter):
        self.filter = filter[0].strip()


class QuotedFilterExpr(FilterExpr):
    def __init__(self, filter):
        self.filter = filter[0].strip().strip("'")


class BinaryExpr(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class AndExpr(BinaryExpr):
    pass


class OrExpr(BinaryExpr):
    pass


class UnaryExpr(Expr):
    def __init__(self, inner):
        self.inner = inner


class NotExpr(UnaryExpr):
    pass


@singledispatch
def traverse(expr, func):
    raise NotImplementedError


@traverse.register(FilterExpr)
def _(expr, func):
    return func(expr, expr.filter)


@traverse.register(BinaryExpr)
def _(expr, func):
    left = traverse(expr.left, func)
    right = traverse(expr.right, func)
    return func(expr, left, right)


@traverse.register(UnaryExpr)
def _(expr, func):
    return func(expr, expr.inner)


@singledispatch
def build_expr(expr, *funcs):
    raise NotImplementedError


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

        if output:
            matches.update(left_output[1], right_output[1])
        return (output, matches)

    return func


@build_expr.register(NotExpr)
def not_val(_, func):
    def func(text):
        inner_output = func(text)

        output = not inner_output[0]
        matches = set()

        return (output, matches)

    return func


@singledispatch
def print_expr(expr, *funcs):
    raise NotImplementedError


@print_expr.register(FilterExpr)
def print_filter_val(expr, filter):
    return f'{expr.__class__.__name__}({filter})'


@print_expr.register(BinaryExpr)
def print_binary_val(expr, left, right):
    return f'{expr.__class__.__name__}({left}, {right})'


@print_expr.register(UnaryExpr)
def print_unary_val(expr, inner):
    return f'{expr.__class__.__name__}({inner})'


class TokenParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = -1
        self.end = object()
        self.result = None

    def next(self):
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        else:
            return self.end

    def consume(self):
        if self.next() != self.end:
            self.pos += 1

    def error(self):
        raise Exception('Parser error')

    def expect(self, token_type):
        if self.next()[1] == token_type:
            self.consume()
        else:
            self.error()

    def E(self):
        arg1 = self.P()
        while self.next() != self.end and self.next()[1] in (AND, OR):
            op = self.next()[1]
            self.consume()
            arg2 = self.P()
            if op == AND:
                arg1 = AndExpr(arg1, arg2)
            elif op == OR:
                arg1 = OrExpr(arg1, arg2)
        return arg1

    def P(self):
        expr = None
        if self.next()[1] == QUOTED_FILTER:
            expr = QuotedFilterExpr(self.next())
            self.consume()
        elif self.next()[1] == FILTER:
            expr = FilterExpr(self.next())
            self.consume()
        elif self.next()[1] == LPAREN:
            self.consume()
            expr = self.E()
            self.expect(RPAREN)
        elif self.next()[1] == NOT:
            self.consume()
            expr = NotExpr(self.P())
        else:
            self.error()
        return expr

    def buildFunc(self):
        return self.E().build()
