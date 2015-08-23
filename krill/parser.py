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
        self.filter = token[0]

    def build(self):
        regex = re.compile(self.filter)
        
        def func(text):
            match = regex.match(text)
            if match:
                return match.group(0)
            else:
                return None

        return func

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

class OrExpr(BinaryExpr):
    def build(self):
        def func(text):
            left_func = self.left.build()
            right_func = self.right.build()

            return left_func(text) or right_func(text)
        return func

class TokenParser(object):
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
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
        raise Exception('Parser error')

    def expect(self, token_type):
        if self.next()[1] == token_type:
            self.consume()
        else:
            self.error()

    def E(self):
        self.P()
        while self.next()[1] in (AND, OR):
            self.consume()
            self.P()

    def P(self):
        if self.next()[1] == FILTER:
            self.consume()
        elif self.next()[1] == LPAREN:
            self.consume()
            self.E()
            self.expect(RPAREN)
        else:
            self.error()

