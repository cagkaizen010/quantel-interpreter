from pygments.lexer import RegexLexer, words, include
from pygments.token import Text, Comment, Keyword, Name, String, Number, Operator, Punctuation, Whitespace

class QuantelPygmentsLexer(RegexLexer):
    name = 'Quantel'
    aliases = ['quantel', 'qtl']
    filenames = ['*.qtl']

    # Based on the grammar analysis of CSC617M Syntax Definition.pdf
    # and CFG NOTES.pdf (e.g., control flow, data types, operators)
    tokens = {
        'root': [
            (r'\n', Whitespace), # Explicit newline
            (r'\s+', Whitespace), # Other whitespace (tabs, spaces)
            (r'#.*$', Comment.Single), # Single-line comments until end of line

            # Keywords (from T in grammar, and control flow)
            (words((
                'import', 'record', 'func', 'return', 'if', 'else', 'for', 'in',
                'while', 'repeat', 'until', 'probe', 'break', 'continue', 'void'
            ), suffix=r'\b'), Keyword.Reserved),

            # Data Types (DTYPE) - changed to Name.Builtin for potentially different color
            (words((
                'float32', 'float64', 'float16', 'int32', 'int64', 'bool',
                'scalar', 'vector', 'matrix', 'tensor'
            ), suffix=r'\b'), Name.Builtin), # Name.Builtin often has a distinct color

            # Operators (from T in grammar) - longest matches first implicitly
            (r'\+='           , Operator),
            (r'-='            , Operator),
            (r'\*='           , Operator),
            (r'/='            , Operator),
            (r'@='            , Operator),
            (r'=='            , Operator.Comparison),
            (r'!='            , Operator.Comparison),
            (r'>='            , Operator.Comparison),
            (r'<='            , Operator.Comparison),
            (r'->'            , Operator),
            (r'\.\.'          , Operator), # Range operator
            (r'[+\-*/%^@=<>!&]', Operator), # Generic operators, ensure specific ones are before this


            # Punctuation (from T in grammar)
            (r'[;,{}(),\[\]]', Punctuation),

            # Numbers (Integers and Floats)
            (r'\d+\.\d*', Number.Float), # Floating point numbers
            (r'\d+', Number.Integer),   # Integers

            # Identifiers (NAME) - must be after keywords and datatypes
            (r'[a-zA-Z_][a-zA-Z0-9_]*', Name.Other), # General identifiers

            # Strings (Uncommented and added basic string rules)
            (r'"(\\"|[^"])*"', String), # Double-quoted strings
            (r"'(\\'|[^'])*'", String), # Single-quoted strings
        ]
    }