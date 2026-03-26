import copy
import numpy as np
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

    def visit_ConstDecl(self, node):
        return self.visit_VarDecl(node)

    def visit_Assignment(self, node):
        node.value = self.visit(node.value)
        target_name = getattr(node.target, 'name', None)

        if target_name:
            # ONLY propagate if it's a standard assignment
            if node.op == '=' and self._is_constant(node.value):
                self.constants[target_name] = node.value.value
            else:
                # If it's +=, -=, etc., the variable is no longer a "known" simple constant
                if target_name in self.constants:
                    del self.constants[target_name]
        return node

    def visit_InputStmt(self, node):
        # User input makes the variable non-constant/unknown
        target_name = getattr(node.target, 'name', None)
        if target_name and target_name in self.constants:
            del self.constants[target_name]
        return node

    def visit_InputExpr(self, node):
        return node

    def visit_Identifier(self, node):
        # If the variable name is in our map, it means it's safe to fold
        # (because if it were in a loop, visit_WhileStmt would have deleted it)
        if node.name in self.constants:
            self.changed = True
            return Literal(self.constants[node.name], lineno=node.lineno)
        return node

    # --- Structural Optimizations ---

    def visit_Block(self, node):
        node.statements = self.visit(node.statements)
        return node

    def visit_BinOp(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        if self._is_constant(node.left) and self._is_constant(node.right):
            try:
                # Use _evaluate_binop safely
                val = self._evaluate_binop(node.op, node.left.value, node.right.value)
                self.changed = True
                return Literal(val, lineno=node.lineno)
            except Exception:
                # If error (e.g. 1/0), don't optimize, leave for runtime or other stages
                return node
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

    def visit_WhileStmt(self, node):
        # 1. Find every variable modified inside the loop body
        dirty_vars = self._get_modified_vars(node.body)

        # 2. Remove those variables from our constant map temporarily
        # so we don't accidentally fold them in the condition or body
        for var in dirty_vars:
            if var in self.constants:
                del self.constants[var]

        # 3. Now optimize the condition and body normally
        node.condition = self.visit(node.condition)
        node.body = self.visit(node.body)
        return node

    def visit_RepeatUntilStmt(self, node):
        # 1. Clear constants modified in the loop
        dirty_vars = self._get_modified_vars(node.body)
        for var in dirty_vars:
            if var in self.constants:
                del self.constants[var]

        # 2. Optimize the body and the condition
        node.body = self.visit(node.body)
        node.condition = self.visit(node.condition)
        return node

    def _is_constant(self, node):
        return node.__class__.__name__ == 'Literal'

    def _evaluate_binop(self, op, left, right):
        ops = {
            # Arithmetic
            '+':  lambda a, b: a + b,
            '-':  lambda a, b: a - b,
            '*':  lambda a, b: a * b,
            '/':  lambda a, b: a / b,
            '%':  lambda a, b: a % b,
            '^':  lambda a, b: a ** b,
            '@':  lambda a, b: np.matmul(a, b),
            
            # Comparisons (Wrapped in bool() to prevent NumPy/Int leaks)
            '>':  lambda a, b: bool(a > b),
            '<':  lambda a, b: bool(a < b),
            '>=': lambda a, b: bool(a >= b),
            '<=': lambda a, b: bool(a <= b),
            '==': lambda a, b: bool(a == b),
            '!=': lambda a, b: bool(a != b),
            
            # Logical Operators
            # Using bool() here ensures '&&' returns True/False, not the last truthy value
            '&&': lambda a, b: bool(a and b),
            '||': lambda a, b: bool(a or b)
        }
        return ops.get(op, lambda a, b: 0)(left, right)

    def _get_modified_vars(self, node):
        """Returns a set of variable names modified within this node/block."""
        modified = set()

        if node is None:
            return modified

        # If it's a list of statements (like a block body)
        if isinstance(node, list):
            for stmt in node:
                modified.update(self._get_modified_vars(stmt))

        # Standard Assignment (x = 5) or Augmented Assignment (x += 1)
        elif node.__class__.__name__ in ['Assignment', 'AugmentedAssignment']:
            if hasattr(node.target, 'name'):
                modified.add(node.target.name)

        # Input Statement (input(x, ...))
        elif node.__class__.__name__ == 'InputStmt':
            if hasattr(node.target, 'name'):
                modified.add(node.target.name)

        # For Loops (the loop variable changes every iteration!)
        elif node.__class__.__name__ == 'ForStmt':
            if hasattr(node, 'loop_var'):
                modified.add(node.loop_var)
            if hasattr(node, 'body'):
                modified.update(self._get_modified_vars(node.body))

        # If Statements (check both paths)
        elif node.__class__.__name__ == 'IfStmt':
            modified.update(self._get_modified_vars(node.then_block))
            if hasattr(node, 'else_block'):
                modified.update(self._get_modified_vars(node.else_block))

        # Generic recursion for anything with a 'body' (While, RepeatUntil, Blocks)
        elif hasattr(node, 'body'):
            modified.update(self._get_modified_vars(node.body))

        # Check 'statements' attribute if the class uses that name instead of body
        elif hasattr(node, 'statements'):
            modified.update(self._get_modified_vars(node.statements))

        return modified