from sly import Lexer

class QuantelLexer(Lexer):
    tokens = {
        ID, NUMBER, STRING,
        IMPORT, FUNC, RETURN, IF, ELSE, FOR, IN, WHILE, REPEAT, UNTIL,
        BREAK, CONTINUE, PROBE, RECORD,
        SCALAR, VECTOR, MATRIX, TENSOR, AUTO,
        DTYPE, BOOLEAN,
        PLUS, MINUS, TIMES, DIVIDE, MOD, POWER, MATMUL,
        EQ, NE, LT, GT, LE, GE,
        AND, OR, NOT,
        ASSIGN, PLUS_ASSIGN, MINUS_ASSIGN, TIMES_ASSIGN, DIVIDE_ASSIGN, AT_ASSIGN,
        LPAREN, RPAREN, LBRACE, RBRACE, LBRACKET, RBRACKET,
        COMMA, SEMICOLON, DOT, ARROW, AMPERSAND, RANGE, STEP
    }

    ignore = ' \t'

    def __init__(self, print_errors=False):
        super().__init__()
        self.errors = []
        self.lineno = 1
        self.print_errors = print_errors

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    @_(r'\#.*|//.*|/\*[\s\S]*?\*/')
    def COMMENT(self, t):
        pass

    # --- Compound Operators ---
    EQ = r'=='
    NE = r'!='
    LE = r'<='
    GE = r'>='
    PLUS_ASSIGN = r'\+='
    MINUS_ASSIGN = r'-='
    TIMES_ASSIGN = r'\*='
    DIVIDE_ASSIGN = r'/='
    AT_ASSIGN = r'@='
    ARROW = r'->'
    RANGE = r'\.\.'
    AND = r'&&'
    OR = r'\|\|'

    # --- Single Character Operators ---
    ASSIGN = r'='
    LT = r'<'
    GT = r'>'
    PLUS = r'\+'
    MINUS = r'-'
    TIMES = r'\*'
    DIVIDE = r'/'
    MOD = r'%'
    POWER = r'\^'
    MATMUL = r'@'
    NOT = r'!'
    AMPERSAND = r'&'

    # --- Punctuation ---
    LPAREN = r'\('
    RPAREN = r'\)'
    LBRACE = r'\{'
    RBRACE = r'\}'
    LBRACKET = r'\['
    RBRACKET = r'\]'
    COMMA = r','
    SEMICOLON = r';'
    DOT = r'\.'

    @_(r'\d+\.\d+')
    def FLOAT_NUMBER(self, t):
        t.value = float(t.value)
        t.type = 'NUMBER'
        return t

    @_(r'\d+')
    def INT_NUMBER(self, t):
        t.value = int(t.value)
        t.type = 'NUMBER'
        return t

    keywords = {
        'import': 'IMPORT',
        'func': 'FUNC',
        'return': 'RETURN',
        'if': 'IF',
        'else': 'ELSE',
        'for': 'FOR',
        'in': 'IN',
        'step': 'STEP',
        'while': 'WHILE',
        'repeat': 'REPEAT',
        'until': 'UNTIL',
        'break': 'BREAK',
        'continue': 'CONTINUE',
        'probe': 'PROBE',
        'record': 'RECORD',
        'scalar': 'SCALAR',
        'vector': 'VECTOR',
        'matrix': 'MATRIX',
        'tensor': 'TENSOR',
        'auto': 'AUTO',
        # dtypes
        'float32': 'DTYPE',
        'float64': 'DTYPE',
        'float16': 'DTYPE',
        'int32': 'DTYPE',
        'int64': 'DTYPE',
        'bool': 'DTYPE',
        # Boolean Literals
        'true': 'BOOLEAN',
        'false': 'BOOLEAN',
    }

    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def ID(self, t):
        t.type = self.keywords.get(t.value, 'ID')
        return t

    @_(r'\".*?\"')
    def STRING(self, t):
        t.value = t.value[1:-1]
        return t

    def error(self, t):
        msg = f"Lexer Error: Illegal character '{t.value[0]}' at line {self.lineno}"
        self.errors.append(msg)
        if not self.print_errors:
            print(msg)
        self.index += 1

    def get_errors(self):
        return getattr(self, 'errors', [])