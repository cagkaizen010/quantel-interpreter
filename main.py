import sys
import argparse
import json
import os

# --- Core Engine Imports ---
from engine.lexer import QuantelLexer
from engine.parser import QuantelParser
import engine.ast as ast

# NEW: Import the new modules you've built
from engine.semantic_analyzer import SemanticAnalyzer
from engine.optimizer import QuantelOptimizer
from engine.tac_generator import TACGenerator
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
    """Recursively converts AST nodes to a dictionary for JSON printing."""
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
    parser.add_argument("-l", "--lex", action="store_true", help="Tokenize and print tokens")
    parser.add_argument("--lex-out", action="store_true", help="Output lexed tokens to the specified .txt file")
    parser.add_argument("-t", "--tac", action="store_true", help="Show Optimized Three-Address Code")

    args = parser.parse_args()

    # --- MODE 1: Launch GUI ---
    if args.gui:
        if GUI_AVAILABLE:
            print("--- Launching Quantel IDE ---")
            target_file = args.file if args.file else "samples/base.qtl"
            if target_file == "samples/base.qtl" and not os.path.exists(target_file):
                os.makedirs("samples", exist_ok=True)
                with open(target_file, "w") as f:
                    f.write("// Quantel Base File\nvar x: int32 = 10 + 20;\nprobe x;\n")
            app = QuantelIDE(file_path=target_file)
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
        default_cli = "samples/base.qtl"
        if os.path.exists(default_cli):
            source_name = default_cli
            with open(default_cli, 'r') as f:
                code_input = f.read()
        else:
            parser.print_help()
            return

    # --- 1. LEXING ---
    lexer = QuantelLexer()
    tokens = lexer.tokenize(code_input)

    if args.lex:
        for tok in tokens: print(tok)
        return
    
    if args.lex_out:
        # Create directory if it doesn't exist
        os.makedirs("samples", exist_ok=True)
        
        with open("samples/output.txt", "w") as f:
            for tok in tokens:
                f.write(f"{tok}\n")

            errors = lexer.get_errors()
            if errors:
                for msg in errors:
                    f.write(f"{msg}\n")
        return
    # --- 2. PARSING ---
    print(f"--- Processing: {source_name} ---")
    quantel_parser = QuantelParser()
    tree = quantel_parser.parse(tokens)

    if quantel_parser.errors or not tree:
        print("\n!!! Parser Errors Found !!!")
        for err in quantel_parser.errors: print(f" - {err}")
        return

    # --- 3. SEMANTIC ANALYSIS ---
    # We do this before optimization to ensure the original code is valid
    print("\n--- Semantic Analysis ---")
    analyzer = SemanticAnalyzer()
    semantic_errors = analyzer.analyze(tree)

    if semantic_errors:
        print("\n!!! Semantic Errors Found !!!")
        for err in semantic_errors: print(f" - {err}")
        return

    # --- 4. OPTIMIZATION ---
    print("\n--- Optimizing AST ---")
    optimizer = QuantelOptimizer()
    optimized_tree = optimizer.optimize(tree)

    # --- 5. TAC GENERATION ---
    if args.tac:
        print("\n--- Three-Address Code (Optimized) ---")
        tac_gen = TACGenerator()
        print(tac_gen.generate(optimized_tree))

    # --- 6. EXECUTION (Interpreter) ---
    print("\n--- Executing Program ---")
    interpreter = QuantelInterpreter()
    try:
        # We run the optimized tree for better performance
        interpreter.interpret(optimized_tree)
        print("\n[Program Finished Successfully]")
    except Exception as e:
        print(f"\nRuntime Error: {e}")


if __name__ == "__main__":
    run_cli()