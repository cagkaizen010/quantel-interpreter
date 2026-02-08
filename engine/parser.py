from engine.lexer import QuantelLexer 
from sly import Parser

class QuantelParser(Parser):
    # Get the token list from the lexer (required)
    tokens = QuantelLexer.tokens

    # Precedence rules (to handle order of operations)
    precedence = (
        ('left', PLUS, MINUS), # pyright: ignore[reportUndefinedVariable]
        ('left', TIMES, DIVIDE), # type: ignore
        ('right', UMINUS), # Urany minus operator
    )

    # Dictionary to store variables
    decl= {}

    # Grammar Rules
    # The method name is usually 'statement' or 'expr'
    # The decorator defines the rule: e.g., "statement : NAME ASSIGN expr"

    @_('DTYPE NAME ASSIGN expr')
    def statement(self, p):
        self.decl[p.NAME] = p.expr

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
        if p[1] == "/": 
            if p.expr1 == 0:
                print("Error: Division by zero")
                return 0
            return p.expr0 / p.expr1

    @_('MINUS expr %prec UMINUS')
    def expr(self, p):
        return -p.expr

    @_('LPAREN expr RPAREN') # type: ignore
    def expr(self, p):
        return p.expr

    @_('NUMBER')
    def expr(self, p):
        return p.NUMBER

    @_('NAME')
    def expr(self, p):
        try:
            return self.decl[p.NAME]
        except LookupError:
            print(f"Undefined name '{p.NAME}'")
            return 0
