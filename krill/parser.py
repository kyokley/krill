# Based on https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm
from .lexer import (LPAREN,
                    RPAREN,
                    AND,
                    OR,
                    NOT,
                    FILTER,
                    QUOTED_FILTER,
                    )

import re

class Expr(object):
    def build(self):
        return (False, set())

class FilterExpr(Expr):
    def __init__(self, token):
        self.filter = token[0].strip()

    def build(self):
        regex = re.compile(self.filter, re.IGNORECASE)
        
        def func(text):
            match = regex.search(text)
            if match:
                return (True, set([regex]))
            else:
                return (False, set())

        return func

    def __str__(self):
        return 'FilterExpr(%s)' % self.filter

class BinaryExpr(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class AndExpr(BinaryExpr):
    def build(self):
        def func(text):
            left_func = self.left.build()
            right_func = self.right.build()

            left_output = left_func(text)
            right_output = right_func(text)

            output = left_output[0] and right_output[0]
            matches = set()

            if output:
                matches.update(left_output[1], right_output[1])
            return (output, matches)
        return func

    def __str__(self):
        return 'AndExpr(%s, %s)' % (self.left, self.right)

class OrExpr(BinaryExpr):
    def build(self):
        def func(text):
            left_func = self.left.build()
            right_func = self.right.build()

            left_output = left_func(text)
            right_output = right_func(text)

            output = left_output[0] or right_output[0]
            matches = set()

            if output:
                matches.update(left_output[1], right_output[1])
            return (output, matches)
        return func

    def __str__(self):
        return 'OrExpr(%s, %s)' % (self.left, self.right)

class NotExpr(Expr):
    def __init__(self, input):
        self.input = input

    def build(self):
        def func(text):
            input_func = self.input.build()
            input_output = input_func(text)

            output = not input_output[0]
            matches = set()

            return (output, matches)
        return func

    def __str__(self):
        return 'NotExpr(%s)' % (self.input)

class QuotedFilterExpr(FilterExpr):
    def __init__(self, filter):
        self.filter = filter[0].strip().strip("'")

    def __str__(self):
        return 'QuotedFilterExpr(%s)' % self.filter

class TokenParser(object):
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
