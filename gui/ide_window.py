import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, ttk
import json
import io
import contextlib

# 3rd Party UI Libs
from chlorophyll import CodeView
from pygments.styles import get_style_by_name

# Project Imports
from gui.highlighter import QuantelHighlighter
from engine.lexer import QuantelLexer

# Try importing Parser and Interpreter safely
try:
    from engine.parser import QuantelParser
    from engine.interpreter import QuantelInterpreter
except ImportError:
    QuantelParser = None
    QuantelInterpreter = None


# --- AST VISUALIZER HELPER ---
def render_ast_tree(node, prefix="", is_last=True):
    """
    Recursively converts a Python object (AST) into a pretty ASCII tree string.
    """
    lines = []
    connector = "└── " if is_last else "├── "

    if isinstance(node, (str, int, float, bool, type(None))):
        return f"{prefix}{connector}{repr(node)}"

    if isinstance(node, list):
        if not node:
            return f"{prefix}{connector}[] (empty)"
        lines.append(f"{prefix}{connector}[]")
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, item in enumerate(node):
            lines.append(render_ast_tree(item, new_prefix, i == len(node) - 1))
        return "\n".join(lines)

    node_name = node.__class__.__name__
    lines.append(f"{prefix}{connector}{node_name}")
    new_prefix = prefix + ("    " if is_last else "│   ")

    if hasattr(node, "__dict__"):
        attrs = {k: v for k, v in node.__dict__.items() if not k.startswith('_')}
        attr_names = sorted(attrs.keys())
        for i, key in enumerate(attr_names):
            val = attrs[key]
            lines.append(render_ast_tree(val, new_prefix + ("└── " if i == len(attr_names) - 1 else "├── "),
                                         i == len(attr_names) - 1))

    return "\n".join(lines)


