# engine/lexer.py
from sly import Lexer

class QuantelLexerError(Exception):
    pass

class QuantelLexer(Lexer):
    tokens = {
        NAME, NUMBER, STRING,
        IMPORT, FUNC, RETURN, IF, ELSE, FOR, IN, WHILE, REPEAT, UNTIL,
        BREAK, CONTINUE, PROBE, RECORD,
        SCALAR, VECTOR, MATRIX, TENSOR, AUTO, # Added AUTO
        DTYPE,
        PLUS, MINUS, TIMES, DIVIDE, MOD, POWER, MATMUL,
        EQ, NE, LT, GT, LE, GE,
        AND, OR, NOT,
        ASSIGN, PLUS_ASSIGN, MINUS_ASSIGN, TIMES_ASSIGN, DIVIDE_ASSIGN, AT_ASSIGN,
        LPAREN, RPAREN, LBRACE, RBRACE, LBRACKET, RBRACKET,
        COMMA, SEMICOLON, DOT, ARROW, AMPERSAND, RANGE, STEP
    }

    def __init__(self):
        self.errors = []
        self.lineno = 1
        super().__init__()

    ignore = ' \t'

    # Line number tracking
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    # Comments
    @_(r'\#.*|//.*|/\*[\s\S]*?\*/') # Added multiline support just in case
    def COMMENT(self, t):
        pass

    # --- PRIORITY 1: Compound Operators ---
    @_(r'==')
    def EQ(self, t): return t
    @_(r'!=')
    def NE(self, t): return t
    @_(r'<=')
    def LE(self, t): return t
    @_(r'>=')
    def GE(self, t): return t
    @_(r'\+=')
    def PLUS_ASSIGN(self, t): return t
    @_(r'-=')
    def MINUS_ASSIGN(self, t): return t
    @_(r'\*=')
    def TIMES_ASSIGN(self, t): return t
    @_(r'/=')
    def DIVIDE_ASSIGN(self, t): return t
    @_(r'@=')
    def AT_ASSIGN(self, t): return t
    @_(r'->')
    def ARROW(self, t): return t
    @_(r'\.\.')
    def RANGE(self, t): return t
    @_(r'&&')
    def AND(self, t): return t
    @_(r'\|\|')
    def OR(self, t): return t

    # --- PRIORITY 2: Single Character Operators ---
    @_(r'=')
    def ASSIGN(self, t): return t
    @_(r'<')
    def LT(self, t): return t
    @_(r'>')
    def GT(self, t): return t
    @_(r'\+')
    def PLUS(self, t): return t
    @_(r'-')
    def MINUS(self, t): return t
    @_(r'\*')
    def TIMES(self, t): return t
    @_(r'/')
    def DIVIDE(self, t): return t
    @_(r'%')
    def MOD(self, t): return t
    @_(r'\^')
    def POWER(self, t): return t
    @_(r'@')
    def MATMUL(self, t): return t
    @_(r'!')
    def NOT(self, t): return t
    @_(r'&')
    def AMPERSAND(self, t): return t

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

    # --- PRIORITY 3: Numbers ---
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

    # --- Keywords & Identifiers ---
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
        'float32': 'DTYPE',
        'float64': 'DTYPE',
        'int32': 'DTYPE',
        'int64': 'DTYPE',
        'bool': 'DTYPE',
    }

    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def NAME(self, t):
        t.type = self.keywords.get(t.value, 'NAME')
        return t

    @_(r'\".*?\"')
    def STRING(self, t):
        t.value = t.value[1:-1]
        return t

    def error(self, t):
        msg = f"Lexer Error: Illegal character '{t.value[0]}' at line {self.lineno}"
        self.errors.append(msg)
        print(msg)
        self.index += 1

    def get_errors(self):
        return self.errors