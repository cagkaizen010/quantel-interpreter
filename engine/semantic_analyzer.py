class Symbol:
    def __init__(self, name, symbol_type, category, shape=None, is_initialized=False, params_count=None):
        self.name = name
        self.symbol_type = symbol_type
        self.category = category  # 'variable', 'function', 'record'
        self.shape = shape  # None=unknown, []=scalar, [n]=vector, [n,m]=matrix
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
        # Use symbol_type as key for records to allow type-based lookup in visit_RecordAccess
        history_key = name if category != 'record' else name
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
        field_map = {decl.name: decl.dtype for decl in node.fields}
        self.define(node, node.name, node.name, 'record', initialized=True, params_count=field_map)
        self.visit(node.fields)

    def visit_RecordAccess(self, node):
        self.visit(node.record)
        target_type = self.get_type(node.record)
        record_def = self.history.get(target_type)

        if not record_def or record_def.category != 'record':
            self._report_error(node, "Invalid access", f"Type '{target_type}' is not a record.")
            return

        if node.field not in record_def.params_count:
            self._report_error(node, f"Field '{node.field}' not in '{target_type}'",
                               f"Available: {', '.join(record_def.params_count.keys())}")

    def visit_PointerDecl(self, node):
        if not self.lookup(node.target):
            self._report_error(node, "Undefined pointer target", f"'{node.target}' was never declared.")
        self.define(node, node.name, node.dtype, 'variable', initialized=True)

    def visit_VarDecl(self, node):
        v_shape = getattr(node.shape, 'dims', []) if node.shape else []
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
                p_shape = getattr(p.shape_type, 'dims', []) if hasattr(p, 'shape_type') else []
                self.define(p, p.name, p.dtype, 'variable', shape=p_shape, initialized=True)
        self.visit(node.body)
        self.exit_scope()
        self.current_function = None

    def visit_FuncCall(self, node):
        symbol = self.lookup(node.name)
        if not symbol:
            self._report_error(node, f"Undefined function '{node.name}'", "Check spelling.")
        else:
            if symbol.category != 'function':
                self._report_error(node, f"'{node.name}' is not a function", f"It is a {symbol.category}.")

            args_given = len(node.args) if node.args else 0
            if args_given != symbol.params_count:
                self._report_error(node, "Argument mismatch", f"Expected {symbol.params_count}, got {args_given}.")
        self.visit(node.args)

    def visit_UnaryOp(self, node):
        if node.op == '&' and hasattr(node.operand, 'name'):
            if not self.lookup(node.operand.name):
                self._report_error(node, "Undefined pointer target", f"'{node.operand.name}' was never declared.")
        self.visit(node.operand)

    def visit_Identifier(self, node):
        if not self.lookup(node.name):
            self._report_error(node, f"Undefined identifier '{node.name}'", "Variable is out of scope.")

    def visit_ArrayAccess(self, node):
        # Improved: Check both Identifier targets and expression targets
        target_name = getattr(node.target, 'name', None) if hasattr(node, 'target') else None
        if target_name:
            s = self.lookup(target_name)
            if s and s.shape == []:
                self._report_error(node, "Invalid indexing", f"'{s.name}' is a scalar and cannot be indexed.")
        self.visit(getattr(node, 'target', None))
        self.visit(node.index)

    def visit_Assignment(self, node):
        t_type = self.get_type(node.target)
        v_type = self.get_type(node.value)
        t_shape = self.get_shape(node.target)
        v_shape = self.get_shape(node.value)

        # ERROR 7: Assignment Type Mismatch
        if t_type != v_type and "unknown" not in [t_type, v_type]:
            self._report_error(node, "Assignment mismatch", f"Cannot assign {v_type} to {t_type}.")

        # [NEW] ADDED: Shape Mismatch Check
        if t_shape != v_shape and t_shape is not None and v_shape is not None:
            self._report_error(node, "Dimension mismatch",
                               f"Target expects shape {t_shape}, but value has shape {v_shape}.")

        self.visit(node.value)

    # [NEW] ADDED: Explicit BinOp Visitor for Mathematical Logic
    def visit_BinOp(self, node):
        l_shape = self.get_shape(node.left)
        r_shape = self.get_shape(node.right)

        if node.op == '@':
            if not l_shape or not r_shape:
                self._report_error(node, "Invalid Matmul", "Matrix multiplication requires defined shapes.")
            elif len(l_shape) < 1 or len(r_shape) < 1:
                self._report_error(node, "Matmul Error", "Cannot multiply scalars with '@'.")
            elif l_shape[-1] != r_shape[0]:
                self._report_error(node, "Inner Dimension Mismatch",
                                   f"Cannot multiply {l_shape} by {r_shape}. Inner dims {l_shape[-1]} and {r_shape[0]} must match.")

        # Element-wise check for +, -, *, /
        elif node.op in ['+', '-', '*', '/']:
            if l_shape != r_shape and len(l_shape) > 0 and len(r_shape) > 0:
                self._report_error(node, "Arithmetic Shape Mismatch",
                                   f"Shapes {l_shape} and {r_shape} must be identical for '{node.op}'.")

        self.visit(node.left)
        self.visit(node.right)

    def visit_IfStmt(self, node):
        self.visit(node.condition)
        self.enter_scope()
        self.visit(node.then_block)
        self.exit_scope()
        if node.else_block:
            self.enter_scope()
            self.visit(node.else_block)
            self.exit_scope()

    def visit_ForStmt(self, node):
        self.visit(node.range)
        self.enter_scope()
        self.define(node, node.loop_var, 'int32', 'variable', shape=[], initialized=True)
        self.visit(node.body)
        self.exit_scope()

    def visit_Return(self, node):
        if not self.current_function: return
        actual = self.get_type(node.value)
        expected = self.current_function.ret_type
        if actual != expected:
            self._report_error(node, "Return mismatch", f"Expected {expected}, got {actual}.")

    # ==========================================
    #           TYPE INFERENCE SYSTEM
    # ==========================================
    def get_type(self, node):
        if node is None: return "unknown"
        if isinstance(node, (int, float, str, bool)):
            if isinstance(node, bool): return "bool"
            if isinstance(node, int): return "int32"
            if isinstance(node, float): return "float32"
            return "string"

        cls = node.__class__.__name__
        if cls == 'Literal': return self.get_type(node.value)
        if cls == 'ArrayLiteral': return "float32"  # Defaulting to float for matrices
        if cls == 'Identifier':
            s = self.lookup(node.name)
            return s.symbol_type if s else "unknown"
        if cls == 'ArrayAccess':
            # Indexing usually reduces dimension but preserves base type
            return self.get_type(getattr(node, 'target', None) or getattr(node, 'name', None))
        if cls == 'RecordAccess':
            target_type = self.get_type(node.record)
            record_def = self.history.get(target_type)
            if record_def and record_def.category == 'record':
                return record_def.params_count.get(node.field, "unknown")
            return "unknown"
        if cls == 'BinOp':
            lt, rt = self.get_type(node.left), self.get_type(node.right)
            if lt != rt and "unknown" not in [lt, rt]:
                self._report_error(node, "Incompatible types", f"Cannot operate on {lt} and {rt}.")
            return lt
        return "unknown"

    def get_shape(self, node):
        if node is None: return []
        if isinstance(node, (int, float, str, bool)): return []
        cls = node.__class__.__name__

        if cls == 'Literal': return []

        if cls == 'ArrayLiteral':
            # Recursive Detection: [ [1,2], [3,4] ] -> [2, 2]
            if len(node.elements) > 0:
                return [len(node.elements)] + self.get_shape(node.elements[0])
            return [0]

        if cls == 'Identifier':
            s = self.lookup(node.name)
            return s.shape if s else []

        if cls == 'ArrayAccess':
            # Simplified: assuming full indexing results in a scalar for now
            return []

        if cls == 'BinOp':
            l_s = self.get_shape(node.left)
            r_s = self.get_shape(node.right)
            if node.op == '@':
                # Matmul Shape Inference: (m,n) @ (n,p) -> (m,p)
                res = l_s[:-1]
                if len(r_s) > 1: res += r_s[1:]
                return res
            return l_s

        return []