from engine.lexer import QuantelLexer 
from engine.parser import QuantelParser

if __name__ == "__main__":
    lexer = QuantelLexer()
    parser = QuantelParser()

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

            for token in tokens:
                print(token)

            # 2. Parsing: Analyze structure and execute
            # parser.parse(tokens)