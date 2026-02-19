class Symbol:
    def __init__(self, name, symbol_type, category, shape=None, is_initialized=False, params_count=None):
        self.name = name
        self.symbol_type = symbol_type
        self.category = category  # 'variable', 'function', 'record'
        self.shape = shape # None means unknown, [] means scalar, [n] means vector, [n,m] means matrix
        self.is_initialized = is_initialized
        self.params_count = params_count


class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [{}]
        self.history = {}
        self.errors = []
        self.current_function = None

    def _report_error(self, node, message, hint):
        lineno = getattr(node, 'lineno', '??')
        self.errors.append(f"\n[!] SEMANTIC ERROR | Line {lineno}\n    Error:    {message}\n    Hint:     {hint}")

    # ==========================================
    #             SCOPE MANAGEMENT
    # ==========================================
    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1: self.scopes.pop()

    def define(self, node, name, symbol_type, category, shape=None, initialized=False, params_count=None):
        if name in self.scopes[-1]:
            self._report_error(node, f"Redeclaration of '{name}'", f"'{name}' is already defined in this block.")
            return None

        symbol = Symbol(name, symbol_type, category, shape, initialized, params_count)
        self.scopes[-1][name] = symbol
        # Always update history for the UI, using a unique key if local
        history_key = name if len(self.scopes) == 1 else f"{name} (local)"
        self.history[history_key] = symbol
        return symbol

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope: return scope[name]
        return None

    # ==========================================
    #             VISITOR CORE
    # ==========================================
    def analyze(self, node):
        self.visit(node)
        return self.errors

    def visit(self, node):
        if node is None or isinstance(node, (int, float, str, bool)): return
        if isinstance(node, list):
            for item in node: self.visit(item)
            return

        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for attr in vars(node).values():
            if hasattr(attr, '__dict__') or isinstance(attr, list):
                self.visit(attr)

    # ==========================================
    #           ERROR-SPECIFIC VISITORS
    # ==========================================

    def visit_RecordDecl(self, node):
        # ERROR 1: Duplicate Record
        self.define(node, node.name, 'record', 'record', initialized=True)

    def visit_PointerDecl(self, node):
        # ERROR 4: Pointer to Undefined
        if not self.lookup(node.target):
            self._report_error(node, "Undefined pointer target", f"'{node.target}' was never declared.")
        self.define(node, node.name, node.dtype, 'variable', initialized=True)

    def visit_VarDecl(self, node):
        v_shape = getattr(node.shape, 'dims', []) if node.shape else None
        v_type = node.dtype

        if v_type == 'auto' and node.value:
            v_type = self.get_type(node.value)
            v_shape = self.get_shape(node.value)

        self.define(node, node.name, v_type, 'variable', v_shape, node.value is not None)
        self.visit(node.value)

    def visit_FuncDecl(self, node):
        p_count = len(node.params) if node.params else 0
        self.define(node, node.name, node.ret_type, 'function', initialized=True, params_count=p_count)

        self.current_function = node
        self.enter_scope()
        if node.params:
            for p in node.params:
                self.define(p, p.name, p.dtype, 'variable', initialized=True)
        self.visit(node.body)
        self.exit_scope()
        self.current_function = None

    def visit_FuncCall(self, node):
        symbol = self.lookup(node.name)
        if not symbol:
            self._report_error(node, f"Undefined function '{node.name}'", "Check spelling.")
        else:
            # ERROR 2: Calling a non-function
            if symbol.category != 'function':
                self._report_error(node, f"'{node.name}' is not a function", f"It is a {symbol.category}.")

            # ERROR 8: Missing Arguments
            args_given = len(node.args) if node.args else 0
            if args_given != symbol.params_count:
                self._report_error(node, "Argument mismatch", f"Expected {symbol.params_count}, got {args_given}.")
        self.visit(node.args)

    def visit_UnaryOp(self, node):
        # Pointer check is now handled in visit_PointerDecl for declarations, 
        # but for general expressions it might still be needed if '&' is used elsewhere.
        if node.op == '&':
            if hasattr(node.operand, 'name'):
                if not self.lookup(node.operand.name):
                    self._report_error(node, "Undefined pointer target", f"'{node.operand.name}' was never declared.")
        self.visit(node.operand)

    def visit_Identifier(self, node):
        if not self.lookup(node.name):
            self._report_error(node, f"Undefined identifier '{node.name}'", "Variable is out of scope.")

    def visit_ArrayAccess(self, node):
        # ERROR 9: Indexing non-array
        target = node.name
        if hasattr(target, 'name'):
            s = self.lookup(target.name)
            # Only error if we are SURE it is a scalar (shape is [])
            if s and s.shape == []:
                self._report_error(node, "Invalid indexing", f"'{s.name}' is a scalar and cannot be indexed.")
        self.visit(target)
        self.visit(node.index)

    def visit_Assignment(self, node):
        # ERROR 7: Assignment Mismatch
        t_type = self.get_type(node.target)
        v_type = self.get_type(node.value)
        if t_type != v_type and "unknown" not in [t_type, v_type]:
            self._report_error(node, "Assignment mismatch", f"Cannot assign {v_type} to {t_type}.")
        self.visit(node.value)

    def visit_IfStmt(self, node):
        self.visit(node.condition)
        # ERROR 5: Scope Leakage Protection
        self.enter_scope()
        self.visit(node.then_block)
        self.exit_scope()
        if node.else_block:
            self.enter_scope()
            self.visit(node.else_block)
            self.exit_scope()

    def visit_WhileStmt(self, node):
        self.visit(node.condition)
        self.enter_scope()
        self.visit(node.body)
        self.exit_scope()

    def visit_RepeatUntilStmt(self, node):
        self.enter_scope()
        self.visit(node.body)
        self.exit_scope()
        self.visit(node.condition)

    def visit_ForStmt(self, node):
        self.visit(node.range)
        self.enter_scope()
        self.define(node, node.loop_var, 'int32', 'variable', shape=[], initialized=True)
        self.visit(node.body)
        self.exit_scope()

    def visit_Probe(self, node):
        self.visit(node.target)

    def visit_Return(self, node):
        # ERROR 6: Return Mismatch
        if not self.current_function: return
        actual = self.get_type(node.value)
        expected = self.current_function.ret_type
        if actual != expected:
            self._report_error(node, "Return mismatch", f"Expected {expected}, got {actual}.")

    def visit_ExprStmt(self, node):
        self.visit(node.expr)

    # ==========================================
    #           TYPE INFERENCE SYSTEM
    # ==========================================
    def get_type(self, node):
        if node is None: return "unknown"
        if isinstance(node, (int, float, str, bool)):
            return "int32" if isinstance(node, int) else "float32" if isinstance(node,
                                                                                 float) else "string" if isinstance(
                node, str) else "bool"

        cls = node.__class__.__name__
        if cls == 'Literal': return self.get_type(node.value)
        if cls == 'ArrayLiteral': return "matrix"  # Simplification for ERROR 7
        if cls == 'Identifier':
            s = self.lookup(node.name)
            if not s:
                return "unknown"
            return s.symbol_type
        if cls == 'BinOp':
            lt, rt = self.get_type(node.left), self.get_type(node.right)
            # ERROR 3: Invalid Matrix Math
            if lt != rt and "unknown" not in [lt, rt]:
                self._report_error(node, "Incompatible types", f"Cannot operate on {lt} and {rt}.")
            return lt
        if cls == 'ArrayAccess':
            return self.get_type(node.name) # Simplified
        return "unknown"

    def get_shape(self, node):
        if node is None: return None
        if isinstance(node, (int, float, str, bool)): return []

        cls = node.__class__.__name__
        if cls == 'Literal': return []
        if cls == 'ArrayLiteral': return [len(node.elements)]
        if cls == 'Identifier':
            s = self.lookup(node.name)
            return s.shape if s else None
        if cls == 'BinOp':
            ls = self.get_shape(node.left)
            rs = self.get_shape(node.right)
            if ls is not None: return ls
            if rs is not None: return rs
            return None
        if cls == 'ArrayAccess':
            # Slicing or indexing might change shape, but for now just pass through
            return self.get_shape(node.name)
        return None