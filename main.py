# from engine.lexer import QuantelLexer 
# from engine.parser import QuantelParser

# if __name__ == "__main__":
#     lexer = QuantelLexer()
#     parser = QuantelParser()

#     print("SLY Calculator (type 'exit' to stop)")
#     while True:
#         try:
#             text = input('calc > ')
#             if text == "exit":
#                 break
#         except EOFError:
#             break
#         if text:
#             # 1. Lexing: Break text into tokens
#             tokens = lexer.tokenize(text)

#             for token in tokens:
#                 print(token)

#             # 2. Parsing: Analyze structure and execute
#             # parser.parse(tokens)


import sys
import argparse
from engine.lexer import QuantelLexer
# from gui.ide_window import QuantelIDE

def run_cli():
    parser = argparse.ArgumentParser(description="Quantel CLI Mode")
    
    # Path to the .qtl file
    parser.add_argument("file", nargs="?", help="Path to the .qtl file")
    
    # Input string directly
    parser.add_argument("-s", "--string", help="Input string directly")

    args = parser.parse_args()
    lexer = QuantelLexer()

    # Case 1: Direct string input via terminal
    if args.string:
        print(f"--- Scanning String Input ---")
        for tok in lexer.tokenize(args.string):
            print(f"Type: {tok.type:12} | Value: {tok.value}")

    # Case 2: Reading from the sample file
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                code = f.read()
            print(f"--- Scanning File: {args.file} ---")
            for tok in lexer.tokenize(code):
                print(f"Type: {tok.type:12} | Value: {tok.value}")
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.")

    # Case 3: No input provided - GUI Switch
    else:
        print("--- No input provided. Launching GUI Mode ---")
        # app = QuantelIDE() # Commented out for now
        # app.mainloop()    # Commented out for now
        print("GUI logic is currently disabled in main.py")

if __name__ == "__main__":
    run_cli()