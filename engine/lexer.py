from sly import Lexer 

class QuantelLexer(Lexer):
    # Set of token names. This is always required
    tokens = { "NAME", "NUMBER", "DTYPE", "SHAPE_TYPE", 
              "PLUS", "MINUS", "TIMES", 
              "DIVIDE", "ASSIGN", "LPAREN", "RPAREN"} 
    # pyright: ignore[reportUndefinedVariable]

    # String containing ignored characters between tokens
    ignore = ' \t'

    # Regular expression rules for tokens
    # NAME    = r'[a-zA-Z_][a-zA-Z0-9_]*'
    PLUS    = r'\+'
    MINUS   = r'-'
    TIMES   = r'\*'
    DIVIDE  = r'/'
    ASSIGN  = r'='
    LPAREN  = r'\('
    RPAREN  = r'\)'

    # Special cases

    # Special handling for distinct token types
    @_(r'\d+')
    def NUMBER(self, t):
        t.value = int(t.value)
        return t
    
    @_(r'scalar|vector<\d+>|matrix\[\d+\]|vector<\d+>')
    def SHAPE_TYPE(self, t):
        return t
    
    ## Identifiers and keywords
    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def NAME(self, t):
        if t.value in ['float32', 'float64', 'float16', 'int32', 'int64', 'bool']:
            t.type = 'DTYPE'
        # if t.value in ['scalar', 'vector<\\d>', 'matrix[\\d]', 'tensor<\\d>']:
        #     t.type = 'SHAPE_TYPE'
        return t

    # Line number tracking (optional but good practice)
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)
    
    #Error handling rule
    def error(self, t):
        print(f"Illegal character '{t.value[0]}'")
        self.index += 1

