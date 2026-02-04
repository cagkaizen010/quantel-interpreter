from Lexer import CalcLexer
from sly import Parser

class CalcParser(Parser):
    # Get the token list from the lexer (required)
    tokens = CalcLexer.tokens

    # Precedence rules (to handle order of operations)
    precedence = (
        ('left', PLUS, MINUS),
        ('left', TIMES, DIVIDE),
        ('right', UMINUS), # Urany minus operator
    )

    # Dictionary to store variables
    names = {}

    # Grammar Rules
    # The method name is usually 'statement' or 'expr'
    # The decorator defines the rule: e.g., "statement : NAME ASSIGN expr"

    @_('NAME ASSIGN expr')
    def statement(self, p):
        self.names[p.NAME] = p.expr

    @_('expr')
    def statement(self, p):
        print(p.expr)
    
    @_('expr PLUS expr',
        'expr MINUS expr',
        'expr TIMES expr',
        'expr DIVIDE expr')
    def expr(self, p):
        if p[1] == "+": return p.expr0 + p.expr1
        if p[1] == "-": return p.expr0 - p.expr1
        if p[1] == "*": return p.expr0 * p.expr1
        if p[1] == "/": return p.expr0 / p.expr1

    @_('MINUS expr %prec UMINUS')
    def expr(self, p):
        return -p.expr

    @_('LPAREN expr RPAREN')
    def expr(self, p):
        return p.expr

    @_('NUMBER')
    def expr(self, p):
        return p.NUMBER

    @_('NAME')
    def expr(self, p):
        try:
            return self.names[p.NAME]
        except LookupError:
            print(f"Undefined name '{p.NAME}'")
            return 0
