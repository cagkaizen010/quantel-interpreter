import sys
import argparse
from engine.lexer import QuantelLexer
from gui.ide_window import QuantelIDE

def run_cli():
    parser = argparse.ArgumentParser(description="Quantel CLI Mode")
    
    # Path to the .qtl file
    parser.add_argument("file", nargs="?", help="Path to the .qtl file")
    
    # Input string directly
    parser.add_argument("-s", "--string", help="Input string directly")

    # Add new argument for GUI
    parser.add_argument("-g", "--gui", action="store_true", help="Launch Quantel IDE GUI")

    args = parser.parse_args()
    lexer = QuantelLexer()

    # Case 1: Launch GUI if -g or --gui is present
    if args.gui:
        print("--- Launching GUI Mode ---")
        app = QuantelIDE()
        app.mainloop()

    # Case 2: Direct string input via terminal
    elif args.string:
        print(f"--- Scanning String Input ---")
        for tok in lexer.tokenize(args.string):
            print(f"Token Type: {tok.type}, Value: {tok.value}, Line: {tok.lineno}")

    # Case 3: Reading from the sample file
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                code = f.read()
            print(f"--- Scanning File: {args.file} ---")
            for tok in lexer.tokenize(code):
                print(f"Token Type: {tok.type}, Value: {tok.value}, Line: {tok.lineno}")
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.")

    # Case 4: No input or --gui provided - show help or a message
    else:
        parser.print_help()
        print("\nNote: To launch the GUI, use 'python main.py --gui'")

if __name__ == "__main__":
    run_cli()