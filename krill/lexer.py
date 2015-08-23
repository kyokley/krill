# Based on the blog post at http://jayconrod.com/posts/37/a-simple-interpreter-from-scratch-in-python-part-1

import sys
import re

AND = 'AND'
OR = 'OR'
FILTER = 'FILTER'
LPAREN = 'LPAREN'
RPAREN = 'RPAREN'

token_exprs = [
    (r'[ \n\t]+', None),
    (r'#[^\n]*', None),
    (r'\(', LPAREN),
    (r'\)', RPAREN),
    (r'&&', AND),
    (r'\|\|', OR),
    #(r'(\S+\s*?)+?(?=\s*($|\n|\(|\)|&&|\|\|))', FILTER),
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
            match = regex.match(characters, pos)
            if match:
                text = match.group(0)
                if tag:
                    token = (text, tag)
                    tokens.append(token)
                break
        if not match:
            print('Illegal character: %s\\n' % characters[pos:])
            sys.exit(1)
        else:
            pos = match.end(0)
    return tokens

def filter_lex(characters):
    return lex(characters, token_exprs)
