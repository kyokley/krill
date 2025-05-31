# Based on the blog post at http://jayconrod.com/posts/37/a-simple-interpreter-from-scratch-in-python-part-1

import re
import sys

AND = 'AND'
OR = 'OR'
NOT = 'NOT'
FILTER = 'FILTER'
LPAREN = 'LPAREN'
RPAREN = 'RPAREN'
QUOTED_FILTER = 'QUOTED_FILTER'

token_exprs = [
    (r'[ \n\t]+', None),
    (r'#[^\n]*', None),
    (r'\(', LPAREN),
    (r'\)', RPAREN),
    (r'&&', AND),
    (r'\|\|', OR),
    (r'!', NOT),
    (r"'[^']*'", QUOTED_FILTER),
    (r'((?!(&&|\|\||\(|\))).)*(?=($|\n|\(|\)|&&|\|\|))', FILTER),
]


def lex(characters, token_exprs):
    pos = 0
    tokens = []
    while pos < len(characters):
        match = None
        for token_expr in token_exprs:
            pattern, tag = token_expr
            regex = re.compile(pattern)

            if match := regex.match(characters, pos):
                text = match.group(0).strip()
                if tag:
                    token = (text, tag)
                    tokens.append(token)
                break

        if not match:
            print(f'Illegal character: {characters[pos:]}\\n')
            sys.exit(1)
        else:
            pos = match.end(0)
    return tokens


def filter_lex(characters):
    return lex(characters, token_exprs)
