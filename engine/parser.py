import difflib
from sly import Parser
from engine.lexer import QuantelLexer
import engine.ast as ast


class QuantelParser(Parser):
    tokens = QuantelLexer.tokens

    precedence = (
        ('right', 'ASSIGN', 'PLUS_ASSIGN', 'MINUS_ASSIGN', 'TIMES_ASSIGN', 'DIVIDE_ASSIGN', 'AT_ASSIGN'),
        ('left', 'OR'),
        ('left', 'AND'),
        ('left', 'EQ', 'NE', 'GT', 'LT', 'GE', 'LE'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD', 'MATMUL'),
        ('right', 'POWER'),
        ('right', 'UMINUS', 'NOT'),
        ('right', 'AMPERSAND'),
        ('left', 'DOT', 'LBRACKET'),
    )

    def __init__(self):
        self.errors = []
        self.source_lines = []
        self.prev_token = None  # Track the last successful token

    def parse(self, tokens, source_text=None):
        if source_text:
            self.source_lines = source_text.splitlines()

        # We wrap the token stream to track the previous token for context
        return super().parse(self._token_tracker(tokens))

    def _token_tracker(self, tokens):
        for tok in tokens:
            yield tok
            self.prev_token = tok

    # ==========================================
    #       PRO-MODE ERROR REPORTING
    # ==========================================
    def error(self, p):
        if not p:
            msg = "Syntax Error: Unexpected End of File. (Check for unclosed braces '{')"
            self.errors.append(msg)
            print(msg)
            return

        # 1. Determine "Expected" context based on grammar state
        # SLY doesn't expose a simple list of strings for expected tokens easily,
        # but we can infer them from the current token type and the previous token.
        hint = self._get_pro_hint(p)

        error_msg = (
            f"\n[!] SYNTAX ERROR | Line {p.lineno}\n"
            f"    Found:    '{p.value}' ({p.type})\n"
            f"    Previous: '{self.prev_token.value if self.prev_token else 'START'}'\n"
            f"    Hint:     {hint}"
        )

        self.errors.append(error_msg)
        print(error_msg)
        self.restart()

    def _get_pro_hint(self, p):

        # Case 1: Consecutive Operators (Double +, etc.)
        op_types = {'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD', 'MATMUL', 'ASSIGN', 'EQ'}
        if p.type in op_types and self.prev_token and self.prev_token.type in op_types:
            return f"Consecutive operators detected. '{self.prev_token.value}' cannot be followed by '{p.value}'."

        # Case 2: Missing Semicolon before a structural change
        if p.type in ('RBRACE', 'FUNC', 'IF', 'WHILE', 'RETURN') and self.prev_token:
            if self.prev_token.type not in ('SEMICOLON', 'RBRACE', 'LBRACE'):
                return f"Missing semicolon ';' after '{self.prev_token.value}'."

        # Case 3: Keyword Typo Analysis
        keywords = ['func', 'import', 'return', 'if', 'else', 'while', 'for', 'record', 'scalar', 'vector', 'matrix']
        if p.type == 'ID':
            matches = difflib.get_close_matches(p.value, keywords, n=1, cutoff=0.7)
            if matches:
                return f"Unrecognized identifier. Did you mean the keyword '{matches[0]}'?"

        # Case 4: Expression/Value expectations
        if self.prev_token and self.prev_token.type in op_types:
            return f"Expected an expression (number, variable, or '(') after '{self.prev_token.value}'."

        return "Verify syntax: check for mismatched brackets, missing semicolons, or invalid types."

    # ==========================================
    #             GRAMMAR RULES
    # ==========================================

    @_('import_list statements')
    def program(self, p):
        return ast.Program(p.import_list, p.statements)

    @_('import_list import_stmt')
    def import_list(self, p):
        return p.import_list + [p.import_stmt]

    @_('empty')
    def import_list(self, p):
        return []

    @_('IMPORT ID SEMICOLON')
    def import_stmt(self, p):
        return ast.Import(p.ID, lineno=p.lineno)

    @_('statements statement')
    def statements(self, p):
        return p.statements + [p.statement]

    @_('statement')
    def statements(self, p):
        return [p.statement]

    @_('declaration', 'assignment', 'control_flow', 'probe_stmt',
       'func_decl', 'record_decl', 'block', 'return_stmt',
       'break_stmt', 'continue_stmt', 'expr_stmt', 'error_stmt')
    def statement(self, p):
        return p[0]

    @_('error SEMICOLON', 'error RBRACE')
    def error_stmt(self, p):
        return None

    @_('dtype shape_type ID ASSIGN expr SEMICOLON')
    def declaration(self, p):
        return ast.VarDecl(p.dtype, p.shape_type, p.ID, p.expr, lineno=p.lineno)

    @_('dtype shape_type ID SEMICOLON')
    def declaration(self, p):
        return ast.VarDecl(p.dtype, p.shape_type, p.ID, None, lineno=p.lineno)

    @_('AUTO ID ASSIGN expr SEMICOLON')
    def declaration(self, p):
        return ast.VarDecl('auto', None, p.ID, p.expr, lineno=p.lineno)

    @_('ID ID SEMICOLON')
    def declaration(self, p):
        return ast.VarDecl(p.ID0, None, p.ID1, None, lineno=p.lineno)

    @_('dtype shape_type TIMES ID ASSIGN AMPERSAND ID SEMICOLON')
    def declaration(self, p):
        return ast.PointerDecl(p.dtype, p.shape_type, p.ID0, p.ID1, lineno=p.lineno)

    @_('FUNC ID LPAREN param_list RPAREN ARROW dtype shape_type block')
    def func_decl(self, p):
        return ast.FuncDecl(p.ID, p.param_list, p.dtype, p.shape_type, p.block, lineno=p.lineno)

    @_('FUNC ID LPAREN param_list RPAREN ARROW ID block')
    def func_decl(self, p):
        return ast.FuncDecl(p.ID0, p.param_list, p.ID1, None, p.block, lineno=p.lineno)

    @_('param_list COMMA param')
    def param_list(self, p):
        return p.param_list + [p.param]

    @_('param')
    def param_list(self, p):
        return [p.param]

    @_('empty')
    def param_list(self, p):
        return []

    @_('dtype shape_type ID')
    def param(self, p):
        return ast.FuncParam(p.dtype, p.shape_type, p.ID, lineno=p.lineno)

    @_('ID ID')
    def param(self, p):
        return ast.FuncParam(p.ID0, None, p.ID1, lineno=p.lineno)

    @_('LBRACE statements RBRACE')
    def block(self, p):
        return ast.Block(p.statements, lineno=p.lineno)

    @_('LBRACE RBRACE')
    def block(self, p):
        return ast.Block([], lineno=p.lineno)

    @_('IF LPAREN expr RPAREN block')
    def control_flow(self, p):
        return ast.IfStmt(p.expr, p.block, None, lineno=p.lineno)

    @_('IF LPAREN expr RPAREN block ELSE block')
    def control_flow(self, p):
        return ast.IfStmt(p.expr, p.block0, p.block1, lineno=p.lineno)

    @_('WHILE LPAREN expr RPAREN block')
    def control_flow(self, p):
        return ast.WhileStmt(p.expr, p.block, lineno=p.lineno)

    @_('REPEAT block UNTIL LPAREN expr RPAREN SEMICOLON')
    def control_flow(self, p):
        return ast.RepeatUntilStmt(p.block, p.expr, lineno=p.lineno)

    @_('FOR ID IN range block')
    def control_flow(self, p):
        return ast.ForStmt(p.ID, p.range, p.block, lineno=p.lineno)

    @_('NUMBER RANGE NUMBER')
    def range(self, p):
        return ast.Range(p.NUMBER0, p.NUMBER1, 1, lineno=p.lineno)

    @_('NUMBER RANGE NUMBER STEP expr')
    def range(self, p):
        return ast.Range(p.NUMBER0, p.NUMBER1, p.expr, lineno=p.lineno)

    @_('target ASSIGN expr SEMICOLON',
       'target PLUS_ASSIGN expr SEMICOLON',
       'target MINUS_ASSIGN expr SEMICOLON',
       'target TIMES_ASSIGN expr SEMICOLON',
       'target DIVIDE_ASSIGN expr SEMICOLON',
       'target AT_ASSIGN expr SEMICOLON')
    def assignment(self, p):
        return ast.Assignment(p.target, p[1], p.expr, lineno=p.lineno)

    @_('ID')
    def target(self, p):
        return ast.Identifier(p.ID, lineno=p.lineno)

    @_('target LBRACKET expr RBRACKET')
    def target(self, p):
        return ast.ArrayAccess(p.target, p.expr, lineno=p.lineno)

    @_('target LBRACKET expr COMMA expr RBRACKET')
    def target(self, p):
        return ast.ArrayAccess(p.target, [p.expr0, p.expr1], lineno=p.lineno)

    @_('target LBRACKET expr RANGE expr RBRACKET')
    def target(self, p):
        slice_node = ast.Slice(p.expr0, p.expr1, lineno=p.lineno)
        return ast.ArrayAccess(p.target, slice_node, lineno=p.lineno)

    @_('target DOT ID')
    def target(self, p):
        return ast.RecordAccess(p.target, p.ID, lineno=p.lineno)

    @_('BOOLEAN')
    def expr(self, p):
        val = True if p.BOOLEAN == 'true' else False
        return ast.Literal(val, lineno=p.lineno)

    @_('expr PLUS expr', 'expr MINUS expr', 'expr TIMES expr', 'expr DIVIDE expr',
       'expr MOD expr', 'expr MATMUL expr', 'expr POWER expr')
    def expr(self, p):
        return ast.BinOp(p.expr0, p[1], p.expr1, lineno=p.lineno)

    @_('expr EQ expr', 'expr NE expr', 'expr GT expr',
       'expr LT expr', 'expr GE expr', 'expr LE expr')
    def expr(self, p):
        return ast.CompareOp(p.expr0, p[1], p.expr1, lineno=p.lineno)

    @_('expr AND expr', 'expr OR expr')
    def expr(self, p):
        return ast.BinOp(p.expr0, p[1], p.expr1, lineno=p.lineno)

    @_('LPAREN expr RPAREN')
    def expr(self, p):
        return p.expr

    @_('MINUS expr %prec UMINUS')
    def expr(self, p):
        return ast.UnaryOp('-', p.expr, lineno=p.lineno)

    @_('NOT expr')
    def expr(self, p):
        return ast.UnaryOp('!', p.expr, lineno=p.lineno)

    @_('NUMBER')
    def expr(self, p):
        return ast.Literal(p.NUMBER, lineno=p.lineno)

    @_('STRING')
    def expr(self, p):
        return ast.Literal(p.STRING, lineno=p.lineno)

    @_('target')
    def expr(self, p):
        return p.target

    @_('ID LPAREN arg_list RPAREN')
    def expr(self, p):
        return ast.FuncCall(p.ID, p.arg_list, lineno=p.lineno)

    @_('LBRACKET arg_list RBRACKET')
    def expr(self, p):
        return ast.ArrayLiteral(p.arg_list, lineno=p.lineno)

    @_('arg_list COMMA expr')
    def arg_list(self, p):
        return p.arg_list + [p.expr]

    @_('expr')
    def arg_list(self, p):
        return [p.expr]

    @_('empty')
    def arg_list(self, p):
        return []

    @_('SCALAR')
    def shape_type(self, p):
        return ast.ShapeType('scalar', [], lineno=p.lineno)

    @_('VECTOR LT NUMBER GT')
    def shape_type(self, p):
        return ast.ShapeType('vector', [p.NUMBER], lineno=p.lineno)

    @_('MATRIX LT NUMBER COMMA NUMBER GT')
    def shape_type(self, p):
        return ast.ShapeType('matrix', [p.NUMBER0, p.NUMBER1], lineno=p.lineno)

    @_('TENSOR LT dim_list GT')
    def shape_type(self, p):
        return ast.ShapeType('tensor', p.dim_list, lineno=p.lineno)

    @_('dim_list COMMA NUMBER')
    def dim_list(self, p):
        return p.dim_list + [p.NUMBER]

    @_('NUMBER')
    def dim_list(self, p):
        return [p.NUMBER]

    @_('PROBE LPAREN expr RPAREN SEMICOLON')
    def probe_stmt(self, p):
        return ast.Probe(p.expr, lineno=p.lineno)

    @_('RETURN expr SEMICOLON')
    def return_stmt(self, p):
        return ast.Return(p.expr, lineno=p.lineno)

    @_('BREAK SEMICOLON')
    def break_stmt(self, p):
        return ast.Break(lineno=p.lineno)

    @_('CONTINUE SEMICOLON')
    def continue_stmt(self, p):
        return ast.Continue(lineno=p.lineno)

    @_('RECORD ID LBRACE decl_list RBRACE')
    def record_decl(self, p):
        return ast.RecordDecl(p.ID, p.decl_list, lineno=p.lineno)

    @_('decl_list declaration')
    def decl_list(self, p):
        return p.decl_list + [p.declaration]

    @_('declaration')
    def decl_list(self, p):
        return [p.declaration]

    @_('expr SEMICOLON')
    def expr_stmt(self, p):
        return ast.ExprStmt(p.expr, lineno=p.lineno)

    @_('DTYPE')
    def dtype(self, p):
        return p.DTYPE

    @_('')
    def empty(self, p):
        pass