# Based on https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm
from lexer import (LPAREN,
                   RPAREN,
                   AND,
                   OR,
                   FILTER,
                   )

import re

class Expr(object):
    def __call__(self):
        return None

    def build(self):
        return None

class FilterExpr(Expr):
    def __init__(self, token):
        self.filter = token[0].strip()

    def build(self):
        regex = re.compile(self.filter)
        
        def func(text):
            match = regex.search(text)
            if match:
                return match.group(0)
            else:
                return None

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

            return left_func(text) and right_func(text)
        return func

    def __str__(self):
        return 'AndExpr(%s, %s)' % (self.left, self.right)

class OrExpr(BinaryExpr):
    def build(self):
        def func(text):
            left_func = self.left.build()
            right_func = self.right.build()

            return left_func(text) or right_func(text)
        return func

    def __str__(self):
        return 'OrExpr(%s, %s)' % (self.left, self.right)

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
        if self.next()[1] in (AND, OR):
            op = self.next()[1]
            self.consume()
            arg2 = self.P()
            if op == AND:
                return AndExpr(arg1, arg2)
            elif op == OR:
                return OrExpr(arg1, arg2)
        return arg1

    def P(self):
        expr = None
        if self.next()[1] == FILTER:
            expr = FilterExpr(self.next())
            self.consume()
        elif self.next()[1] == LPAREN:
            self.consume()
            expr = self.E()
            self.expect(RPAREN)
        else:
            self.error()
        return expr

