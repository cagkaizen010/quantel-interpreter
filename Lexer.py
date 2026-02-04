from sly import Lexer 

class CalcLexer(Lexer):
    # Set of token names. This is always required
    tokens = { NAME, NUMBER, PLUS, MINUS, TIMES, DIVIDE, ASSIGN, LPAREN, RPAREN}

    # String containing ignored characters between tokens
    ignore = '\t'

    # Regular expression rules for tokens
    NAME    = r'[a-zA-Z_][a-zA-Z0-9_]'
    PLUS    = r'\+'
    MINUS   = r'-'
    TIMES   = r'\*'
    DIVIDE  = r'/'
    ASSIGN  = r'='
    LPAREN  = r'\('
    RPAREN  = r'\)'

    # Special handling for distinct token types
    @_(r'\d+')
    def NUMBER(self, t):
        t.value = int(t.value)
        return t
    
    # Line number tracking (optional but good practice)
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)
    
    #Error handling rule
    def error(self, t):
        print(f"Illegal character '{t.value[0]}'")
        self.index += 1

