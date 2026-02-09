from pygments.lexer import RegexLexer, words, bygroups
from pygments.token import Text, Comment, Keyword, Name, String, Number, Operator, Punctuation, Whitespace


class QuantelHighlighter(RegexLexer):
    name = 'Quantel'
    aliases = ['quantel', 'qtl']
    filenames = ['*.qtl']

    tokens = {
        'root': [
            # 1. Whitespace
            (r'\n', Whitespace),
            (r'\s+', Whitespace),

            # 2. Comments (Grey)
            (r'#.*$', Comment.Single),
            (r'//.*$', Comment.Single),
            (r'/\*[\s\S]*?\*/', Comment.Multiline),

            # 3. Function Declarations: "func main" -> "func"(Pink) "main"(Green)
            (r'(func)(\s+)([a-zA-Z_]\w*)', bygroups(Keyword, Whitespace, Name.Function)),

            # 4. Shape Types -> Green (Name.Class)
            # scalar, vector, matrix
            (words((
                'scalar', 'vector', 'matrix', 'tensor'
            ), suffix=r'\b'), Name.Class),

            # 5. Data Types -> Cyan (Keyword.Type)
            (words((
                'float32', 'float64', 'float16', 'int32', 'int64',
                'bool', 'string', 'void', 'auto'
            ), suffix=r'\b'), Keyword.Type),

            # 6. Control Flow & Keywords -> Pink (Keyword)
            (words((
                'import', 'record', 'return', 'if', 'else', 'for', 'in',
                'while', 'repeat', 'until', 'break', 'continue', 'as'
            ), suffix=r'\b'), Keyword),

            # 7. Built-in Functions -> Purple/Cyan (Name.Builtin)
            (words((
                'probe', 'print', 'len', 'shape', 'rows', 'cols'
            ), suffix=r'\b'), Name.Builtin),

            # 8. Boolean Literals -> Purple (Keyword.Constant)
            (words(('true', 'false'), suffix=r'\b'), Keyword.Constant),

            # Complex Operators -> Green (Name.Class)
            (r'->', Name.Attribute),  # Arrow
            (r'\.\.', Name.Attribute),  # Range
            (r'==|!=|>=|<=', Name.Attribute),  # Comparison
            (r'\+=|-=|\*=|/=|@=', Name.Attribute),  # Assignment Ops

            # Single Character Operators  Green -> (Name.Class)
            (r'[+\-*/%^@=<>!&|~]', Name.Attribute),

            # 10. Punctuation (White)
            (r'[(){}\[\],;.]', Punctuation),

            # 11. Numbers -> Purple (Number)
            (r'\d+\.\d+', Number.Float),
            (r'\d+', Number.Integer),

            # 12. Strings -> Yellow (String)
            (r'"(\\"|[^"])*"', String.Double),
            (r"'(\\'|[^'])*'", String.Single),

            # 13. Generic Variables -> White (Name)
            (r'[a-zA-Z_]\w*', Name),
        ]
    }