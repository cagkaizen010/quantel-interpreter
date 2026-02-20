import sys
import argparse
import json
import os

# --- Core Engine Imports ---
from engine.lexer import QuantelLexer
from engine.parser import QuantelParser
import engine.ast as ast

# NEW: Import the modules
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


def run_cli():
    parser = argparse.ArgumentParser(description="Quantel Language Tool (CLI)")

    # Arguments
    parser.add_argument("file", nargs="?", help="Path to the .qtl file")
    parser.add_argument("-s", "--string", help="Process a raw code string directly")
    parser.add_argument("-g", "--gui", action="store_true", help="Launch the Quantel IDE")
    parser.add_argument("-p", "--parse", action="store_true", help="Parse and print AST (JSON)")
    parser.add_argument("-l", "--lex", action="store_true", help="Tokenize and print tokens")
    parser.add_argument("--lex-out", action="store_true", help="Output lexed tokens to output.txt")
    parser.add_argument("-t", "--tac", action="store_true", help="Show Optimized Three-Address Code")

    args = parser.parse_args()

    # --- Launch GUI Mode ---
    if args.gui:
        if GUI_AVAILABLE:
            app = QuantelIDE(file_path=args.file if args.file else "samples/base.qtl")
            app.mainloop()
        else:
            print(f"Error: Could not launch GUI.\nDetails: {GUI_ERROR}")
        return

    # --- Input Preparation ---
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
        parser.print_help()
        return

    # =========================================================================
    #  COMPILATION PIPELINE
    # =========================================================================

    # --- 1. LEXING ---
    lexer = QuantelLexer(print_errors=args.lex_out)
    # We convert tokens to a list so we can check for errors before passing to parser
    tokens = list(lexer.tokenize(code_input))
    lexer_errors = lexer.get_errors() if hasattr(lexer, 'get_errors') else []

    if args.lex:
        for tok in tokens: print(tok)
        return

    if args.lex_out:
        os.makedirs("samples", exist_ok=True)
        with open("samples/output.txt", "w") as f:
            for tok in tokens: f.write(f"{tok}\n")
            # If you want errors in the file but NOT the console:
            if lexer_errors:
                f.write("\n--- LEXER ERRORS ---\n")
                for err in lexer_errors:
                    f.write(f"{err}\n")
                    
        print(f"Tokens written to samples/output.txt")
        return

    # --- 2. PARSING ---
    print(f"\n--- Processing: {source_name} ---")
    quantel_parser = QuantelParser()
    tree = quantel_parser.parse(iter(tokens))
    parser_errors = quantel_parser.errors

    # --- 3. SEMANTIC ANALYSIS ---
    semantic_errors = []
    if tree:
        analyzer = SemanticAnalyzer()
        # Ensure analyze() is calling the visit methods correctly
        semantic_errors = analyzer.analyze(tree)

    # =========================================================================
    #  GLOBAL ERROR SUMMARY
    # =========================================================================
    total_errors = len(lexer_errors) + len(parser_errors) + len(semantic_errors)

    if total_errors > 0:
        print("\n" + "!" * 60)
        print(f" COMPILATION FAILED: {total_errors} Total Errors Found")
        print("!" * 60)

        if lexer_errors:
            print(f"\n[ Lexer Errors: {len(lexer_errors)} ]")
            for err in lexer_errors: print(f"  -> {err}")

        if parser_errors:
            print(f"\n[ Parser Errors: {len(parser_errors)} ]")
            for err in parser_errors: print(f"  -> {err}")

        if semantic_errors:
            print(f"\n[ Semantic Errors: {len(semantic_errors)} ]")
            for err in semantic_errors: print(f"  -> {err}")

        print("\n" + "!" * 60)
        print("Execution halted due to errors.")
        sys.exit(1)

    # =========================================================================
    #  BACK-END (Optimization & Execution)
    # =========================================================================

    print("--- Analysis Successful (0 Errors) ---")

    # --- 4. OPTIMIZATION ---
    print("\n--- Optimizing AST ---")
    optimizer = QuantelOptimizer()
    optimized_tree = optimizer.optimize(tree)

    # --- 5. TAC GENERATION ---
    if args.tac:
        print("\n--- Three-Address Code (Optimized) ---")
        tac_gen = TACGenerator()
        print(tac_gen.generate(optimized_tree))

    # --- 6. EXECUTION ---
    print("\n--- Executing Program ---")
    interpreter = QuantelInterpreter()
    try:
        interpreter.interpret(optimized_tree)
        print("\n[Program Finished Successfully]")
    except Exception as e:
        print(f"\nRuntime Error: {e}")


if __name__ == "__main__":
    run_cli()