import unittest

from krill.lexer import AND, FILTER, LPAREN, NOT, OR, QUOTED_FILTER, RPAREN, filter_lex


class TestLexer(unittest.TestCase):
    def test_simple(self):
        test_str = 'python'
        expected = [('python', FILTER)]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_simple_with_spaces(self):
        test_str = 'python is the best'
        expected = [('python is the best', FILTER)]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_simple_AND(self):
        test_str = 'python is fun && python is simple'
        expected = [
            ('python is fun', FILTER),
            ('&&', AND),
            ('python is simple', FILTER),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_simple_OR(self):
        test_str = 'python is fun || python is the best'
        expected = [
            ('python is fun', FILTER),
            ('||', OR),
            ('python is the best', FILTER),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_multi_AND(self):
        test_str = 'python is fun && python is simple && python is the best'
        expected = [
            ('python is fun', FILTER),
            ('&&', AND),
            ('python is simple', FILTER),
            ('&&', AND),
            ('python is the best', FILTER),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_multi_OR(self):
        test_str = 'python is fun || python is simple || python is the best'
        expected = [
            ('python is fun', FILTER),
            ('||', OR),
            ('python is simple', FILTER),
            ('||', OR),
            ('python is the best', FILTER),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_mixed_AND_and_OR(self):
        test_str = 'python is fun && python is simple || python is the best'
        expected = [
            ('python is fun', FILTER),
            ('&&', AND),
            ('python is simple', FILTER),
            ('||', OR),
            ('python is the best', FILTER),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_mixed_grouping(self):
        test_str = 'python is fun && (python is simple || python is the best)'
        expected = [
            ('python is fun', FILTER),
            ('&&', AND),
            ('(', LPAREN),
            ('python is simple', FILTER),
            ('||', OR),
            ('python is the best', FILTER),
            (')', RPAREN),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_mixed_grouping_not(self):
        test_str = '!python is not fun && (python is simple || python is the best)'
        expected = [
            ('!', NOT),
            ('python is not fun', FILTER),
            ('&&', AND),
            ('(', LPAREN),
            ('python is simple', FILTER),
            ('||', OR),
            ('python is the best', FILTER),
            (')', RPAREN),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_multi_tier(self):
        test_str = 'a && (b || (c && d))'
        expected = [
            ('a', FILTER),
            ('&&', AND),
            ('(', LPAREN),
            ('b', FILTER),
            ('||', OR),
            ('(', LPAREN),
            ('c', FILTER),
            ('&&', AND),
            ('d', FILTER),
            (')', RPAREN),
            (')', RPAREN),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)

    def test_quoted_filter(self):
        test_str = "a && (b || (c && d)) || '(e)'"
        expected = [
            ('a', FILTER),
            ('&&', AND),
            ('(', LPAREN),
            ('b', FILTER),
            ('||', OR),
            ('(', LPAREN),
            ('c', FILTER),
            ('&&', AND),
            ('d', FILTER),
            (')', RPAREN),
            (')', RPAREN),
            ('||', OR),
            ("'(e)'", QUOTED_FILTER),
        ]
        actual = filter_lex(test_str)
        self.assertEqual(expected, actual)
