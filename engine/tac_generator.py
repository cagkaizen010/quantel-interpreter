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
            for stmt in node:
                self.visit(stmt)
            return

        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        return f"<{node.__class__.__name__}>"

    # --- Statements ---

    def visit_Program(self, node):
        self.visit(node.statements)

    def visit_FuncDecl(self, node):
        # Crucial: This allows the generator to enter the 'main' function
        self.instructions.append(f"FUNC {node.name}:")
        # Check if your AST uses node.body or node.block
        body = getattr(node, 'body', getattr(node, 'block', None))
        self.visit(body)
        self.instructions.append(f"ENDFUNC")

    def visit_Block(self, node):
        self.visit(node.statements)

    def visit_ExprStmt(self, node):
        child = getattr(node, 'expr', getattr(node, 'expression', None))
        if child:
            self.visit(child)

    def visit_VarDecl(self, node):
        if node.value:
            val = self.visit(node.value)
            self.instructions.append(f"{node.name} = {val}")
        else:
            type_name = getattr(node, 'var_type', 'auto')
            self.instructions.append(f"ALLOC {node.name} ({type_name})")

    def visit_Assignment(self, node):
        target = getattr(node.target, 'name', node.target if isinstance(node.target, str) else "unknown")
        val = self.visit(node.value)
        self.instructions.append(f"{target} {node.op} {val}")

    def visit_Probe(self, node):
        expr_node = getattr(node, 'expression', getattr(node, 'value', None))

        if expr_node is None:
            attrs = [v for k, v in vars(node).items() if k != 'lineno']
            expr_node = attrs[0] if attrs else None

        val = self.visit(expr_node)
        self.instructions.append(f"PROBE {val}")

    def visit_ReturnStmt(self, node):
        val = self.visit(node.value) if node.value else "void"
        self.instructions.append(f"RETURN {val}")

    def visit_IfStmt(self, node):
        label_id = self.temp_counter  # unique ID for labels
        self.temp_counter += 1

        condition = self.visit(node.condition)
        label_else = f"L_ELSE_{label_id}"
        label_end = f"L_END_{label_id}"

        self.instructions.append(f"IF_FALSE {condition} GOTO {label_else}")
        self.visit(node.then_block)
        self.instructions.append(f"GOTO {label_end}")
        self.instructions.append(f"{label_else}:")
        if node.else_block:
            self.visit(node.else_block)
        self.instructions.append(f"{label_end}:")

    def visit_ForStmt(self, node):
        # Fallback for loops that were NOT unrolled by the optimizer
        label_id = self.temp_counter
        self.temp_counter += 1

        start = self.visit(node.range.start)
        end = self.visit(node.range.end)

        loop_start = f"L_FOR_START_{label_id}"
        loop_end = f"L_FOR_END_{label_id}"

        self.instructions.append(f"{node.loop_var} = {start}")
        self.instructions.append(f"{loop_start}:")
        self.instructions.append(f"IF {node.loop_var} >= {end} GOTO {loop_end}")

        self.visit(node.body)

        self.instructions.append(f"{node.loop_var} = {node.loop_var} + 1")
        self.instructions.append(f"GOTO {loop_start}")
        self.instructions.append(f"{loop_end}:")

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

    def visit_Literal(self, node):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        return str(node.value)

    def visit_Identifier(self, node):
        return node.name

    def visit_FuncCall(self, node):
        args = [str(self.visit(arg)) for arg in (node.args or [])]
        arg_str = ", ".join(args)
        temp = self.new_temp()
        self.instructions.append(f"{temp} = CALL {node.name}({arg_str})")
        return temp