class QuantelIDE(ctk.CTk):
    def __init__(self, file_path=None):
        super().__init__()

        self.title("Quantel IDE")
        self.geometry("1400x900")

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- Compiler Components ---
        self.quantel_lexer = QuantelLexer()
        self.quantel_parser = QuantelParser() if QuantelParser else None
        self.interpreter_instance = None  # Store interpreter state

        self.current_file = None
        self.memory_map_visible = True
        self.white_box_viewer_visible = True

        # --- UI Construction ---
        self.create_menu_bar()
        self.bind_shortcuts()

        # --- RESIZABLE LAYOUT SETUP (PanedWindows) ---

        # 1. Main Vertical Splitter (Separates Top Editor from Bottom Output)
        self.main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # 2. Top Horizontal Splitter (Separates Editor from Side Panel)
        self.top_pane = tk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL, bg="#2b2b2b", bd=0, sashwidth=6)
        self.main_pane.add(self.top_pane, stretch="always", height=600)  # Give top part initial height

        # --- Left Side: Code Editor Container ---
        self.editor_frame = ctk.CTkFrame(self.top_pane, corner_radius=0)
        self.top_pane.add(self.editor_frame, stretch="always", width=900)

        self.editor_frame.grid_rowconfigure(0, weight=1)
        self.editor_frame.grid_columnconfigure(0, weight=1)
        self.create_code_editor(self.editor_frame)

        # --- Right Side: Tools Container ---
        self.side_panel_frame = ctk.CTkFrame(self.top_pane, corner_radius=0)
        self.top_pane.add(self.side_panel_frame, stretch="never", width=400)

        self.side_panel_frame.grid_columnconfigure(0, weight=1)
        self.side_panel_frame.grid_rowconfigure(0, weight=1)
        self.side_panel_frame.grid_rowconfigure(1, weight=1)
        self.create_side_panels(self.side_panel_frame)

        # --- Bottom Side: Output Tabs ---
        self.bottom_frame = ctk.CTkFrame(self.main_pane, corner_radius=0)
        self.main_pane.add(self.bottom_frame, stretch="never", height=300)

        self.bottom_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.create_tabbed_panel(self.bottom_frame)

        # Handle Auto-Open
        if file_path:
            self._open_specific_file(file_path)

    def create_menu_bar(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self._new_file, accelerator="Cmd+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Cmd+O")
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Cmd+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Cmd+Q")

        run_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Program", command=self.run_quantel_code, accelerator="F5")

        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Memory Map", command=self._toggle_memory_map)
        view_menu.add_command(label="Toggle White Box", command=self._toggle_white_box_viewer)

    def bind_shortcuts(self):
        self.bind_all("<Command-n>", lambda event: self._new_file())
        self.bind_all("<Command-o>", lambda event: self._open_file())
        self.bind_all("<Command-s>", lambda event: self._save_file())
        self.bind_all("<F5>", lambda event: self.run_quantel_code())

    def create_code_editor(self, parent_frame):
        # We wrap CodeView in a frame to ensure it expands correctly in the PanedWindow
        self.code_editor = CodeView(parent_frame, lexer=QuantelHighlighter, font=("Consolas", 14),
                                    color_scheme="monokai", undo=True)
        self.code_editor.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.code_editor.insert("1.0", "// Type your Quantel code here...\nfunc main {\n    print(\"Hello World\");\n}")

    def create_side_panels(self, parent_frame):
        # Memory Map
        self.memory_map_frame = ctk.CTkFrame(parent_frame)
        self.memory_map_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.memory_map_frame.grid_columnconfigure(0, weight=1)
        self.memory_map_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.memory_map_frame, text="Live Memory Map", font=ctk.CTkFont(weight="bold")).grid(row=0,
                                                                                                          column=0,
                                                                                                          pady=(5, 0))
        self.memory_map_text = ctk.CTkTextbox(self.memory_map_frame, state="disabled", font=("Consolas", 12))
        self.memory_map_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # White Box
        self.white_box_frame = ctk.CTkFrame(parent_frame)
        self.white_box_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.white_box_frame.grid_columnconfigure(0, weight=1)
        self.white_box_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.white_box_frame, text="TAC Viewer", font=ctk.CTkFont(weight="bold")).grid(row=0,
                                                                                                         column=0,
                                                                                                         pady=(5, 0))
        self.tac_code_text = ctk.CTkTextbox(self.white_box_frame, state="disabled", font=("Consolas", 10))
        self.tac_code_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def create_tabbed_panel(self, parent_frame):
        self.output_tabview = ctk.CTkTabview(parent_frame)
        self.output_tabview.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Define Tabs
        self.tabs = ["Output", "Lexer", "AST", "Errors", "Debug"]
        for t in self.tabs:
            self.output_tabview.add(t)
            self.output_tabview.tab(t).grid_columnconfigure(0, weight=1)
            self.output_tabview.tab(t).grid_rowconfigure(0, weight=1)

        font_style = ("Cascadia Code", 13)

        # Helper to create textboxes
        def create_tb(tab_name, color=None):
            tb = ctk.CTkTextbox(self.output_tabview.tab(tab_name), font=font_style)
            if color: tb.configure(text_color=color)
            tb.grid(row=0, column=0, sticky="nsew")
            tb.configure(state="disabled")
            return tb

        self.output_text = create_tb("Output")
        self.lexer_text = create_tb("Lexer", "#A9B7C6")
        self.ast_text = create_tb("AST", "#FFC66D")
        self.errors_text = create_tb("Errors", "#FF5555")
        self.debug_text = create_tb("Debug")

    # -------------------------------------------------------------------------
    # MAIN RUN LOGIC
    # -------------------------------------------------------------------------

    def run_quantel_code(self):
        code = self.code_editor.get("1.0", "end-1c")

        # Clear Tabs
        self._clear_tab(self.output_text)
        self._clear_tab(self.lexer_text)
        self._clear_tab(self.ast_text)
        self._clear_tab(self.errors_text)
        self._clear_tab(self.debug_text)
        self._clear_tab(self.tac_code_text)  # Clear White Box

        try:
            # 1. LEXER PHASE
            self.quantel_lexer = QuantelLexer()
            tokens_generator = self.quantel_lexer.tokenize(code)
            tokens_list = list(tokens_generator)

            # Display Tokens
            lexer_out = ""
            for tok in tokens_list:
                lexer_out += f"Type: {tok.type:<15} Value: {str(tok.value):<20} Line: {tok.lineno}\n"
            self._write_to_tab(self.lexer_text, lexer_out)

            if self.quantel_lexer.errors:
                self._show_error("Lexer Errors Found:", self.quantel_lexer.errors)
                return

            # 2. PARSER PHASE
            if self.quantel_parser:
                ast_tree = self.quantel_parser.parse(iter(tokens_list))

                if self.quantel_parser.errors:
                    self._show_error("Parser Errors Found:", self.quantel_parser.errors)
                    return

                if ast_tree:
                    # A. Render AST (For AST Tab)
                    tree_str = render_ast_tree(ast_tree)
                    self._write_to_tab(self.ast_text, tree_str)

                    # B. Generate TAC (For White Box Side Panel)
                    # This converts the tree into linear instructions (the "internal view")
                    try:
                        from engine.tac_generator import TACGenerator
                        tac_gen = TACGenerator()
                        tac_output = tac_gen.generate(ast_tree)
                        self._write_to_tab(self.tac_code_text, tac_output)
                    except ImportError:
                        self._write_to_tab(self.tac_code_text, "Error: engine/tac_generator.py not found.")
                    except Exception as e:
                        self._write_to_tab(self.tac_code_text, f"TAC Gen Error: {str(e)}")

                    # 3. INTERPRETER PHASE
                    if QuantelInterpreter:
                        self._write_to_tab(self.output_text, "--- Running Program ---\n")
                        self.interpreter_instance = QuantelInterpreter()

                        f = io.StringIO()
                        try:
                            with contextlib.redirect_stdout(f):
                                self.interpreter_instance.interpret(ast_tree)

                            output_str = f.getvalue()
                            self._write_to_tab(self.output_text, output_str)
                            self._write_to_tab(self.output_text, "\n[Finished]")
                            self.output_tabview.set("Output")

                            # We build a formatted table showing Address | Name | Type | Value

                            header = f"{'ADDRESS':<18} | {'NAME':<12} | {'TYPE':<10} | {'VALUE'}"
                            lines = [header, "-" * len(header)]

                            for name, val in self.interpreter_instance.global_env.items():
                                # 1. GET ADDRESS (Simulated using Python's id())
                                # In a real low-level language, this would be the actual pointer.
                                mem_addr = hex(id(val))

                                # 2. GET TYPE
                                val_type = type(val).__name__
                                if hasattr(val, 'shape'):  # Numpy/Tensor support
                                    val_type = f"Array {val.shape}"

                                # 3. GET VALUE (Truncate if too long)
                                val_str = str(val).replace('\n', ' ')
                                if len(val_str) > 50:
                                    val_str = val_str[:47] + "..."

                                # Format the row
                                row = f"{mem_addr:<18} | {name:<12} | {val_type:<10} | {val_str}"
                                lines.append(row)

                            mem_dump = "\n".join(lines)

                            self._clear_tab(self.memory_map_text)
                            self._write_to_tab(self.memory_map_text, mem_dump)

                        except Exception as e:
                            self._show_error("Runtime Error:", [str(e)])
                    else:
                        self._write_to_tab(self.output_text, "Interpreter module not found.")
                else:
                    self._write_to_tab(self.errors_text, "Parser returned None (Unknown Syntax Error).\n")
                    self.output_tabview.set("Errors")
            else:
                self._write_to_tab(self.debug_text, "Parser not imported.\n")

        except Exception as e:
            self._show_error("System Error:", [str(e)])
            import traceback
            traceback.print_exc()

    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------

    def _show_error(self, title, error_list):
        self.errors_text.configure(state="normal")
        self.errors_text.insert(tk.END, f"--- {title} ---\n")
        for err in error_list:
            self.errors_text.insert(tk.END, f"{err}\n")
        self.errors_text.configure(state="disabled")
        self.output_tabview.set("Errors")

    def _write_to_tab(self, widget, text):
        widget.configure(state="normal")
        widget.insert(tk.END, text)
        widget.configure(state="disabled")

    def _clear_tab(self, widget):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    # --- File/Toggle Helpers ---
    def _new_file(self):
        self.code_editor.delete("1.0", "end")
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
            self.code_editor.delete("1.0", "end")
            self.code_editor.insert("1.0", content)
            self.current_file = filepath
            self.title(f"Quantel IDE - {filepath}")
        except Exception as e:
            print(f"Error opening file: {e}")

    def _save_file(self):
        if self.current_file:
            with open(self.current_file, "w") as f:
                f.write(self.code_editor.get("1.0", "end-1c"))
        else:
            self._save_file_as()

    def _save_file_as(self):
        filepath = filedialog.asksaveasfilename(filetypes=[("Quantel Files", "*.qtl"), ("All Files", "*.*")])
        if filepath:
            with open(filepath, "w") as f: f.write(self.code_editor.get("1.0", "end-1c"))
            self.current_file = filepath
            self.title(f"Quantel IDE - {filepath}")

    def _toggle_memory_map(self):
        # NOTE: With PanedWindow, "hiding" a pane is slightly different.
        # simpler to just forget the frame grid content or remove from pane.
        # For simplicity in this implementation, we toggle grid visibility inside the right panel.
        if self.memory_map_visible:
            self.memory_map_frame.grid_forget()
        else:
            self.memory_map_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.memory_map_visible = not self.memory_map_visible

    def _toggle_white_box_viewer(self):
        if self.white_box_viewer_visible:
            self.white_box_frame.grid_forget()
        else:
            self.white_box_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.white_box_viewer_visible = not self.white_box_viewer_visible


if __name__ == "__main__":
    app = QuantelIDE()
    app.mainloop()