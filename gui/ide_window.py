import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import io
import os
import contextlib
import re
import sys
import threading
from CTkToolTip import CTkToolTip

# --- Project GUI Components ---
from gui.editor_panel import EditorPanel
from gui.output_panel import OutputPanel
from gui.memory_map import StackMapPanel, HeapMapPanel
from gui.tac_viewer import TACViewerPanel
from gui.file_explorer import FileExplorerPanel
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
        self.interpreter_instance = None
        self.execution_thread = None

        # 2. Toolbar
        self.toolbar = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color="#333333")
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Icon-based buttons packed to the right
        self.step_btn = ctk.CTkButton(self.toolbar, text="⤵", width=30, height=24, 
                                      text_color="white",
                                      fg_color="#444444", hover_color="#555555",
                                      state="disabled", command=self.step_program)
        self.step_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        self.step_tooltip = CTkToolTip(self.step_btn, message="Step Forward")

        self.step_back_btn = ctk.CTkButton(self.toolbar, text="↶", width=30, height=24, 
                                           text_color="white",
                                           fg_color="#444444", hover_color="#555555",
                                           state="disabled", command=self.step_back_program)
        self.step_back_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        self.step_back_tooltip = CTkToolTip(self.step_back_btn, message="Step Backward")

        self.debug_btn = ctk.CTkButton(self.toolbar, text="🪲", width=30, height=24, 
                                       text_color="white",
                                       fg_color="#444444", hover_color="#555555",
                                       command=self.debug_quantel_code)
        self.debug_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        self.debug_tooltip = CTkToolTip(self.debug_btn, message="Debug Program")

        self.run_btn = ctk.CTkButton(self.toolbar, text="▶", width=30, height=24, 
                                     text_color="white",
                                     fg_color="#444444", hover_color="#555555", 
                                     command=self.run_quantel_code)
        self.run_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        self.run_tooltip = CTkToolTip(self.run_btn, message="Run Program")

        # Optimizer Toggle
        self.opt_var = tk.BooleanVar(value=True)
        self.opt_toggle = ctk.CTkCheckBox(self.toolbar, text="Optimize", 
                                          variable=self.opt_var,
                                          font=("Segoe UI", 12),
                                          checkbox_width=18, checkbox_height=18,
                                          fg_color="#1f538d", hover_color="#2b2b2b")
        self.opt_toggle.pack(side=tk.RIGHT, padx=15, pady=5)
        self.opt_tooltip = CTkToolTip(self.opt_toggle, message="Toggle AST Optimization")

        # 3. Main Layout
        self.main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # TOP AREA (Explorer | Editor | Memory)
        self.top_pane = tk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.add(self.top_pane, stretch="always", height=600)

        # Left Explorer
        self.explorer_panel = FileExplorerPanel(self.top_pane, on_file_select=self._open_specific_file)
        self.top_pane.add(self.explorer_panel, stretch="never", width=250)

        # Center Editor
        self.editor_panel = EditorPanel(self.top_pane, on_word_click=self.jump_to_definition)
        self.top_pane.add(self.editor_panel, stretch="always", width=750)

        # Right Memory Side
        self.side_container = ctk.CTkFrame(self.top_pane, corner_radius=0)
        self.top_pane.add(self.side_container, stretch="never", width=400)
        self.side_container.grid_columnconfigure(0, weight=1)
        self.side_container.grid_rowconfigure(0, weight=1) # Stack
        self.side_container.grid_rowconfigure(1, weight=1) # Heap

        self.stack_panel = StackMapPanel(self.side_container)
        self.stack_panel.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.heap_panel = HeapMapPanel(self.side_container)
        self.heap_panel.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        # BOTTOM AREA (Output | TAC)
        self.bottom_pane = tk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.add(self.bottom_pane, stretch="never", height=300)

        self.output_panel = OutputPanel(self.bottom_pane, on_line_click=self.highlight_editor_line)
        self.bottom_pane.add(self.output_panel, stretch="always", width=800)

        self.tac_panel = TACViewerPanel(self.bottom_pane)
        self.bottom_pane.add(self.tac_panel, stretch="always", width=600)

        # 4. Menus & Bindings
        self._create_menu()
        self._bind_shortcuts()

        if file_path:
            self._open_specific_file(file_path)

    # -------------------------------------------------------------------------
    # BRIDGE METHODS
    # -------------------------------------------------------------------------

    def jump_to_definition(self, word):
        if not word: return
        code = self.editor_panel.get_text()
        patterns = [rf"func\s+{word}\b", rf"var\s+{word}\b", rf"auto\s+{word}\b", rf"\b{word}\s*="]
        for p in patterns:
            match = re.search(p, code)
            if match:
                line_num = code.count('\n', 0, match.start()) + 1
                self.editor_panel.highlight_line(line_num)
                return

    def _open_search_bar(self): self.editor_panel.show_search()
    def highlight_editor_line(self, line_number): self.editor_panel.highlight_line(line_number)

    def _get_line_from_error(self, err):
        for attr in ['lineno', 'line', 'row']:
            val = getattr(err, attr, None)
            if isinstance(val, int): return val
        err_str = str(err)
        match = re.search(r"line\s+(\d+)", err_str, re.IGNORECASE)
        return int(match.group(1)) if match else None

    # -------------------------------------------------------------------------
    # CORE LOGIC: THE COMPILER PIPELINE
    # -------------------------------------------------------------------------

    def run_quantel_code(self, debug_mode=False):
        self.output_panel.clear_all()
        self.editor_panel.clear_indicators()
        self.output_panel.select_tab("Output")

        self.run_btn.configure(state="disabled")
        self.debug_btn.configure(state="disabled")
        
        if debug_mode:
            self.debug_btn.configure(fg_color="#28a745")
            self.step_btn.configure(state="normal", fg_color="#1f538d")
            self.step_back_btn.configure(state="normal", fg_color="#1f538d")
        else:
            self.run_btn.configure(fg_color="#28a745")
            self.step_btn.configure(state="disabled", fg_color="#444444")
            self.step_back_btn.configure(state="disabled", fg_color="#444444")

        code = self.editor_panel.get_text()

        def execution_task():
            try:
                lexer = QuantelLexer()
                tokens = list(lexer.tokenize(code))
                self.after(0, lambda: self.output_panel.update_lexer_tab(tokens))

                if lexer.errors:
                    for err in lexer.errors:
                        line = self._get_line_from_error(err)
                        self.after(0, lambda l=line: self.editor_panel.mark_error(l))
                    self.after(0, lambda: self.output_panel.show_error("Lexer Errors", lexer.errors))
                    return

                if not QuantelParser:
                    self.after(0, lambda: self.output_panel.show_error("Config Error", ["Parser missing."]))
                    return

                parser = QuantelParser()
                ast_tree = parser.parse(iter(tokens), source_text=code)

                if parser.errors:
                    for err in parser.errors:
                        line = self._get_line_from_error(err)
                        self.after(0, lambda l=line: self.editor_panel.mark_error(l))
                    self.after(0, lambda: self.output_panel.show_error("Parser Errors", parser.errors))
                    return

                from engine.semantic_analyzer import SemanticAnalyzer
                analyzer = SemanticAnalyzer()
                analyzer.analyze(ast_tree)
                semantic_errors = analyzer.errors

                if semantic_errors:
                    self.after(0, lambda: self.output_panel.show_error("Semantic Errors", semantic_errors))
                    return
                else:
                    self.after(0, lambda: self.output_panel.update_symbols_tab(analyzer))

                if ast_tree:
                    should_optimize = self.opt_var.get()
                    if QuantelOptimizer and should_optimize:
                        optimizer = QuantelOptimizer()
                        ast_tree = optimizer.optimize(ast_tree)
                    
                    self.after(0, lambda: self.output_panel.write("AST", render_ast_tree(ast_tree)))
                    self.after(0, lambda: self.tac_panel.generate_and_show(ast_tree))

                    if QuantelInterpreter:
                        self.after(0, lambda: self.output_panel.write("Output", "--- Running Program ---\n", False))
                        
                        def live_update_cb(interpreter):
                            self.after(0, lambda: self.stack_panel.update_map(interpreter))
                            self.after(0, lambda: self.heap_panel.update_map(interpreter))
                            
                            if interpreter.current_node:
                                node = interpreter.current_node
                                self.after(0, lambda n=node: self.tac_panel.highlight_instruction(n))
                                line = getattr(node, 'lineno', None)
                                if line: self.after(0, lambda l=line: self.editor_panel.highlight_line(l))

                        self.interpreter_instance = QuantelInterpreter(step_callback=live_update_cb)
                        if debug_mode: self.interpreter_instance.step_mode = True

                        class GUIStream:
                            def __init__(self, panel, original):
                                self.panel = panel
                                self.original = original
                            def write(self, s):
                                self.original.write(s)
                                self.panel.after(0, lambda: self.panel.write("Output", s, False))
                            def flush(self): self.original.flush()
                            def readline(self): return self.panel.get_input() + "\n"

                        original_stdout, original_stdin = sys.stdout, sys.stdin
                        try:
                            stream = GUIStream(self.output_panel, original_stdout)
                            sys.stdout = stream
                            sys.stdin = stream
                            self.interpreter_instance.interpret(ast_tree)
                            self.after(0, lambda: self.output_panel.write("Output", "\n[Finished]", False))
                            self.after(0, lambda: self.stack_panel.update_map(self.interpreter_instance))
                            self.after(0, lambda: self.heap_panel.update_map(self.interpreter_instance))
                        except Exception as e:
                            self.after(0, lambda e_msg=str(e): self.output_panel.write("Output", f"\n[Runtime Error] {e_msg}\n", False, tag="red"))
                        finally:
                            sys.stdout, sys.stdin = original_stdout, original_stdin
            except Exception as e:
                self.after(0, lambda e_msg=str(e): self.output_panel.show_error("System Error", [e_msg]))
            finally:
                # RE-ENABLE BUTTONS ALWAYS
                self.after(0, lambda: self.run_btn.configure(state="normal", fg_color="#444444"))
                self.after(0, lambda: self.debug_btn.configure(state="normal", fg_color="#444444"))
                self.after(0, lambda: self.step_btn.configure(state="disabled", fg_color="#444444"))
                self.after(0, lambda: self.step_back_btn.configure(state="disabled", fg_color="#444444"))
                self.after(0, lambda: self.editor_panel.clear_indicators())

        self.execution_thread = threading.Thread(target=execution_task, daemon=True)
        self.execution_thread.start()

    def debug_quantel_code(self): self.run_quantel_code(debug_mode=True)
    def step_program(self):
        if self.interpreter_instance: self.interpreter_instance.step_event.set()

    def step_back_program(self):
        if self.interpreter_instance:
            if self.interpreter_instance.step_back():
                self.stack_panel.update_map(self.interpreter_instance)
                self.heap_panel.update_map(self.interpreter_instance)
                node = self.interpreter_instance.current_node
                if node:
                    self.tac_panel.highlight_instruction(node)
                    line = getattr(node, 'lineno', None)
                    if line: self.editor_panel.highlight_line(line)
                self.interpreter_instance.step_event.set()

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self._new_file, accelerator="Cmd+N")
        file_menu.add_command(label="Open File...", command=self._open_file, accelerator="Cmd+O")
        file_menu.add_command(label="Open Folder...", command=self._open_folder)
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Cmd+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Cmd+Q")

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Find", command=self._open_search_bar, accelerator="Cmd+F")

    def _bind_shortcuts(self):
        self.bind_all("<Control-n>", lambda e: self._new_file())
        self.bind_all("<Control-o>", lambda e: self._open_file())
        self.bind_all("<Control-s>", lambda e: self._save_file())
        self.bind_all("<Control-f>", lambda e: self._open_search_bar())
        self.bind_all("<Control-slash>", lambda e: self.editor_panel.toggle_comment())
        self.bind_all("<Command-slash>", lambda e: self.editor_panel.toggle_comment())
        self.bind_all("<F5>", lambda e: self.run_quantel_code())

    def _new_file(self):
        self.editor_panel.set_text("")
        self.current_file = None
        self.title("Quantel IDE - Untitled")

    def _open_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Quantel Files", "*.qtl"), ("All Files", "*.*")])
        if filepath: self._open_specific_file(filepath)

    def _open_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path: self.explorer_panel.set_project_root(folder_path)

    def _open_specific_file(self, filepath):
        try:
            with open(filepath, "r") as f: content = f.read()
            self.editor_panel.set_text(content)
            self.current_file = filepath
            self.title(f"Quantel IDE - {os.path.basename(filepath)}")
        except Exception as e: messagebox.showerror("Open File", str(e))

    def _save_file(self):
        if not self.current_file:
            self.current_file = filedialog.asksaveasfilename(defaultextension=".qtl")
        if self.current_file:
            try:
                with open(self.current_file, "w") as f: f.write(self.editor_panel.get_text())
                self.explorer_panel.refresh_tree()
            except Exception as e: messagebox.showerror("Save File", str(e))
