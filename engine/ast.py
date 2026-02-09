# engine/ast.py
class Node:
    def __init__(self, lineno=0):
        self.lineno = lineno

class Program(Node):
    def __init__(self, imports, statements):
        super().__init__()
        self.imports = imports
        self.statements = statements

class Block(Node):
    def __init__(self, statements, lineno=0):
        super().__init__(lineno)
        self.statements = statements

class Import(Node):
    def __init__(self, name, lineno=0):
        super().__init__(lineno)
        self.name = name

# --- Declarations ---
class VarDecl(Node):
    def __init__(self, dtype, shape, name, value=None, lineno=0):
        super().__init__(lineno)
        self.dtype = dtype      # 'float32', 'auto', etc.
        self.shape = shape      # ShapeType node or None (if auto)
        self.name = name
        self.value = value

class PointerDecl(Node):
    def __init__(self, dtype, shape, pointer_name, target_name, lineno=0):
        super().__init__(lineno)
        self.dtype = dtype
        self.shape = shape
        self.name = pointer_name
        self.target = target_name

class ShapeType(Node):
    def __init__(self, base_type, dims, lineno=0):
        super().__init__(lineno)
        self.base_type = base_type # 'scalar', 'vector', 'matrix', 'tensor'
        self.dims = dims # list of numbers

class RecordDecl(Node):
    def __init__(self, name, fields, lineno=0):
        super().__init__(lineno)
        self.name = name
        self.fields = fields

# --- Functions ---
class FuncDecl(Node):
    def __init__(self, name, params, ret_type, ret_shape, body, lineno=0):
        super().__init__(lineno)
        self.name = name
        self.params = params
        self.ret_type = ret_type
        self.ret_shape = ret_shape
        self.body = body

class FuncParam(Node):
    def __init__(self, dtype, shape, name, lineno=0):
        super().__init__(lineno)
        self.dtype = dtype
        self.shape = shape
        self.name = name

class FuncCall(Node):
    def __init__(self, name, args, lineno=0):
        super().__init__(lineno)
        self.name = name
        self.args = args

# --- Statements ---
class Assignment(Node):
    def __init__(self, target, op, value, lineno=0):
        super().__init__(lineno)
        self.target = target
        self.op = op
        self.value = value

class IfStmt(Node):
    def __init__(self, condition, then_block, else_block=None, lineno=0):
        super().__init__(lineno)
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

class WhileStmt(Node):
    def __init__(self, condition, body, lineno=0):
        super().__init__(lineno)
        self.condition = condition
        self.body = body

class RepeatUntilStmt(Node):
    def __init__(self, body, condition, lineno=0):
        super().__init__(lineno)
        self.body = body
        self.condition = condition

class ForStmt(Node):
    def __init__(self, loop_var, range_node, body, lineno=0):
        super().__init__(lineno)
        self.loop_var = loop_var
        self.range = range_node
        self.body = body

class Range(Node):
    # Used for For Loops (has step)
    def __init__(self, start, end, step, lineno=0):
        super().__init__(lineno)
        self.start = start
        self.end = end
        self.step = step

class Return(Node):
    def __init__(self, value, lineno=0):
        super().__init__(lineno)
        self.value = value

class Break(Node):
    pass

class Continue(Node):
    pass

class Probe(Node):
    def __init__(self, target, lineno=0):
        super().__init__(lineno)
        self.target = target

class ExprStmt(Node):
    def __init__(self, expr, lineno=0):
        super().__init__(lineno)
        self.expr = expr

# --- Expressions ---
class BinOp(Node):
    def __init__(self, left, op, right, lineno=0):
        super().__init__(lineno)
        self.left = left
        self.op = op
        self.right = right

class CompareOp(Node):
    def __init__(self, left, op, right, lineno=0):
        super().__init__(lineno)
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(Node):
    def __init__(self, op, operand, lineno=0):
        super().__init__(lineno)
        self.op = op
        self.operand = operand

class Literal(Node):
    def __init__(self, value, lineno=0):
        super().__init__(lineno)
        self.value = value

class Identifier(Node):
    def __init__(self, name, lineno=0):
        super().__init__(lineno)
        self.name = name

class ArrayAccess(Node):
    def __init__(self, name, index, lineno=0):
        super().__init__(lineno)
        self.name = name
        self.index = index # Can be Expr or Slice

class Slice(Node):
    # Used for Array Indexing [0..5]
    def __init__(self, start, end, lineno=0):
        super().__init__(lineno)
        self.start = start
        self.end = end

class RecordAccess(Node):
    def __init__(self, record, field, lineno=0):
        super().__init__(lineno)
        self.record = record
        self.field = field

class ArrayLiteral(Node):
    def __init__(self, elements, lineno=0):
        super().__init__(lineno)
        self.elements = elements