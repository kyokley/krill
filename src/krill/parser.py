# Based on https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm
from krill.lexer import AND, FILTER, LPAREN, NOT, OR, QUOTED_FILTER, RPAREN
from krill.expression import FilterExpr, AndExpr, OrExpr, NotExpr, QuotedFilterExpr


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
