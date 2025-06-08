from krill.lexer import filter_lex
from krill.parser import TokenParser


class TestParser:
    def test_simple(self):
        test_str = 'python'
        tokens = filter_lex(test_str)
        expected = 'FilterExpr(python)'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_str = 'python is great'
        neg_str = 'rust is great'

        test_func = TokenParser(tokens).buildFunc()
        assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_simple_with_parens(self):
        test_str = '(python )'
        tokens = filter_lex(test_str)
        expected = 'FilterExpr(python)'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_str = 'python is great'
        neg_str = 'rust is great'

        test_func = TokenParser(tokens).buildFunc()
        assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_simple_with_spaces(self):
        test_str = 'python is the best'
        tokens = filter_lex(test_str)
        expected = 'FilterExpr(python is the best)'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_str = 'python is the best'
        neg_str = 'python is great'

        test_func = TokenParser(tokens).buildFunc()
        assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_simple_AND(self):
        test_str = 'python is fun && python is simple'
        tokens = filter_lex(test_str)
        expected = 'AndExpr(FilterExpr(python is fun), FilterExpr(python is simple))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_str = 'python is fun and python is simple'
        neg_str = 'python is only fun'

        test_func = TokenParser(tokens).buildFunc()
        assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_simple_OR(self):
        test_str = 'python is fun || python is the best'
        tokens = filter_lex(test_str)
        expected = 'OrExpr(FilterExpr(python is fun), FilterExpr(python is the best))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_str = 'python is fun and python is simple'
        neg_str = 'python is only fun'

        test_func = TokenParser(tokens).buildFunc()
        assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_multi_AND(self):
        test_str = 'python is fun && python is simple && python is the best'
        tokens = filter_lex(test_str)
        expected = 'AndExpr(AndExpr(FilterExpr(python is fun), FilterExpr(python is simple)), FilterExpr(python is the best))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_str = 'python is fun and python is simple and python is the best'
        neg_str = 'python is fun and python is the best'

        test_func = TokenParser(tokens).buildFunc()
        assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_multi_OR(self):
        test_str = 'python is fun || python is simple || python is the best'
        tokens = filter_lex(test_str)
        expected = 'OrExpr(OrExpr(FilterExpr(python is fun), FilterExpr(python is simple)), FilterExpr(python is the best))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_str = 'python is the best'
        neg_str = 'rust is the best'

        test_func = TokenParser(tokens).buildFunc()
        assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_mixed_AND_and_OR(self):
        test_str = 'python is fun && python is simple || python is the best'
        tokens = filter_lex(test_str)
        expected = 'OrExpr(AndExpr(FilterExpr(python is fun), FilterExpr(python is simple)), FilterExpr(python is the best))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_strs = ('python is fun and python is simple',
                       'python is great and python is the best',
                       )
        neg_str = 'python is fun and python is the great'

        test_func = TokenParser(tokens).buildFunc()
        for affirm_str in affirm_strs:
            assert test_func(affirm_str)[0]
        assert not test_func(neg_str)[0]

    def test_mixed_grouping(self):
        test_str = 'python is fun && (python is simple || python is the best)'
        tokens = filter_lex(test_str)
        expected = 'AndExpr(FilterExpr(python is fun), OrExpr(FilterExpr(python is simple), FilterExpr(python is the best)))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        affirm_strs = ('python is fun and python is simple',
                       'python is fun and python is the best',
                       )
        neg_strs = ('python is fun and python is the great',
                    'python is great and python is simple',
                    )

        test_func = TokenParser(tokens).buildFunc()
        for affirm_str in affirm_strs:
            assert test_func(affirm_str)[0]
        for neg_str in neg_strs:
            assert not test_func(neg_str)[0]

    def test_mixed_grouping_not(self):
        test_str = '!python is not fun && (python is simple || python is the best)'
        tokens = filter_lex(test_str)
        expected = 'AndExpr(NotExpr(FilterExpr(python is not fun)), OrExpr(FilterExpr(python is simple), FilterExpr(python is the best)))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

        test_func = TokenParser(tokens).buildFunc()
        affirm_strs = ('python is great, python is simple',
                       'python is fun and python is the best',
                       )
        neg_strs = ('python is not fun but python is the great',
                    'python is not fun and python is simple',
                    )
        for affirm_str in affirm_strs:
            assert test_func(affirm_str)[0]
        for neg_str in neg_strs:
            assert not test_func(neg_str)[0]


    def test_multi_tier(self):
        test_str = 'a && (b || (c && d))'
        tokens = filter_lex(test_str)
        expected = 'AndExpr(FilterExpr(a), OrExpr(FilterExpr(b), AndExpr(FilterExpr(c), FilterExpr(d))))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual

    def test_quoted_filter(self):
        test_str = "a && (b || (c && d)) || '(e)'"
        tokens = filter_lex(test_str)
        expected = 'OrExpr(AndExpr(FilterExpr(a), OrExpr(FilterExpr(b), AndExpr(FilterExpr(c), FilterExpr(d)))), QuotedFilterExpr((e)))'
        actual = str(TokenParser(tokens).E())
        assert expected == actual
