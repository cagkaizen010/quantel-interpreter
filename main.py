from Lexer import CalcLexer
from Parser import CalcParser

if __name__ == "__main__":
    lexer = CalcLexer()
    parser = CalcParser()

    print("SLY Calculator (type 'exit' to stop)")
    while True:
        try:
            text = input('calc > ')
            if text == "exit":
                break
        except EOFError:
            break
        if text:
            # 1. Lexing: Break text into tokens
            tokens = lexer.tokenize(text)

            # 2. Parsing: Analyze structure and execute
            parser.parse(tokens)