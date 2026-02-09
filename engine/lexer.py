from sly import Lexer 

class QuantelLexerError(Exception):
    """Custom exception for Quantel Lexer errors."""
    pass

class QuantelLexer(Lexer):
    # Set of token names. This is always required
    tokens = { 
        "NAME", "NUMBER", "DTYPE", "SHAPE_TYPE", 
        "PLUS", "MINUS", "TIMES", "DIVIDE", "MODULO", "POWER", "DOT", "ARROW",
        "ASSIGN", "PLUS_ASSIGN", "MINUS_ASSIGN", "TIMES_ASSIGN", "DIVIDE_ASSIGN", "AT_ASSIGN",
        "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "LBRACE", "RBRACE", "COMMA", "SEMICOLON",
        "EQ", "NE", "GT", "LT", "GE", "LE", "AT",
        "IMPORT", "RECORD", "FUNC", "RETURN", 
        "IF", "ELSE", "FOR", "IN", "WHILE",
        "REPEAT", "UNTIL", "PROBE", "BREAK", "CONTINUE",
        "VOID" 
    }
    # pyright: ignore[reportUndefinedVariable]

    def __init__(self):
        self.errors = [] # Initialize an empty list to store errors
        self.lineno = 1 # Initialize line number
        super().__init__()

    # String containing ignored characters between tokens
    ignore = ' \t'

    # Regular expression rules for tokens
    # Basic Operators and Punctuation
    PLUS           = r'\+'
    MINUS          = r'-'
    TIMES          = r'\*'
    DIVIDE         = r'/'
    MODULO         = r'%'
    POWER          = r'\^'
    DOT            = r'\.'
    ARROW          = r'->' # For function signatures
    LPAREN         = r'\('
    RPAREN         = r'\)'
    LBRACKET       = r'\['
    RBRACKET       = r'\]'
    LBRACE         = r'\{'
    RBRACE         = r'\}'
    COMMA          = r','
    SEMICOLON      = r';'
    AT             = r'@' # For matrix multiplication and possibly special types

    # Assignment Operators
    PLUS_ASSIGN    = r'\+='
    MINUS_ASSIGN   = r'-='
    TIMES_ASSIGN   = r'\*='
    DIVIDE_ASSIGN  = r'/='
    AT_ASSIGN      = r'@='
    ASSIGN         = r'='

    # Comparison Operators
    EQ             = r'=='
    NE             = r'!='
    GE             = r'>='
    LE             = r'<='
    GT             = r'>'
    LT             = r'<'

    # Keywords (order matters for longer keywords before shorter prefixes)
    IMPORT          = r'import'
    RECORD          = r'record'
    FUNC            = r'func'
    RETURN          = r'return'
    IF              = r'if'
    ELSE            = r'else'
    FOR             = r'for'
    IN              = r'in'
    WHILE           = r'while'
    REPEAT          = r'repeat'
    UNTIL           = r'until'
    PROBE           = r'probe'
    BREAK           = r'break'
    CONTINUE        = r'continue'
    VOID            = r'void'


    # Data Types
    # Order matters: longer (e.g., float32) before shorter prefixes (e.g., float) if there was one
    DTYPE = r'float32|float64|float16|int32|int64|bool'

    # Shape Types (assuming simple forms for now, more complex regex for nested <> or [] if needed)
    # This might need refinement based on exact grammar of <num> within <> and []
    SHAPE_TYPE = r'scalar|vector<\d+>|matrix\[\d+,\s*\d+\]|tensor<[\d,\s]+>'


    # Numbers (Integers and Floats)
    @_(r'\d+\.\d*')
    def NUMBER_FLOAT(self, t): # Renamed to avoid clash with NUMBER token name for simplicity
        t.type = 'NUMBER'
        t.value = float(t.value)
        return t

    @_(r'\d+')
    def NUMBER_INT(self, t): # Renamed to avoid clash
        t.type = 'NUMBER'
        t.value = int(t.value)
        return t

    # Identifiers (NAME) - must be after keywords
    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def NAME(self, t):
        # SLY usually matches longest regex first, so explicit keyword tokens
        # defined before NAME will be matched first.
        return t

    # Line number tracking
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)
    
    # Comments (must be before any rules that might match the # character)
    @_(r'#.*')
    def COMMENT(self, t):
        pass # Discard comments

    # Error handling rule
    def error(self, t):
        self.errors.append(f"Token Type: LEX_ERROR, Value: '{t.value[0]}', Line: {self.lineno}, Column: {self.index}")
        self.index += 1
        # No longer raising QuantelLexerError here, allowing lexer to continue
    
    def get_errors(self):
        return self.errors