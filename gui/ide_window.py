import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import io
import contextlib

# --- Project GUI Components ---
from gui.editor_panel import EditorPanel
from gui.output_panel import OutputPanel
from gui.memory_map import MemoryMapPanel
from gui.tac_viewer import TACViewerPanel
from gui.utils import render_ast_tree

# --- Engine Imports ---
from engine.lexer import QuantelLexer

# Safe Import for Parser/Interpreter/Optimizer
# (Prevents crash if files are still being written)
try:
    from engine.parser import QuantelParser
    from engine.interpreter import QuantelInterpreter
    from engine.optimizer import QuantelOptimizer
except ImportError:
    QuantelParser = None
    QuantelInterpreter = None
    QuantelOptimizer = None


class QuantelIDE(ctk.CTk):
    def __init__(self, file_path=None):
        super().__init__()

        # 1. Window Setup
        self.title("Quantel IDE")
        self.geometry("1400x900")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # State
        self.current_file = None
        self.show_memory = True
        self.show_tac = True
        self.interpreter_instance = None  # Keep reference for memory inspection

        # 2. Main Layout

        # Vertical Split: Top (Editor+Tools) / Bottom (Output)
        self.main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Horizontal Split: Left (Editor) / Right (Tools)
        self.top_pane = tk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.add(self.top_pane, stretch="always", height=600)

        # 3. Initialize Components

        # --- Left: Code Editor ---
        self.editor_panel = EditorPanel(self.top_pane)
        self.top_pane.add(self.editor_panel, stretch="always", width=900)

        # --- Right: Side Tools Container ---
        self.side_container = ctk.CTkFrame(self.top_pane, corner_radius=0)
        self.top_pane.add(self.side_container, stretch="never", width=400)

        # Grid layout for the side container
        self.side_container.grid_columnconfigure(0, weight=1)
        self.side_container.grid_rowconfigure(0, weight=1)  # Memory Map row
        self.side_container.grid_rowconfigure(1, weight=1)  # TAC Viewer row

        # Right Top: Memory Map
        self.memory_panel = MemoryMapPanel(self.side_container)
        self.memory_panel.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Right Bottom: TAC Viewer (White Box)
        self.tac_panel = TACViewerPanel(self.side_container)
        self.tac_panel.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        # --- Bottom: Output Panel ---
        self.output_panel = OutputPanel(self.main_pane)
        self.main_pane.add(self.output_panel, stretch="never", height=300)

        # 4. Menus & Bindings
        self._create_menu()
        self._bind_shortcuts()

        # 5. Open File (if argument provided)
        if file_path:
            self._open_specific_file(file_path)

    # -------------------------------------------------------------------------
    # UI SETUP HELPERS
    # -------------------------------------------------------------------------

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self._new_file, accelerator="Cmd+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Cmd+O")
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Cmd+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Cmd+Q")

        # Run Menu
        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Program", command=self.run_quantel_code, accelerator="F5")

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Memory Map", command=self._toggle_memory)
        view_menu.add_command(label="Toggle White Box", command=self._toggle_tac)

    def _bind_shortcuts(self):
        self.bind_all("<Command-n>", lambda e: self._new_file())
        self.bind_all("<Command-o>", lambda e: self._open_file())
        self.bind_all("<Command-s>", lambda e: self._save_file())
        self.bind_all("<F5>", lambda e: self.run_quantel_code())

    # -------------------------------------------------------------------------
    # CORE LOGIC: THE COMPILER PIPELINE
    # -------------------------------------------------------------------------

    def run_quantel_code(self):
        # 1. Reset UI
        self.output_panel.clear_all()
        self.output_panel.select_tab("Output")

        # 2. Get Source Code
        code = self.editor_panel.get_text()

        try:
            # --- PHASE 1: LEXER ---
            lexer = QuantelLexer()
            tokens = list(lexer.tokenize(code))

            # Let the OutputPanel handle the table formatting
            self.output_panel.update_lexer_tab(tokens)

            if lexer.errors:
                self.output_panel.show_error("Lexer Errors", lexer.errors)
                return

            # --- PHASE 2: PARSER ---
            if not QuantelParser:
                self.output_panel.show_error("Configuration Error", ["Parser module missing."])
                return

            parser = QuantelParser()
            ast_tree = parser.parse(iter(tokens))

            if parser.errors:
                self.output_panel.show_error("Parser Errors", parser.errors)
                return

            # --- PHASE 2.1: SEMANTIC ANALYSIS ---
            try:
                from engine.semantic_analyzer import SemanticAnalyzer, SemanticError
                analyzer = SemanticAnalyzer()
                analyzer.analyze(ast_tree)

                # Update the GUI Symbols Tab
                symbol_data = analyzer.get_symbol_table_text()
                self.output_panel.write("Symbols", symbol_data)
            except SemanticError as e:
                self.output_panel.show_error("Semantic Error", [str(e)])
                return
            except Exception as e:
                self.output_panel.show_error("Analyzer Crash", [str(e)])
                return

            if ast_tree:
                # --- PHASE 2.5: OPTIMIZER ---
                if QuantelOptimizer:
                    optimizer = QuantelOptimizer()
                    optimized_ast = optimizer.optimize(ast_tree)

                    if optimizer.changed:
                        self.output_panel.write("Output",
                                                "[Optimizer] Code optimized (Constant Propagation / Folding).\n",
                                                clear_first=False)
                    ast_tree = optimized_ast

                # --- VISUALIZATION ---
                self.output_panel.write("AST", render_ast_tree(ast_tree))
                self.tac_panel.generate_and_show(ast_tree)

                # --- PHASE 3: INTERPRETER ---
                if QuantelInterpreter:
                    self.output_panel.write("Output", "--- Running Program ---\n", clear_first=False)
                    self.interpreter_instance = QuantelInterpreter()

                    f = io.StringIO()
                    try:
                        with contextlib.redirect_stdout(f):
                            self.interpreter_instance.interpret(ast_tree)

                        result_output = f.getvalue()
                        self.output_panel.write("Output", result_output + "\n[Finished]", clear_first=False)
                        self.memory_panel.update_map(self.interpreter_instance.global_env)

                    except Exception as e:
                        self.output_panel.show_error("Runtime Error", [str(e)])
                else:
                    self.output_panel.write("Errors", "Interpreter module missing.")
            else:
                self.output_panel.write("Errors", "Parser returned None.")

        except Exception as e:
            self.output_panel.show_error("System Critical Error", [str(e)])
            import traceback
            traceback.print_exc()

    # -------------------------------------------------------------------------
    # FILE OPERATIONS
    # -------------------------------------------------------------------------

    def _new_file(self):
        self.editor_panel.set_text("")
        self.current_file = None
        self.title("Quantel IDE - Untitled")

    def _open_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Quantel Files", "*.qtl"), ("All Files", "*.*")])
        if filepath:
            self._open_specific_file(filepath)

    def _open_specific_file(self, filepath):
        try:
            with open(filepath, "r") as f:
                content = f.read()
            self.editor_panel.set_text(content)
            self.current_file = filepath
            self.title(f"Quantel IDE - {filepath}")
        except Exception as e:
            self.output_panel.show_error("File Error", [f"Could not open file: {e}"])

    def _save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, "w") as f:
                    f.write(self.editor_panel.get_text())
            except Exception as e:
                self.output_panel.show_error("File Error", [f"Could not save file: {e}"])
        else:
            self._save_file_as()

    def _save_file_as(self):
        filepath = filedialog.asksaveasfilename(filetypes=[("Quantel Files", "*.qtl"), ("All Files", "*.*")])
        if filepath:
            try:
                with open(filepath, "w") as f:
                    f.write(self.editor_panel.get_text())
                self.current_file = filepath
                self.title(f"Quantel IDE - {filepath}")
            except Exception as e:
                self.output_panel.show_error("File Error", [f"Could not save file: {e}"])

    # -------------------------------------------------------------------------
    # VIEW TOGGLES
    # -------------------------------------------------------------------------

    def _toggle_memory(self):
        if self.show_memory:
            self.memory_panel.grid_forget()
        else:
            self.memory_panel.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.show_memory = not self.show_memory

    def _toggle_tac(self):
        if self.show_tac:
            self.tac_panel.grid_forget()
        else:
            self.tac_panel.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.show_tac = not self.show_tac


if __name__ == "__main__":
    app = QuantelIDE()
    app.mainloop()