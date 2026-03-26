import numpy as np
import sys
import threading
import copy
from engine.heap import QuantelHeap

# --- Custom Exceptions for Control Flow ---
class ReturnValue(Exception):
    def __init__(self, value): self.value = value

class BreakException(Exception): pass
class ContinueException(Exception): pass

class StepBackException(Exception):
    """Raised to jump back in the execution sequence."""
    pass

# --- Main Interpreter Class ---
class QuantelInterpreter:
    def __init__(self, step_callback=None):
        self.global_env = {}
        self.global_types = {}
        self.local_envs = []
        self.local_types_stack = []
        self.heap = QuantelHeap(size=10)
        self.execution_steps = 0
        self.MAX_STEPS = 10000
        self.step_callback = step_callback
        self.step_mode = False
        self.step_event = threading.Event()
        self.current_node = None
        
        # Simple Snapshot History
        self.history = []

    def get_current_env(self):
        return self.local_envs[-1] if self.local_envs else self.global_env

    def get_current_types(self):
        return self.local_types_stack[-1] if self.local_types_stack else self.global_types

    def take_snapshot(self, node):
        snapshot = {
            'node': node,
            'global_env': copy.deepcopy(self.global_env),
            'global_types': copy.deepcopy(self.global_types),
            'local_envs': copy.deepcopy(self.local_envs),
            'local_types_stack': copy.deepcopy(self.local_types_stack),
            'heap_memory': copy.deepcopy(self.heap.memory),
            'heap_free_pool': copy.deepcopy(self.heap.free_pool),
            'execution_steps': self.execution_steps
        }
        self.history.append(snapshot)
        if len(self.history) > 100: self.history.pop(0)

    def step_back(self):
        if len(self.history) < 2: return False
        self.history.pop() # Remove current
        prev = self.history[-1] # Peek at previous
        
        self.global_env = copy.deepcopy(prev['global_env'])
        self.global_types = copy.deepcopy(prev['global_types'])
        self.local_envs = copy.deepcopy(prev['local_envs'])
        self.local_types_stack = copy.deepcopy(prev['local_types_stack'])
        self.heap.memory = copy.deepcopy(prev['heap_memory'])
        self.heap.free_pool = copy.deepcopy(prev['heap_free_pool'])
        self.execution_steps = prev['execution_steps']
        self.current_node = prev['node']
        return True

    def interpret(self, tree):
        if not tree: return
        return self.visit(tree)

    def visit(self, node):
        if node is None: return None
        self.current_node = node

        # Trigger UI / Stepping
        if self.step_callback:
            is_stmt = node.__class__.__name__ in [
                'VarDecl', 'ConstDecl', 'Assignment', 'IfStmt', 'WhileStmt', 
                'ForStmt', 'FuncDecl', 'Return', 'Break', 'Continue', 
                'Probe', 'InputExpr', 'ExprStmt', 'FreeStmt', 'ShowHeap',
                'MallocExpr', 'RecordDecl', 'Import'
            ]
            if is_stmt:
                if self.step_mode: self.take_snapshot(node)
                self.step_callback(self)
                if self.step_mode:
                    self.step_event.wait()
                    self.step_event.clear()

        if isinstance(node, (int, float, str, bool, np.number)): return node
        if isinstance(node, list):
            res = None
            for stmt in node: res = self.visit(stmt)
            return res

        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"Interpreter Error: Unknown node type '{node.__class__.__name__}'")

    def visit_Program(self, node):
        if hasattr(node, 'imports'):
            for imp in node.imports: self.visit(imp)
        return self.visit(node.statements)

    def visit_Import(self, node): return None

    def visit_Block(self, node):
        res = None
        for stmt in node.statements: res = self.visit(stmt)
        return res

    def _check_type(self, name, val, expected_dtype, shape_node, lineno):
        if val is None or expected_dtype in ['auto', 'unknown']: return val
        # Basic validation
        if expected_dtype in ['int32', 'int'] and not isinstance(val, (int, np.integer)):
            raise Exception(f"Type Error at Line {lineno}: Expected int")
        return val

    def visit_VarDecl(self, node):
        val = self.visit_InputExpr(node.value, node.dtype) if node.value and node.value.__class__.__name__ == 'InputExpr' else self.visit(node.value)
        is_ptr = getattr(node, 'is_pointer', False)
        env = self.get_current_env()
        types = self.get_current_types()
        env[node.name] = val
        types[node.name] = (node.dtype, node.shape, is_ptr)
        return val

    def visit_ConstDecl(self, node):
        val = self.visit(node.value)
        env = self.get_current_env()
        types = self.get_current_types()
        env[node.name] = val
        types[node.name] = (node.dtype, node.shape, False)
        return val

    def visit_InputExpr(self, node, expected_dtype='string'):
        raw_val = input(node.prompt if node.prompt else "Enter value: ")
        try:
            if expected_dtype in ['int32', 'int']: return int(raw_val)
            if expected_dtype in ['float32', 'float64', 'float']: return float(raw_val)
            return raw_val
        except: return raw_val

    def visit_RecordDecl(self, node):
        env = self.get_current_env()
        env[node.name] = {'type': 'RECORD_DEF', 'fields': node.fields}
        return None

    def visit_PointerDecl(self, node):
        env = self.get_current_env()
        target_val = env.get(node.target)
        if target_val is None and self.local_envs:
            target_val = self.global_env.get(node.target)
        ptr_val = f"0x{id(target_val):x}" if target_val is not None else "0x0"
        env[node.name] = ptr_val
        return ptr_val

    def visit_IfStmt(self, node):
        if self.visit(node.condition): return self.visit(node.then_block)
        elif node.else_block: return self.visit(node.else_block)
        return None

    def visit_WhileStmt(self, node):
        while self.visit(node.condition):
            try: self.visit(node.body)
            except BreakException: break
            except ContinueException: continue
        return None

    def visit_RepeatUntilStmt(self, node):
        while True:
            try: self.visit(node.body)
            except BreakException: break
            except ContinueException: pass
            if self.visit(node.condition): break
        return None

    def visit_ForStmt(self, node):
        start = int(self.visit(node.range.start))
        end = int(self.visit(node.range.end))
        env = self.get_current_env()
        for i in range(start, end):
            env[node.loop_var] = i
            try: self.visit(node.body)
            except BreakException: break
            except ContinueException: continue

    def visit_Break(self, node): raise BreakException()
    def visit_Continue(self, node): raise ContinueException()
    def visit_FuncDecl(self, node): self.global_env[node.name] = node

    def visit_Return(self, node):
        raise ReturnValue(self.visit(node.value) if node.value else None)

    def visit_FuncCall(self, node):
        if node.name == 'print':
            print(" ".join([str(self.visit(a)) for a in node.args]))
            return None
        
        if node.name == 'load_csv':
            path = self.visit(node.args[0])
            # Load CSV using numpy (skipping header)
            data = np.genfromtxt(path, delimiter=',', skip_header=1)
            return data

        func_node = self.global_env.get(node.name)
        if not func_node: raise Exception(f"Function '{node.name}' not defined.")
        
        arg_values = [self.visit(a) for a in node.args]
        
        # Isolation: Push new local environment
        self.local_envs.append({})
        self.local_types_stack.append({})
        
        current_local = self.local_envs[-1]
        current_types = self.local_types_stack[-1]
        
        for p, v in zip(func_node.params, arg_values):
            current_local[p.name] = v
            current_types[p.name] = (p.dtype, p.shape)
            
        try: 
            self.visit(func_node.body)
            return None
        except ReturnValue as r: 
            return r.value
        finally: 
            # Isolation: Pop local environment
            self.local_envs.pop()
            self.local_types_stack.pop()

    def visit_BinOp(self, node):
        l, r, op = self.visit(node.left), self.visit(node.right), node.op
        if op == '+': return l + r
        if op == '-': return l - r
        if op == '*': return l * r
        if op == '/': return l / r
        if op == '@': return np.matmul(l, r)
        if op == '==': return l == r
        if op == '!=': return l != r
        if op == '<': return l < r
        if op == '>': return l > r
        if op == '<=': return l <= r
        if op == '>=': return l >= r
        return None

    def visit_CompareOp(self, node): return self.visit_BinOp(node)

    def visit_UnaryOp(self, node):
        val = self.visit(node.operand)
        if node.op == '-': return -val
        if node.op == '!': return not val
        if node.op == '&': return f"0x{id(val):x}"
        return val

    def visit_Assignment(self, node):
        env = self.get_current_env()
        types = self.get_current_types()
        target_name = node.target.name if hasattr(node.target, 'name') else None
        if target_name:
            val = self.visit(node.value)
            if node.op == '=': env[target_name] = val
            else:
                curr = env.get(target_name)
                if node.op == '+=': env[target_name] = curr + val
                elif node.op == '-=': env[target_name] = curr - val
                elif node.op == '*=': env[target_name] = curr * val
                elif node.op == '/=': env[target_name] = curr / val
        return None

    def visit_Literal(self, node): return node.value
    def visit_Identifier(self, node):
        # Local scope first, then global
        env = self.get_current_env()
        if node.name in env: return env[node.name]
        if node.name in self.global_env: return self.global_env[node.name]
        raise Exception(f"Variable '{node.name}' is not defined.")

    def visit_ArrayLiteral(self, node): return np.array([self.visit(el) for el in node.elements])
    def visit_ArrayAccess(self, node):
        target, idx = self.visit(node.name), self.visit(node.index)
        return target[idx]

    def visit_Slice(self, node):
        return slice(int(self.visit(node.start)) if node.start is not None else 0, int(self.visit(node.end)) if node.end is not None else None)

    def visit_ExprStmt(self, node): return self.visit(node.expr)
    def visit_Probe(self, node):
        val = self.visit(node.target)
        print(f"PROBE: {val}")
        return val

    def visit_MallocExpr(self, node): return self.heap.malloc(self.visit(node.value))
    def visit_FreeStmt(self, node): 
        env = self.get_current_env()
        self.heap.free(env.get(node.name))
    def visit_ShowHeap(self, node): print(self.heap)
