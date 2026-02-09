class TACGenerator:
    """
    Converts AST into Three-Address Code (TAC) for debugging.
    """

    def __init__(self):
        self.temp_counter = 0
        self.instructions = []

    def new_temp(self):
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def generate(self, node):
        self.instructions = []
        self.temp_counter = 0
        if node:
            self.visit(node)
        return "\n".join(self.instructions)

    def visit(self, node):
        if node is None:
            return "null"

        if isinstance(node, list):
            for stmt in node: self.visit(stmt)
            return

        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        # FALLBACK: If we don't know the node, return its type name
        # This prevents "None" from appearing in the output
        return f"<{node.__class__.__name__}>"

    # --- Statements ---

    def visit_Program(self, node):
        self.visit(node.statements)

    def visit_Block(self, node):
        self.visit(node.statements)

    def visit_ExprStmt(self, node):
        child = getattr(node, 'expr', getattr(node, 'expression', None))
        if child: self.visit(child)

    def visit_VarDecl(self, node):
        # Format: var x: int = 5
        type_name = getattr(node, 'var_type', 'auto')

        if node.value:
            val = self.visit(node.value)
            self.instructions.append(f"{node.name} = {val}")
        else:
            self.instructions.append(f"ALLOC {node.name} ({type_name})")

    def visit_Assignment(self, node):
        target = getattr(node.target, 'name', 'unknown')
        val = self.visit(node.value)
        self.instructions.append(f"{target} {node.op} {val}")

    def visit_ReturnStmt(self, node):
        val = self.visit(node.value) if node.value else "void"
        self.instructions.append(f"RETURN {val}")

    def visit_IfStmt(self, node):
        condition = self.visit(node.condition)
        label_else = f"L_ELSE_{self.temp_counter}"
        label_end = f"L_END_{self.temp_counter}"

        self.instructions.append(f"IF_FALSE {condition} GOTO {label_else}")
        self.visit(node.then_block)
        self.instructions.append(f"GOTO {label_end}")
        self.instructions.append(f"{label_else}:")
        if node.else_block:
            self.visit(node.else_block)
        self.instructions.append(f"{label_end}:")

    # --- Expressions ---

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)

        temp = self.new_temp()
        self.instructions.append(f"{temp} = {left} {node.op} {right}")
        return temp

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        temp = self.new_temp()
        self.instructions.append(f"{temp} = {node.op}{operand}")
        return temp

    def visit_FuncCall(self, node):
        # Handle arguments
        args = []
        if node.args:
            for arg in node.args:
                args.append(str(self.visit(arg)))

        arg_str = ", ".join(args)

        # Function calls usually return a value, so we assign it to a temp
        temp = self.new_temp()
        self.instructions.append(f"{temp} = CALL {node.name}({arg_str})")
        return temp

    # --- Literals ---

    def visit_Literal(self, node):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        return str(node.value)

    def visit_Identifier(self, node):
        return node.name

    def visit_VectorLiteral(self, node):
        # Instead of printing the whole vector, just show a placeholder or short version
        count = len(node.elements)
        return f"[Vector size={count}]"

    def visit_MatrixLiteral(self, node):
        rows = len(node.rows)
        # Try to guess columns from first row
        cols = len(node.rows[0].elements) if rows > 0 else 0
        return f"[Matrix {rows}x{cols}]"

    def visit_ArrayLiteral(self, node):
        # Generic array fallback
        return f"[Array size={len(node.elements)}]"

    def visit_ArrayAccess(self, node):
        # 1. Find the array variable (handles different AST naming conventions)
        if hasattr(node, 'array'):
            arr_node = node.array
        elif hasattr(node, 'target'):
            arr_node = node.target
        elif hasattr(node, 'value'):
            arr_node = node.value
        elif hasattr(node, 'name'):
            arr_node = node.name
        else:
            # Fallback for debugging
            return "<Unknown Array>"

        # 2. Find the index (handles 'index' or 'subscript')
        if hasattr(node, 'index'):
            idx_node = node.index
        elif hasattr(node, 'subscript'):
            idx_node = node.subscript
        else:
            idx_node = None

        # 3. Generate the string
        arr_str = self.visit(arr_node)
        idx_str = self.visit(idx_node) if idx_node else "?"

        return f"{arr_str}[{idx_str}]"

    def visit_Slice(self, node):
        # 1. Get the start (lower bound)
        start = ""
        if hasattr(node, 'lower') and node.lower:
            start = self.visit(node.lower)
        elif hasattr(node, 'start') and node.start:
            start = self.visit(node.start)

        # 2. Get the end (upper bound)
        stop = ""
        if hasattr(node, 'upper') and node.upper:
            stop = self.visit(node.upper)
        elif hasattr(node, 'stop') and node.stop:
            stop = self.visit(node.stop)

        # 3. Return Python-style slice notation "start:stop"
        return f"{start}:{stop}"