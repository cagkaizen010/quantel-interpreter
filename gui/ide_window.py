import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import io
import contextlib
import re

# --- Project GUI Components ---
from gui.editor_panel import EditorPanel
from gui.output_panel import OutputPanel
from gui.memory_map import MemoryMapPanel
from gui.tac_viewer import TACViewerPanel
from gui.utils import render_ast_tree

# --- Engine Imports ---
from engine.lexer import QuantelLexer

# Safe Import for Parser/Interpreter/Optimizer
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
        self.interpreter_instance = None

        # 2. Main Layout
        self.main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self.top_pane = tk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.add(self.top_pane, stretch="always", height=600)

        # 3. Initialize Components
        # Editor with Jump to Definition callback
        self.editor_panel = EditorPanel(self.top_pane, on_word_click=self.jump_to_definition)
        self.top_pane.add(self.editor_panel, stretch="always", width=900)

        self.side_container = ctk.CTkFrame(self.top_pane, corner_radius=0)
        self.top_pane.add(self.side_container, stretch="never", width=400)

        self.side_container.grid_columnconfigure(0, weight=1)
        self.side_container.grid_rowconfigure(0, weight=1)
        self.side_container.grid_rowconfigure(1, weight=1)

        self.memory_panel = MemoryMapPanel(self.side_container)
        self.memory_panel.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.tac_panel = TACViewerPanel(self.side_container)
        self.tac_panel.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        self.output_panel = OutputPanel(
            self.main_pane,
            on_line_click=self.highlight_editor_line
        )
        self.main_pane.add(self.output_panel, stretch="never", height=300)

        # 4. Menus & Bindings
        self._create_menu()
        self._bind_shortcuts()

        if file_path:
            self._open_specific_file(file_path)

    # -------------------------------------------------------------------------
    # BRIDGE METHODS
    # -------------------------------------------------------------------------

    def jump_to_definition(self, word):
        """Scans code for declarations or assignments of the given word."""
        if not word: return
        code = self.editor_panel.get_text()
        patterns = [rf"func\s+{word}\b", rf"var\s+{word}\b", rf"auto\s+{word}\b", rf"\b{word}\s*="]

        for p in patterns:
            match = re.search(p, code)
            if match:
                line_num = code.count('\n', 0, match.start()) + 1
                self.editor_panel.highlight_line(line_num)
                return

    def _open_search_bar(self):
        """Triggers the minimalist overlay in the EditorPanel."""
        self.editor_panel.show_search()

    def highlight_editor_line(self, line_number):
        """Called when a user clicks a row in the Lexer tab."""
        self.editor_panel.highlight_line(line_number)

    def _get_line_from_error(self, err):
        """Intelligently finds a line number in an error object or string."""
        for attr in ['lineno', 'line', 'row']:
            val = getattr(err, attr, None)
            if isinstance(val, int): return val

        match = re.search(r"line (\d+)", str(err), re.IGNORECASE)
        if match:
            return int(match.group(1))

        return 1

    # -------------------------------------------------------------------------
    # CORE LOGIC: THE COMPILER PIPELINE
    # -------------------------------------------------------------------------

    def run_quantel_code(self):
        self.output_panel.clear_all()
        self.editor_panel.clear_indicators()
        self.output_panel.select_tab("Output")

        code = self.editor_panel.get_text()

        try:
            # --- PHASE 1: LEXER ---
            lexer = QuantelLexer()
            tokens = list(lexer.tokenize(code))
            self.output_panel.update_lexer_tab(tokens)

            if lexer.errors:
                for err in lexer.errors:
                    line = self._get_line_from_error(err)
                    self.editor_panel.mark_error(line)
                self.output_panel.show_error("Lexer Errors", lexer.errors)
                return

            # --- PHASE 2: PARSER ---
            if not QuantelParser:
                self.output_panel.show_error("Config Error", ["Parser missing."])
                return

            parser = QuantelParser()
            ast_tree = parser.parse(iter(tokens))

            if parser.errors:
                for err in parser.errors:
                    line = self._get_line_from_error(err)
                    self.editor_panel.mark_error(line)
                self.output_panel.show_error("Parser Errors", parser.errors)
                return

            # --- PHASE 2.1: SEMANTIC ANALYSIS ---
            try:
                from engine.semantic_analyzer import SemanticAnalyzer, SemanticError
                analyzer = SemanticAnalyzer()
                analyzer.analyze(ast_tree)
                self.output_panel.update_symbols_tab(analyzer)
            except SemanticError as e:
                line = self._get_line_from_error(e)
                self.editor_panel.mark_error(line)
                self.output_panel.show_error("Semantic Error", [str(e)])
                return
            except Exception as e:
                self.output_panel.show_error("Analyzer Crash", [str(e)])
                return

            if ast_tree:
                # --- OPTIMIZER ---
                if QuantelOptimizer:
                    optimizer = QuantelOptimizer()
                    ast_tree = optimizer.optimize(ast_tree)
                    if optimizer.changed:
                        self.output_panel.write("Output", "[Optimizer] Code optimized.\n", False)

                # --- VISUALS ---
                self.output_panel.write("AST", render_ast_tree(ast_tree))

                # --- INTEGRATED TAC VIEWING ---
                self.tac_panel.generate_and_show(ast_tree)

                # --- INTERPRETER ---
                if QuantelInterpreter:
                    self.output_panel.write("Output", "--- Running Program ---\n", False)
                    self.interpreter_instance = QuantelInterpreter()
                    f = io.StringIO()
                    try:
                        with contextlib.redirect_stdout(f):
                            self.interpreter_instance.interpret(ast_tree)
                        self.output_panel.write("Output", f.getvalue() + "\n[Finished]", False)
                        self.memory_panel.update_map(self.interpreter_instance.global_env)
                    except Exception as e:
                        self.output_panel.show_error("Runtime Error", [str(e)])

        except Exception as e:
            self.output_panel.show_error("System Error", [str(e)])

    # -------------------------------------------------------------------------
    # UI HELPERS (Menus, Files, Toggles)
    # -------------------------------------------------------------------------

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        file_menu.add_command(label="New", command=self._new_file, accelerator="Cmd+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Cmd+O")
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Cmd+S")

        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Cmd+Q")

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Find", command=self._open_search_bar, accelerator="Cmd+F")

        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Program", command=self.run_quantel_code, accelerator="F5")

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Memory Map", command=self._toggle_memory)
        view_menu.add_command(label="Toggle White Box", command=self._toggle_tac)

    def _bind_shortcuts(self):

        ## To prevent the hotkeys from popping up during use.
        # self.bind_all("<Command-n>", lambda e: self._new_file())
        # self.bind_all("<Command-o>", lambda e: self._open_file())
        # self.bind_all("<Command-s>", lambda e: self._save_file())
        
        # self.bind_all("<Command-f>", lambda e: self._open_search_bar())
        self.bind_all("<Control-n>", lambda e: self._new_file())
        self.bind_all("<Control-o>", lambda e: self._open_file())
        self.bind_all("<Control-s>", lambda e: self._save_file())
        self.bind_all("<Control-f>", lambda e: self._open_search_bar())
        self.bind_all("<F5>", lambda e: self.run_quantel_code())

    def _new_file(self):
        self.editor_panel.set_text("")
        self.current_file = None
        self.title("Quantel IDE - Untitled")

    def _open_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Quantel Files", "*.qtl"), ("All Files", "*.*")])
        if filepath: self._open_specific_file(filepath)

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