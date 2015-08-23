import unittest
from krill.lexer import filter_lex
from krill.parser import TokenParser

class TestParser(unittest.TestCase):
    def test_simple(self):
        test_str = 'python'
        tokens = filter_lex(test_str)
        expected = 'FilterExpr(python)'
        actual = str(TokenParser(tokens).E())
        self.assertEquals(expected, actual)

    def test_simple_with_parens(self):
        test_str = '(python )'
        tokens = filter_lex(test_str)
        expected = 'FilterExpr(python)'
        actual = str(TokenParser(tokens).E())
        self.assertEquals(expected, actual)

    def test_simple_with_spaces(self):
        test_str = 'python is the best'
        tokens = filter_lex(test_str)
        expected = 'FilterExpr(python is the best)'
        actual = str(TokenParser(tokens).E())
        self.assertEquals(expected, actual)

    def test_simple_AND(self):
        test_str = 'python is fun && python is simple'
        tokens = filter_lex(test_str)
        expected = 'AndExpr(FilterExpr(python is fun), FilterExpr(python is simple))'
        actual = str(TokenParser(tokens).E())
        self.assertEquals(expected, actual)

    def test_simple_OR(self):
        test_str = 'python is fun || python is the best'
        tokens = filter_lex(test_str)
        expected = 'OrExpr(FilterExpr(python is fun), FilterExpr(python is the best))'
        actual = str(TokenParser(tokens).E())
        self.assertEquals(expected, actual)

    def test_multi_AND(self):
        test_str = 'python is fun && python is simple && python is the best'
        tokens = filter_lex(test_str)
        expected = 'AndExpr(AndExpr(FilterExpr(python is fun), FilterExpr(python is simple)), FilterExpr(python is the best))'
        actual = str(TokenParser(tokens).E())
        self.assertEquals(expected, actual)
