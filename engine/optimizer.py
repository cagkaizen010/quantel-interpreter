import copy
from engine.ast import Literal, Assignment, Identifier, Block, VarDecl


class QuantelOptimizer:
    def __init__(self):
        self.changed = False
        self.constants = {}  # Tracks variable name -> constant value

    def optimize(self, node):
        iteration = 0
        while True:
            self.changed = False
            self.constants = {}  # Reset for each pass
            node = self.visit(node)
            iteration += 1
            if not self.changed or iteration > 10:
                break
        return node

    def visit(self, node):
        if isinstance(node, list):
            res_list = []
            for n in node:
                res = self.visit(n)
                if res is not None:
                    if isinstance(res, list):
                        res_list.extend(res)
                    else:
                        res_list.append(res)
            return res_list

        if hasattr(node, '__dict__'):
            method_name = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method_name, self.generic_visit)
            return visitor(node)
        return node

    def generic_visit(self, node):
        for key, value in node.__dict__.items():
            if isinstance(value, list):
                setattr(node, key, self.visit(value))
            elif hasattr(value, '__dict__'):
                setattr(node, key, self.visit(value))
        return node

    # --- Constant Propagation Logic ---

    def visit_VarDecl(self, node):
        node.value = self.visit(node.value)
        # If we declare 'var x = 50', remember it
        if self._is_constant(node.value):
            self.constants[node.name] = node.value.value
        return node

    def visit_Assignment(self, node):
        node.value = self.visit(node.value)
        target_name = getattr(node.target, 'name', None)

        if target_name:
            if self._is_constant(node.value):
                # Update constant map: i = 0
                self.constants[target_name] = node.value.value
            else:
                # If variable is assigned something non-constant, forget previous value
                if target_name in self.constants:
                    del self.constants[target_name]
        return node

    def visit_Identifier(self, node):
        # Swap 'i' for '0' if we know 'i' is 0
        if node.name in self.constants:
            self.changed = True
            val = self.constants[node.name]
            return Literal(val, lineno=node.lineno)
        return node

    # --- Structural Optimizations ---

    def visit_Block(self, node):
        new_statements = []
        for stmt in node.statements:
            result = self.visit(stmt)
            if result is None:
                continue

            if isinstance(result, list):
                new_statements.extend(result)
            elif result.__class__.__name__ == 'Block':
                new_statements.extend(result.statements)
            else:
                new_statements.append(result)

        node.statements = new_statements
        return node

    def visit_BinOp(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        if self._is_constant(node.left) and self._is_constant(node.right):
            val = self._evaluate_binop(node.op, node.left.value, node.right.value)
            self.changed = True
            return Literal(val, lineno=node.lineno)
        return node

    def visit_CompareOp(self, node):
        return self.visit_BinOp(node)

    def visit_IfStmt(self, node):
        node.condition = self.visit(node.condition)
        # Visit blocks even if we don't DCE yet to propagate constants inside them
        node.then_block = self.visit(node.then_block)
        node.else_block = self.visit(node.else_block)

        if self._is_constant(node.condition):
            self.changed = True
            return node.then_block if node.condition.value else node.else_block
        return node

    def visit_ForStmt(self, node):
        node.range.start = self.visit(node.range.start)
        node.range.end = self.visit(node.range.end)

        def get_val(n):
            if hasattr(n, 'value'): return n.value
            return n

        start_val = get_val(node.range.start)
        end_val = get_val(node.range.end)

        if isinstance(start_val, int) and isinstance(end_val, int):
            iterations = end_val - start_val
            if 0 < iterations <= 10:
                self.changed = True
                unrolled = []
                for i in range(start_val, end_val):
                    iter_assign = Assignment(
                        target=Identifier(node.loop_var, lineno=node.lineno),
                        op='=',
                        value=Literal(i, lineno=node.lineno),
                        lineno=node.lineno
                    )
                    unrolled.append(iter_assign)
                    unrolled.append(copy.deepcopy(node.body))
                # Note: Unrolled list will be processed by visit_Block's next pass
                return unrolled

        node.body = self.visit(node.body)
        return node

    def _is_constant(self, node):
        return node.__class__.__name__ == 'Literal'

    def _evaluate_binop(self, op, left, right):
        ops = {
            '+': lambda a, b: a + b, '-': lambda a, b: a - b,
            '*': lambda a, b: a * b, '/': lambda a, b: a // b,
            '>': lambda a, b: a > b, '<': lambda a, b: a < b,
            '==': lambda a, b: a == b
        }
        return ops.get(op, lambda a, b: 0)(left, right)