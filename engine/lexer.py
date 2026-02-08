from sly import Lexer 

class QuantelLexer(Lexer):
    # 1. Configuration: Easy to add new items here
    KEYWORDS = {
        'import', 'if', 'else', 'for', 'in', 'while', 
        'repeat', 'until', 'probe', 'break', 'continue', 'step'
    }

    DATATYPES = {
        'float32', 'float64', 'float16', 'int32', 'int64', 'bool'
    }

    # 2. Automatically build the token set
    base_tokens = { 
        "NAME", "NUMBER", "DTYPE", "SHAPE_TYPE",
        "PLUS", "MINUS", "TIMES", "DIVIDE", "ASSIGN", 
        "LPAREN", "RPAREN", "LBRACE", "RBRACE", 
        "SEMICOLON", "DOTDOT", "COMMA"
    }
    
    tokens = base_tokens | KEYWORDS | DATATYPES 

    ignore = ' \t'

    # Simple Literal Tokens
    PLUS      = r'\+'
    MINUS     = r'-'
    TIMES     = r'\*'
    DIVIDE    = r'/'
    ASSIGN    = r'='
    LPAREN    = r'\('
    RPAREN    = r'\)'
    LBRACE    = r'\{'
    RBRACE    = r'\}'
    SEMICOLON = r';'
    COMMA     = r','
    DOTDOT    = r'\.\.'

    @_(r'\d+')
    def NUMBER(self, t):
        t.value = int(t.value)
        return t
    
    @_(r'scalar|vector<\d+>|matrix<\d+,\s*\d+>|tensor<\d+(,\s*\d+)*>')
    def SHAPE_TYPE(self, t):
        return t
    
    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def NAME(self, t):
        if t.value in self.DATATYPES:
            t.type = 'DTYPE'
        elif t.value in self.KEYWORDS:
            t.type = t.value.upper()
        else:
            t.type = 'ID'
        return t

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)
    
    def error(self, t):
        print(f"Line {self.lineno}: Illegal character '{t.value[0]}'")
        self.index += 1