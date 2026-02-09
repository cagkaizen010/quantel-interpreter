class SemanticError(Exception): pass

class Symbol:
    def __init__(self, name, symbol_type, category):
        self.name = name
        self.symbol_type = symbol_type
        # Adding .dtype as an alias for symbol_type for GUI compatibility
        self.dtype = symbol_type
        self.category = category

class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [{}]
        self.history = {}

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1: self.scopes.pop()

    def define(self, name, symbol):
        self.scopes[-1][name] = symbol
        # History stores every symbol for the GUI Symbols tab
        self.history[name] = symbol

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope: return scope[name]
        return None

    def analyze(self, node):
        self.visit(node)

    def visit(self, node):
        if node is None: return
        if isinstance(node, list):
            for item in node: self.visit(item)
            return
        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for attr in vars(node).values():
            if hasattr(attr, '__dict__') or isinstance(attr, list):
                self.visit(attr)

    # --- Declarations ---
    def visit_VarDecl(self, node):
        v_type = node.dtype
        if v_type == 'auto' and node.value:
            v_type = self.get_type(node.value)
        self.define(node.name, Symbol(node.name, v_type, 'variable'))

    def visit_PointerDecl(self, node):
        v_type = f"{node.dtype}*"
        self.define(node.name, Symbol(node.name, v_type, 'variable'))

    def visit_FuncDecl(self, node):
        rt = node.ret_type
        self.define(node.name, Symbol(node.name, rt, 'function'))
        self.enter_scope()
        self.visit(node.params)
        self.visit(node.body)
        self.exit_scope()

    def visit_FuncParam(self, node):
        self.define(node.name, Symbol(node.name, node.dtype, 'variable'))

    def visit_ForStmt(self, node):
        self.enter_scope()
        self.define(node.loop_var, Symbol(node.loop_var, 'int32', 'variable'))
        self.visit(node.body)
        self.exit_scope()

    # --- Type Inference Engine ---
    def get_type(self, node):
        if node is None: return "void"
        if isinstance(node, (int, float, str, bool)):
            if isinstance(node, bool): return "bool"
            if isinstance(node, int): return "int32"
            return "float32" if isinstance(node, float) else "string"

        cls = node.__class__.__name__
        if cls == 'Literal': return self.get_type(node.value)
        if cls == 'Identifier':
            s = self.lookup(node.name)
            return s.symbol_type if s else "unknown"
        if cls == 'BinOp':
            if node.op in ['&&', '||', 'AND', 'OR']: return "bool"
            return self.get_type(node.left)
        if cls == 'CompareOp': return "bool"
        if cls == 'FuncCall':
            s = self.lookup(node.name)
            return s.symbol_type if s else "void"
        if cls in ['ArrayLiteral', 'ArrayAccess']: return "float32"
        if cls == 'UnaryOp':
            if node.op == '&': return self.get_type(node.operand) + "*"
            return self.get_type(node.operand)
        return "unknown"

    def get_symbol_table_text(self):
        output = f"{'NAME':<18} | {'TYPE':<12}\n"
        output += "=" * 35 + "\n"
        for n, s in self.history.items():
            output += f"{n:<18} | {s.symbol_type:<12}\n"
        return output