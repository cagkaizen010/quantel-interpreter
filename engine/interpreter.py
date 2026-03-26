import numpy as np
import sys
import threading
from engine.heap import QuantelHeap


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
    def __init__(self, step_callback=None):
        self.global_env = {}
        self.global_types = {}
        self.local_env = None
        self.local_types = None

        # 1. Initialize the Heap with a fixed size to show "Gaps"
        self.heap = QuantelHeap(size=10)

        # 2. Safety counter for infinite loops
        self.execution_steps = 0
        self.MAX_STEPS = 10000
        self.step_callback = step_callback

        # 3. Debugging / Stepping State
        self.step_mode = False
        self.step_event = threading.Event()
        self.current_node = None

    def interpret(self, tree):
        if not tree:
            return
        try:
            return self.visit(tree)
        except Exception as e:
            # Let the caller (CLI or GUI) handle the error reporting
            raise e

    def visit(self, node):
        if node is None:
            return None

        # Track the node for the GUI (even if not stepping)
        self.current_node = node

        # 1. Safety Break for Infinite Loops
        self.execution_steps += 1
        if self.execution_steps > self.MAX_STEPS:
            raise Exception(f"Interpreter Safety Break: Maximum execution steps ({self.MAX_STEPS}) exceeded.")

        # 2. Trigger UI update and handle Stepping
        if self.step_callback:
            # Check if this is a "Top-Level" Statement that we want to step on
            # (We don't want to pause for every literal or sub-expression)
            is_stmt = node.__class__.__name__ in [
                'VarDecl', 'ConstDecl', 'Assignment', 'IfStmt', 'WhileStmt', 
                'ForStmt', 'FuncDecl', 'Return', 'Break', 'Continue', 
                'Probe', 'InputStmt', 'ExprStmt', 'FreeStmt', 'ShowHeap',
                'MallocExpr', 'RecordDecl', 'Import'
            ]
            
            if is_stmt:
                self.step_callback(self)
                if self.step_mode:
                    self.step_event.wait()  # Block until GUI signals
                    self.step_event.clear()

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
    #       Helper: Type Enforcement
    # ==========================================
    
    def _check_type(self, name, val, expected_dtype, shape_node, lineno):
        if val is None or expected_dtype == 'auto' or expected_dtype == 'unknown':
            return val

        # If a shape is provided (vector, matrix, tensor), we expect a numpy array
        if shape_node and shape_node.base_type != 'scalar':
            if not isinstance(val, np.ndarray):
                raise Exception(f"Runtime Type Error at Line {lineno}: Cannot assign {type(val).__name__} to '{name}' (expected {shape_node.base_type} of {expected_dtype})")
            return val
            
        # Scalar checks
        if expected_dtype in ['int32', 'int']:
            if not isinstance(val, (int, np.integer)):
                raise Exception(f"Runtime Type Error at Line {lineno}: Cannot assign {type(val).__name__} to '{name}' (expected {expected_dtype})")
        elif expected_dtype in ['float32', 'float64', 'float']:
            if not isinstance(val, (float, int, np.floating, np.integer)):
                raise Exception(f"Runtime Type Error at Line {lineno}: Cannot assign {type(val).__name__} to '{name}' (expected {expected_dtype})")
        elif expected_dtype == 'bool':
            if not isinstance(val, (bool, np.bool_)):
                raise Exception(f"Runtime Type Error at Line {lineno}: Cannot assign {type(val).__name__} to '{name}' (expected bool)")
        elif expected_dtype == 'string':
            if not isinstance(val, str):
                raise Exception(f"Runtime Type Error at Line {lineno}: Cannot assign {type(val).__name__} to '{name}' (expected string)")
        return val

    # ==========================================
    #       Declarations
    # ==========================================

    def visit_VarDecl(self, node):
        # Pass type info if it's an input call
        if node.value and node.value.__class__.__name__ == 'InputExpr':
            val = self.visit_InputExpr(node.value, node.dtype)
        else:
            val = self.visit(node.value) if node.value else None
        is_pointer = getattr(node, 'is_pointer', False)

        # Runtime Type Check (Skip if it's a pointer, as they hold addresses)
        if not is_pointer:
            val = self._check_type(node.name, val, node.dtype, node.shape, getattr(node, 'lineno', '?'))

        env = self.local_env if self.local_env is not None else self.global_env
        types = self.local_types if self.local_types is not None else self.global_types

        env[node.name] = val
        # Store both dtype and shape info
        types[node.name] = (node.dtype, node.shape, is_pointer)

        return val
    def visit_ConstDecl(self, node):
        val = self.visit(node.value)
        val = self._check_type(node.name, val, node.dtype, node.shape, getattr(node, 'lineno', '?'))
        
        env = self.local_env if self.local_env is not None else self.global_env
        types = self.local_types if self.local_types is not None else self.global_types
        
        env[node.name] = val
        types[node.name] = (node.dtype, node.shape, False)

        return val

    def visit_InputExpr(self, node, expected_dtype='string'):
        prompt = node.prompt if node.prompt else "Enter value: "
        raw_val = input(prompt)
        
        val = raw_val
        try:
            if expected_dtype in ['int32', 'int']:
                val = int(raw_val)
            elif expected_dtype in ['float32', 'float64', 'float']:
                val = float(raw_val)
            elif expected_dtype == 'bool':
                val = raw_val.lower() in ['true', '1', 'yes']
        except ValueError:
            raise Exception(f"Runtime Input Error: Expected {expected_dtype} but got '{raw_val}'")
        
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

        if node.name == 'input':
            if len(node.args) >= 2:
                prompt = str(self.visit(node.args[1]))
            elif len(node.args) == 1:
                prompt = str(self.visit(node.args[0]))
            else:
                prompt = ""
                
            val = input(prompt)
            # Standard numeric inference for built-in input() function
            try:
                if '.' in val: return float(val)
                return int(val)
            except (ValueError, TypeError):
                return val

        func_node = self.global_env.get(node.name)
        if not func_node:
            raise Exception(f"Function '{node.name}' not defined.")

        # Evaluate arguments in the CALLER'S scope before switching environments
        arg_values = [self.visit(a) for a in node.args]

        prev_env = self.local_env
        prev_types = self.local_types
        self.local_env = {}
        self.local_types = {}

        for param_node, arg_val in zip(func_node.params, arg_values):
            self.local_env[param_node.name] = arg_val
            self.local_types[param_node.name] = (param_node.dtype, param_node.shape)

        result = None
        try:
            self.visit(func_node.body)
        except ReturnValue as r:
            result = r.value
        finally:
            self.local_env = prev_env
            self.local_types = prev_types

        return result

    # ==========================================
    #           Math & Operations
    # ==========================================

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op

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
            if op == '&&': return left and right
            if op == '||': return left or right
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
        env = self.local_env if self.local_env is not None else self.global_env
        types = self.local_types if self.local_types is not None else self.global_types
        
        target_name = node.target.name if hasattr(node.target, 'name') else None

        if target_name:
            # 1. Get the target's type info first
            type_info = types.get(target_name, ('unknown', None, False))
            if isinstance(type_info, tuple):
                if len(type_info) == 3:
                    dtype, shape, is_ptr = type_info
                else:
                    dtype, shape = type_info
                    is_ptr = False
            else:
                dtype, shape, is_ptr = type_info, None, False

            # 2. Now evaluate the value (passing dtype if it's an input call)
            if node.value.__class__.__name__ == 'InputExpr':
                val = self.visit_InputExpr(node.value, dtype)
            else:
                val = self.visit(node.value)

            # 3. Type Checking
            if not is_ptr:
                val = self._check_type(target_name, val, dtype, shape, getattr(node, 'lineno', '?'))
            
            if node.op == '=':
                env[target_name] = val
            else:
                current = env.get(target_name)
                if current is None:
                    raise Exception(f"Variable '{target_name}' not defined.")

                if node.op == '+=':
                    env[target_name] = current + val
                elif node.op == '-=':
                    env[target_name] = current - val
                elif node.op == '*=':
                    env[target_name] = current * val
                elif node.op == '/=':
                    env[target_name] = current / val
        else:
            # Target is complex (like an array index), evaluate value normally
            val = self.visit(node.value)
            # Future: add type checking for complex targets here
            pass

        return val

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

    def visit_MallocExpr(self, node):
        val = self.visit(node.value)
        return self.heap.malloc(val)  # Returns address integer

    def visit_FreeStmt(self, node):
        # Get the address stored in the variable name
        env = self.local_env if self.local_env is not None else self.global_env
        address = env.get(node.name)
        self.heap.free(address)

    def visit_ShowHeap(self, node):
        print(self.heap)  # Uses the __repr__ we wrote earlier to show Gaps