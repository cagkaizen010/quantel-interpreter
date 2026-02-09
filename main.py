import sys
import argparse
import json
import os

# --- Core Engine Imports ---
from engine.lexer import QuantelLexer
from engine.parser import QuantelParser
import engine.ast as ast
# NEW: Import the interpreter so we can run the code
from engine.interpreter import QuantelInterpreter

# --- GUI Import ---
try:
    from gui.ide_window import QuantelIDE

    GUI_AVAILABLE = True
    GUI_ERROR = None
except ImportError as e:
    GUI_AVAILABLE = False
    GUI_ERROR = str(e)


def ast_to_dict(node):
    """
    Recursively converts AST nodes to a dictionary for JSON printing.
    """
    if node is None: return None
    if isinstance(node, list): return [ast_to_dict(n) for n in node]
    if isinstance(node, (str, int, float, bool)): return node
    if isinstance(node, ast.Node):
        node_dict = {"node_type": node.__class__.__name__}
        if hasattr(node, '__dict__'):
            for key, value in vars(node).items():
                if key.startswith("_") or key == "lineno": continue
                node_dict[key] = ast_to_dict(value)
        return node_dict
    return str(node)


def run_cli():
    parser = argparse.ArgumentParser(description="Quantel Language Tool (CLI)")

    # Arguments
    parser.add_argument("file", nargs="?", help="Path to the .qtl file")
    parser.add_argument("-s", "--string", help="Process a raw code string directly")
    parser.add_argument("-g", "--gui", action="store_true", help="Launch the Quantel IDE")
    parser.add_argument("-p", "--parse", action="store_true", help="Parse and print AST (JSON)")
    parser.add_argument("-l", "--lex", action="store_true", help="Tokenize and print tokens (Debug)")

    args = parser.parse_args()

    # --- MODE 1: Launch GUI ---
    if args.gui:
        if GUI_AVAILABLE:
            print("--- Launching Quantel IDE ---")

            # 1. Determine target file (Default: base.qtl)
            target_file = args.file if args.file else "base.qtl"

            # 2. Create default file if missing
            if target_file == "base.qtl" and not os.path.exists(target_file):
                print(f"Creating default file: {target_file}")
                with open(target_file, "w") as f:
                    f.write("// Quantel Base File\nprint(\"Hello Quantel\");\n")

            # 3. Launch App
            try:
                app = QuantelIDE(file_path=target_file)
            except TypeError:
                print("Note: IDE does not accept file args. Opening empty.")
                app = QuantelIDE()

            app.mainloop()
        else:
            print(f"Error: Could not launch GUI.\nDetails: {GUI_ERROR}")
        return

    # --- Prepare Input ---
    code_input = ""
    source_name = "Input String"

    if args.string:
        code_input = args.string
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File '{args.file}' not found.")
            return
        source_name = args.file
        with open(args.file, 'r') as f:
            code_input = f.read()
    else:
        # If no args, try to run base.qtl by default in CLI mode too
        default_cli = "base.qtl"
        if os.path.exists(default_cli):
            source_name = default_cli
            with open(default_cli, 'r') as f:
                code_input = f.read()
            print(f"--- No args provided, running {default_cli} ---")
        else:
            parser.print_help()
            return

    # Initialize Lexer
    lexer = QuantelLexer()

    # --- MODE 2: Lexing Only ---
    if args.lex:
        print(f"--- Scanning: {source_name} ---")
        tokens = lexer.tokenize(code_input)
        for tok in tokens:
            print(f"Token: {tok.type:<15} Value: {str(tok.value):<20} Line: {tok.lineno}")
        if lexer.errors:
            print("\n!!! Lexer Errors !!!")
            for err in lexer.errors: print(err)
        return

    # --- MODE 3: Parsing & Execution ---
    print(f"--- Parsing: {source_name} ---")
    quantel_parser = QuantelParser()
    tree = quantel_parser.parse(lexer.tokenize(code_input))

    if lexer.errors:
        print("\n!!! Parsing Aborted: Lexer Errors Found !!!")
        for err in lexer.errors: print(f" - {err}")
        return

    if quantel_parser.errors:
        print("\n!!! Parser Errors Found !!!")
        for err in quantel_parser.errors: print(f" - {err}")
        return

    if tree:
        # Print AST only if requested
        if args.parse:
            print("\n--- AST ---")
            print(json.dumps(ast_to_dict(tree), indent=2))

        # --- INTERPRETER EXECUTION ---
        print("\n--- Executing Program ---")
        interpreter = QuantelInterpreter()
        try:
            interpreter.interpret(tree)
            print("\n[Program Finished Successfully]")
        except Exception as e:
            print(f"\nruntime error: {e}")
    else:
        print("\nError: Parser returned None.")


if __name__ == "__main__":
    run_cli()