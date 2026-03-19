import numpy as np
import sys
import engine.ast as ast


# --- Custom Exceptions for Control Flow ---
class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value


class BreakException(Exception):
    pass


class ContinueException(Exception):
    pass


# --- Main Interpreter Class ---
class QuantelInterpreter:
    def __init__(self):
        self.global_env = {}
        self.local_env = None

    def interpret(self, tree):
        if not tree:
            return
        try:
            return self.visit(tree)
        except Exception as e:
            print(f"\n--- Runtime Error ---\n{e}")
            raise e

    def visit(self, node):
        if node is None:
            return None

        if isinstance(node, (int, float, str, bool, np.number)):
            return node

        if isinstance(node, list):
            last_result = None
            for stmt in node:
                last_result = self.visit(stmt)
            return last_result

        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        # Report Line Number
        lineno = getattr(node, 'lineno', 'Unknown')
        raise Exception(f"Interpreter Error at Line {lineno}: Unknown node type '{node.__class__.__name__}'")

    # ==========================================
    #       Top Level
    # ==========================================

    def visit_Program(self, node):
        if hasattr(node, 'imports'):
            for imp in node.imports:
                self.visit(imp)
        return self.visit(node.statements)

    def visit_Import(self, node):
        return None

    def visit_Block(self, node):
        result = None
        for stmt in node.statements:
            result = self.visit(stmt)
        return result

    # ==========================================
    #       Declarations
    # ==========================================

    def visit_VarDecl(self, node):
        val = None
        if hasattr(node, 'value') and node.value is not None:
            val = self.visit(node.value)
        elif node.dtype not in ['auto', 'int32', 'float32', 'float64', 'bool', 'string']:
            # Record instantiation
            env = self.local_env if self.local_env is not None else self.global_env
            rec_def = env.get(node.dtype)
            if rec_def is None and self.local_env is not None:
                rec_def = self.global_env.get(node.dtype)
            
            if rec_def and isinstance(rec_def, dict) and rec_def.get('type') == 'RECORD_DEF':
                val = {field.name: None for field in rec_def['fields']}

        env = self.local_env if self.local_env is not None else self.global_env
        env[node.name] = val
        return val

    def visit_ConstDecl(self, node):
        val = self.visit(node.value)
        env = self.local_env if self.local_env is not None else self.global_env
        env[node.name] = val
        return val

    def visit_InputStmt(self, node):
        prompt = node.prompt if node.prompt else f"Enter value for {node.name}: "
        val = input(prompt)
        # Try to convert to number if possible
        try:
            if '.' in val: val = float(val)
            else: val = int(val)
        except ValueError:
            pass
        
        env = self.local_env if self.local_env is not None else self.global_env
        env[node.name] = val
        return val

    def visit_RecordDecl(self, node):
        env = self.local_env if self.local_env is not None else self.global_env
        env[node.name] = {'type': 'RECORD_DEF', 'fields': node.fields}
        return None

    def visit_PointerDecl(self, node):
        # Pointer logic: store the address
        env = self.local_env if self.local_env is not None else self.global_env
        target_val = env.get(node.target)
        if target_val is None and self.local_env is not None:
            target_val = self.global_env.get(node.target)

        ptr_val = f"0x{id(target_val):x}" if target_val is not None else "0x0"
        env[node.name] = ptr_val
        return ptr_val

    # ==========================================
    #           Control Flow
    # ==========================================

    def visit_IfStmt(self, node):
        if self.visit(node.condition):
            return self.visit(node.then_block)
        elif node.else_block:
            return self.visit(node.else_block)
        return None

    def visit_WhileStmt(self, node):
        while self.visit(node.condition):
            try:
                self.visit(node.body)
            except BreakException:
                break
            except ContinueException:
                continue
        return None

    def visit_RepeatUntilStmt(self, node):
        while True:
            try:
                self.visit(node.body)
            except BreakException:
                break
            except ContinueException:
                pass
            if self.visit(node.condition):
                break
        return None

    def visit_ForStmt(self, node):
        iterable_node = node.range

        # Handle 'Range' node vs generic Iterable
        if iterable_node.__class__.__name__ == 'Range':
            # Note: visit() now handles if start/end are raw ints
            start = int(self.visit(iterable_node.start))
            end = int(self.visit(iterable_node.end))
            step = 1
            if iterable_node.step:
                step = int(self.visit(iterable_node.step))
            iterator = range(start, end, step)
        else:
            iterator = self.visit(iterable_node)

        env = self.local_env if self.local_env is not None else self.global_env

        for i in iterator:
            env[node.loop_var] = i
            try:
                self.visit(node.body)
            except BreakException:
                break
            except ContinueException:
                continue

    def visit_Break(self, node):
        raise BreakException()

    def visit_Continue(self, node):
        raise ContinueException()

    # ==========================================
    #           Functions
    # ==========================================

    def visit_FuncDecl(self, node):
        self.global_env[node.name] = node
        return None

    def visit_Return(self, node):
        val = self.visit(node.value) if node.value else None
        raise ReturnValue(val)

    def visit_FuncCall(self, node):
        if node.name == 'print':
            args = [str(self.visit(a)) for a in node.args]
            print(" ".join(args))
            return None

        func_node = self.global_env.get(node.name)
        if not func_node:
            raise Exception(f"Function '{node.name}' not defined.")

        prev_env = self.local_env
        self.local_env = {}

        for param_node, arg_expr in zip(func_node.params, node.args):
            arg_value = self.visit(arg_expr)
            self.local_env[param_node.name] = arg_value

        result = None
        try:
            self.visit(func_node.body)
        except ReturnValue as r:
            result = r.value
        finally:
            self.local_env = prev_env

        return result

    # ==========================================
    #           Math & Operations
    # ==========================================

    def visit_BinOp(self, node):
        op = node.op

        # Short-circuiting
        if op == '&&':
            left = self.visit(node.left)
            if not left: return False
            right = self.visit(node.right)
            return left and right
        if op == '||':
            left = self.visit(node.left)
            if left: return True
            right = self.visit(node.right)
            return left or right

        left = self.visit(node.left)
        right = self.visit(node.right)

        try:
            if op == '+': return left + right
            if op == '-': return left - right
            if op == '*': return left * right
            if op == '/': return left / right
            if op == '%': return left % right
            if op == '^': return left ** right
            if op == '@': return np.matmul(left, right)
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '<': return left < right
            if op == '>': return left > right
            if op == '<=': return left <= right
            if op == '>=': return left >= right
        except Exception as e:
            lineno = getattr(node, 'lineno', '?')
            raise Exception(f"Math Error at Line {lineno} ({op}): {e}")

        raise Exception(f"Runtime Error: Unknown operator '{op}'")

    def visit_CompareOp(self, node):
        return self.visit_BinOp(node)

    def visit_UnaryOp(self, node):
        val = self.visit(node.operand)
        if node.op == '-': return -val
        if node.op == '!': return not val
        if node.op == '&': return f"0x{id(val):x}"
        return val

    def visit_Assignment(self, node):
        val = self.visit(node.value)
        
        # Helper to get the actual container and key for assignment
        def get_target_info(target_node):
            if isinstance(target_node, ast.Identifier):
                env = self.local_env if self.local_env is not None else self.global_env
                if target_node.name in env: return env, target_node.name
                if self.local_env is not None and target_node.name in self.global_env:
                    return self.global_env, target_node.name
                return env, target_node.name
            elif isinstance(target_node, ast.ArrayAccess):
                container = self.visit(target_node.name)
                if isinstance(target_node.index, list):
                    index = tuple([self.visit(x) for x in target_node.index])
                else:
                    index = self.visit(target_node.index)
                return container, index
            elif isinstance(target_node, ast.RecordAccess):
                container = self.visit(target_node.record)
                return container, target_node.field
            else:
                raise Exception(f"Unsupported assignment target: {type(target_node)}")

        container, key = get_target_info(node.target)

        if node.op == '=':
            container[key] = val
        else:
            current = container[key]
            if current is None:
                raise Exception(f"Variable or field at '{key}' is not initialized.")

            if node.op == '+=': container[key] = current + val
            elif node.op == '-=': container[key] = current - val
            elif node.op == '*=': container[key] = current * val
            elif node.op == '/=': container[key] = current / val
            elif node.op == '@=': container[key] = np.matmul(current, val)
            
        return val

    def visit_RecordAccess(self, node):
        record = self.visit(node.record)
        if not isinstance(record, dict):
             raise Exception(f"Runtime Error: Expected record, got {type(record)}")
        return record.get(node.field)

    # ==========================================
    #           Data Types & Slicing
    # ==========================================

    def visit_Literal(self, node):
        return node.value

    def visit_Identifier(self, node):
        env = self.local_env if self.local_env is not None else self.global_env
        val = env.get(node.name)
        if val is None and self.local_env is not None:
            val = self.global_env.get(node.name)
        if val is None:
            lineno = getattr(node, 'lineno', '?')
            raise Exception(f"Runtime Error (Line {lineno}): Variable '{node.name}' is not defined.")
        return val

    def visit_ArrayLiteral(self, node):
        elements = [self.visit(el) for el in node.elements]
        return np.array(elements)

    def visit_ArrayAccess(self, node):
        target = self.visit(node.name)

        # Handle Slice vs Index vs List of Indices
        if hasattr(node.index, 'start'):  # It's a Slice node
            index = self.visit(node.index)
        elif isinstance(node.index, list):  # Multi-dimensional [i, j]
            index = tuple([self.visit(x) for x in node.index])
        else:  # Standard index
            index = self.visit(node.index)

        try:
            return target[index]
        except Exception as e:
            lineno = getattr(node, 'lineno', '?')
            raise Exception(f"Array Access Error (Line {lineno}): {e}")

    def visit_Slice(self, node):
        start = self.visit(node.start) if node.start is not None else 0
        end = self.visit(node.end) if node.end is not None else None
        return slice(int(start), int(end))

    # ==========================================
    #           Debugging Tools
    # ==========================================

    def visit_ExprStmt(self, node):
        if node.expr:
            return self.visit(node.expr)
        return None

    def visit_Probe(self, node):
        val = self.visit(node.target)
        lineno = getattr(node, 'lineno', '?')

        print(f"\n   [PROBE TOOL @ Line {lineno}]")
        print(f"   Value: {val}")

        if isinstance(val, np.ndarray):
            print(f"   Shape: {val.shape}")
            print(f"   Dtype: {val.dtype}")
        elif isinstance(val, str):
            print(f"   Type:  String")
        else:
            print(f"   Type:  {type(val).__name__}")
        print("")

        return val