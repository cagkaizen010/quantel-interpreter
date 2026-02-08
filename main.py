from sly import Lexer

class QuantelLexer(Lexer):
    # 1. Define the set of all possible token names
    # This is required by SLY to validate the lexer
    tokens = {
        ID, NUM, OPERATOR, KEYWORD, 
        IMPORT, RECORD, IF, ELSE, FOR, IN, WHILE, REPEAT,
        UNTIL, PROBE, BREAK, CONTINUE, FLOAT32, FLOAT64,
        FLOAT16, INT32, INT64, BOOL, SCALAR, VECTOR, 
        MATRIX, TENSOR, STEP
    }

    ignore = ' \t'

    OPERATOR = r'\.\.|==|!=|>=|<=|\+=|-=|\*=|/=|@=|=[+\-*/@%^><&;,.\{\}\(\)\[\]]'

    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    @_(r'[a-zA-Z][a-zA-Z0-9]*')
    def ID(self, t):
        keywords = {
            'import': 'IMPORT', 'record': 'RECORD', 'if': 'IF', 'else': 'ELSE',
            'for': 'FOR', 'in': 'IN', 'while': 'WHILE', 'repeat': 'REPEAT',
            'until': 'UNTIL', 'probe': 'PROBE', 'break': 'BREAK', 
            'continue': 'CONTINUE', 'float32': 'FLOAT32', 'float64': 'FLOAT64',
            'float16': 'FLOAT16', 'int32': 'INT32', 'int64': 'INT64',
            'bool': 'BOOL', 'scalar': 'SCALAR', 'vector': 'VECTOR',
            'matrix': 'MATRIX', 'tensor': 'TENSOR', 'step': 'STEP'
        }
        t.type = keywords.get(t.value, 'ID')
        return t

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += t.value.count('\n')

    def error(self, t):
        print(f"Illegal character '{t.value[0]}' at line {self.lineno}")
        self.index += 1

# test part
if __name__ == '__main__':
    sample_code = """
    import myLib;
    int32 scalar x = 10;
    float64 matrix<2,2> m;
    
    probe(x);
    
    for i in 1..10 step 2 {
        x += 1;
    }
    """
    
    lexer = QuantelLexer()
    print(f"{'LINE':<5} {'TYPE':<15} {'VALUE'}")
    print("-" * 35)
    
    for tok in lexer.tokenize(sample_code):
        print(f"{tok.lineno:<5} {tok.type:<15} {tok.value}")