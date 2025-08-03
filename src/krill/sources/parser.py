# Based on https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm
import re

from . import lexer
from .expression import (
    AndExpr,
    FilterExpr,
    NotExpr,
    OrExpr,
    QuotedFilterExpr,
    build_expr,
    print_expr,
    traverse,
)


@traverse.register(FilterExpr)
def _(expr, func):
    return func(expr)


@traverse.register(AndExpr)
@traverse.register(OrExpr)
def _(expr, func):
    left = traverse(expr.left, func)
    right = traverse(expr.right, func)
    return func(expr, left, right)


@traverse.register(NotExpr)
def _(expr, func):
    inner = traverse(expr.inner, func)
    return func(expr, inner)


@build_expr.register(FilterExpr)
def _(expr):
    def func(text):
        regex = re.compile(expr.filter, re.IGNORECASE)

        if match := regex.search(text):
            return (True, set([match.group()]))
        else:
            return (False, set())

    return func


@build_expr.register(AndExpr)
@build_expr.register(OrExpr)
def _(expr, left, right):
    def func(text):
        left_output = left(text)
        right_output = right(text)

        if output := expr.comparator(left_output[0], right_output[0]):
            matches = set()
            if left_output[1]:
                matches.update(left_output[1])

            if right_output[1]:
                matches.update(right_output[1])

            return (output, matches)
        return False, set()

    return func


@build_expr.register(NotExpr)
def _(expr, inner):
    def not_func(text):
        inner_output = inner(text)
        if inner_output[0]:
            return (False, inner_output[1])
        else:
            return (True, inner_output[1])

    return not_func


@print_expr.register(FilterExpr)
def _(expr):
    return f"{expr.__class__.__name__}({expr.filter})"


@print_expr.register(AndExpr)
@print_expr.register(OrExpr)
def _(expr, left, right):
    return f"{expr.__class__.__name__}({left}, {right})"


@print_expr.register(NotExpr)
def _(expr, inner):
    return f"{expr.__class__.__name__}({inner})"


class TokenParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = -1
        self.end = object()

    def next(self):
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        else:
            return self.end

    def consume(self):
        if self.next() != self.end:
            self.pos += 1

    def error(self):
        raise Exception("Parser error")

    def expect(self, token_type):
        if self.next()[1] == token_type:
            self.consume()
        else:
            self.error()

    def E(self):
        arg1 = self.P()
        while self.next() != self.end and self.next()[1] in (lexer.AND, lexer.OR):
            op = self.next()[1]
            self.consume()
            arg2 = self.P()

            match op:
                case lexer.AND:
                    arg1 = AndExpr(arg1, arg2)
                case lexer.OR:
                    arg1 = OrExpr(arg1, arg2)
        return arg1

    def P(self):
        expr = None
        match self.next():
            case filter, lexer.QUOTED_FILTER:
                expr = QuotedFilterExpr(filter)
                self.consume()
            case filter, lexer.FILTER:
                expr = FilterExpr(filter)
                self.consume()
            case _, lexer.LPAREN:
                self.consume()
                expr = self.E()
                self.expect(lexer.RPAREN)
            case _, lexer.NOT:
                self.consume()
                expr = NotExpr(self.P())
            case _:
                self.error()
        return expr

    def build(self):
        return self.E().build()
