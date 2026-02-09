import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from chlorophyll import CodeView
from gui.quantel_pygments_lexer import QuantelPygmentsLexer
from pygments.styles import get_style_by_name # To choose a style
from pygments.util import ClassNotFound
from engine.lexer import QuantelLexer, QuantelLexerError # Our existing Quantel lexer and custom error
from tkterm import Terminal # Import Terminal widget

class QuantelIDE(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Quantel IDE")
        self.geometry("1200x800")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=3) # Give more weight to the top frame
        self.grid_rowconfigure(1, weight=1) # Less weight to the bottom frame

        # Configure theme
        ctk.set_appearance_mode("System") # Can be "System", "Dark", "Light"
        ctk.set_default_color_theme("blue") # Can be "blue", "dark-blue", "green"

        self.quantel_lexer = QuantelLexer() # Instantiate our custom Quantel lexer
        self.current_file = None # Track the currently open file
        self.memory_map_visible = True
        self.white_box_viewer_visible = True


        # --- Menu Bar ---
        self.create_menu_bar()

        # --- Keyboard Shortcuts ---
        self.bind_shortcuts()

        # --- Main Layout Frames ---
        # Top frame for Editor and Side Panels
        self.top_frame = ctk.CTkFrame(self, corner_radius=0)
        self.top_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.top_frame.grid_columnconfigure(0, weight=3) # Editor takes more space
        self.top_frame.grid_columnconfigure(1, weight=1) # Side panels
        self.top_frame.grid_rowconfigure(0, weight=1)

        # Bottom frame for Output/Console
        self.bottom_frame = ctk.CTkFrame(self, corner_radius=0)
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_rowconfigure(0, weight=1)

        # --- [A] Code Editor Panel (using CodeView) ---
        self.create_code_editor(self.top_frame)

        # --- Side Panels (Memory Map & White Box Viewer) ---
        self.create_side_panels(self.top_frame)

        # --- [D] Output / Console / Error Log Panel ---
        self.create_output_panel(self.bottom_frame)

    def create_menu_bar(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # File Menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self._new_file, accelerator="Cmd+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Cmd+O")
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Cmd+S")
        file_menu.add_command(label="Save As...", command=self._save_file_as, accelerator="Cmd+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Cmd+Q")

        # Edit Menu
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=lambda: self.code_editor.event_generate("<<Undo>>"), accelerator="Cmd+Z")
        edit_menu.add_command(label="Redo", command=lambda: self.code_editor.event_generate("<<Redo>>"), accelerator="Cmd+Shift+Z")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.code_editor.event_generate("<<Cut>>"), accelerator="Cmd+X")
        edit_menu.add_command(label="Copy", command=lambda: self.code_editor.event_generate("<<Copy>>"), accelerator="Cmd+C")
        edit_menu.add_command(label="Paste", command=lambda: self.code_editor.event_generate("<<Paste>>"), accelerator="Cmd+V")

        # Run Menu
        run_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Program", command=self.run_quantel_code, accelerator="F5") # Linked to new method
        run_menu.add_command(label="Stop Program", command=self.dummy_command, accelerator="Shift+F5") # Placeholder for now

        # View Menu
        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Memory Map", command=self._toggle_memory_map, accelerator="Cmd+M")
        view_menu.add_command(label="Toggle White Box Viewer", command=self._toggle_white_box_viewer, accelerator="Cmd+B")

        # Help Menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About Quantel", command=self.show_about_quantel)
        help_menu.add_command(label="Documentation", command=self.show_syntax_docs)

    def bind_shortcuts(self):
        # File operations
        self.bind_all("<Command-n>", lambda event: self._new_file())
        self.bind_all("<Command-o>", lambda event: self._open_file())
        self.bind_all("<Command-s>", lambda event: self._save_file())
        self.bind_all("<Command-S>", lambda event: self._save_file_as()) # Cmd+Shift+S
        self.bind_all("<Command-q>", lambda event: self.quit())

        # Edit operations (CodeView/Text widget typically handles these, but binding them explicitly)
        self.bind_all("<Command-z>", lambda event: self.code_editor.event_generate("<<Undo>>"))
        self.bind_all("<Command-Z>", lambda event: self.code_editor.event_generate("<<Redo>>")) # Cmd+Shift+Z
        self.bind_all("<Command-x>", lambda event: self.code_editor.event_generate("<<Cut>>"))
        self.bind_all("<Command-c>", lambda event: self.code_editor.event_generate("<<Copy>>"))
        self.bind_all("<Command-v>", lambda event: self.code_editor.event_generate("<<Paste>>"))

        # Run
        self.bind_all("<F5>", lambda event: self.run_quantel_code())
        self.bind_all("<Shift-F5>", lambda event: self.dummy_command()) # Stop Program

        # View
        self.bind_all("<Command-m>", lambda event: self._toggle_memory_map())
        self.bind_all("<Command-b>", lambda event: self._toggle_white_box_viewer())


    def dummy_command(self):
        print("Menu item clicked (dummy command)")

    # --- File Menu Callbacks ---
    def _new_file(self):
        self.code_editor.delete("1.0", "end")
        self.current_file = None
        self.title("Quantel IDE - Untitled")

    def _open_file(self):
        filepath = filedialog.askopenfilename(defaultextension=".qtl",
                                              filetypes=[("Quantel Files", "*.qtl"), ("All Files", "*.*")])
        if not filepath:
            return
        self.code_editor.delete("1.0", "end")
        with open(filepath, "r") as input_file:
            text = input_file.read()
            self.code_editor.insert("1.0", text)
        self.current_file = filepath
        self.title(f"Quantel IDE - {filepath}")

    def _save_file(self):
        if self.current_file:
            with open(self.current_file, "w") as output_file:
                text = self.code_editor.get("1.0", "end-1c")
                output_file.write(text)
        else:
            self._save_file_as()

    def _save_file_as(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".qtl",
                                                filetypes=[("Quantel Files", "*.qtl"), ("All Files", "*.*")])
        if not filepath:
            return
        with open(filepath, "w") as output_file:
            text = self.code_editor.get("1.0", "end-1c")
            output_file.write(text)
        self.current_file = filepath
        self.title(f"Quantel IDE - {filepath}")

    # --- View Menu Callbacks ---
    def _toggle_memory_map(self):
        if self.memory_map_visible:
            self.memory_map_frame.grid_forget()
        else:
            self.memory_map_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.memory_map_visible = not self.memory_map_visible
        # Adjust grid weights of side_panel_frame if only one is visible
        if self.memory_map_visible and self.white_box_viewer_visible:
            self.side_panel_frame.grid_rowconfigure(0, weight=1)
            self.side_panel_frame.grid_rowconfigure(1, weight=1)
        elif self.memory_map_visible:
            self.side_panel_frame.grid_rowconfigure(0, weight=1)
            self.side_panel_frame.grid_rowconfigure(1, weight=0) # Only memory map visible
        elif self.white_box_viewer_visible:
            self.side_panel_frame.grid_rowconfigure(0, weight=0)
            self.side_panel_frame.grid_rowconfigure(1, weight=1)
        else: # Neither visible
            self.side_panel_frame.grid_rowconfigure(0, weight=0)
            self.side_panel_frame.grid_rowconfigure(1, weight=0)

    def _toggle_white_box_viewer(self):
        if self.white_box_viewer_visible:
            self.white_box_frame.grid_forget()
        else:
            self.white_box_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.white_box_viewer_visible = not self.white_box_viewer_visible
        # Adjust grid weights of side_panel_frame
        if self.memory_map_visible and self.white_box_viewer_visible:
            self.side_panel_frame.grid_rowconfigure(0, weight=1)
            self.side_panel_frame.grid_rowconfigure(1, weight=1)
        elif self.memory_map_visible:
            self.side_panel_frame.grid_rowconfigure(0, weight=1)
            self.side_panel_frame.grid_rowconfigure(1, weight=0)
        elif self.white_box_viewer_visible:
            self.side_panel_frame.grid_rowconfigure(0, weight=0)
            self.side_panel_frame.grid_rowconfigure(1, weight=1)
        else: # Neither visible
            self.side_panel_frame.grid_rowconfigure(0, weight=0)
            self.side_panel_frame.grid_rowconfigure(1, weight=0)


    def run_quantel_code(self):
        code = self.code_editor.get("1.0", "end-1c") # Get code from CodeView

        # Clear all output/error areas
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

        self.errors_text.configure(state="normal")
        self.errors_text.delete("1.0", "end")
        self.errors_text.configure(state="disabled")
        
        # Re-instantiate lexer for a fresh start with each run
        self.quantel_lexer_instance = QuantelLexer()

        try:
            # Tokenize will now use the updated lexer in engine/lexer.py
            tokens_generator = self.quantel_lexer_instance.tokenize(code)
            
            # Configure tags for colored output
            self.output_text.tag_config("token_type", foreground="cyan")
            self.output_text.tag_config("token_value", foreground="lightgreen")
            
            self.output_text.configure(state="normal")
            self.output_text.insert(tk.END, "--- Lexer Output ---\n")
            
            # Display tokens in Output tab with colors
            for token in tokens_generator:
                self.output_text.insert(tk.END, "Token Type: ")
                self.output_text.insert(tk.END, token.type, "token_type")
                self.output_text.insert(tk.END, ", Value: ")
                self.output_text.insert(tk.END, token.value, "token_value")
                self.output_text.insert(tk.END, f", Line: {token.lineno}, Column: {token.index + 1}\n")
            
            self.output_text.configure(state="disabled")
            self.output_tabview.set("Output") # Always switch to output tab first
            
            # Check for and display lexer errors
            lexer_errors = self.quantel_lexer_instance.get_errors()
            if lexer_errors:
                self.errors_text.configure(state="normal")
                self.errors_text.delete("1.0", "end") # Clear previous errors in the tab
                self.errors_text.insert("1.0", "--- Lexer Errors ---\n")
                
                # Configure tag for red color
                self.errors_text.tag_config("error", foreground="red")
                
                for err_msg in lexer_errors:
                    self.errors_text.insert("end", err_msg + "\n", "error") # Insert with 'error' tag
                
                self.errors_text.configure(state="disabled")
                self.output_tabview.set("Errors") # Always switch to errors tab if errors are present

        except Exception as e:
            # Catch any unexpected Python exceptions during tokenization
            self.errors_text.configure(state="normal")
            self.errors_text.delete("1.0", "end")
            self.errors_text.insert("1.0", f"Unexpected Error during Lexing: {e}")
            self.errors_text.configure(state="disabled")
            self.output_tabview.set("Errors") # Switch to errors tab for unexpected exceptions
        
        self.update_idletasks() # Force UI update
        
    def create_code_editor(self, parent_frame):
        # CodeView handles both line numbers and editor with syntax highlighting
        style_name = "monokai" # A popular dark style, can be changed later

        self.code_editor = CodeView(parent_frame,
                                    lexer=QuantelPygmentsLexer,
                                    font="TkFixedFont", # Monospace font for code
                                    color_scheme=style_name, # Pass the string name of the style
                                    undo=True, # Enable undo/redo
                                    autoseparators=True # Automatically manage undo groups
                                   )
        self.code_editor.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Load sample code from training_demo.qtl or use default
        initial_code = ""
        try:
            with open("samples/training_demo.qtl", "r") as f:
                initial_code = f.read()
            if not initial_code.strip(): # If file is empty or only whitespace
                 initial_code = "# Load error or empty file: samples/training_demo.qtl was empty.\n" + \
                                "# Default sample code:\n" + \
                                "func main() -> void {\n" + \
                                "    float32 scalar my_var = 10.0;\n" + \
                                "    probe(my_var);\n" + \
                                "}"
        except FileNotFoundError:
            initial_code = "# File not found: samples/training_demo.qtl. Using default sample code.\n" + \
                           "func main() -> void {\n" + \
                           "    float32 scalar my_var = 10.0;\n" + \
                           "    probe(my_var);\n" + \
                           "}"
        except Exception as e:
            initial_code = f"# Error loading samples/training_demo.qtl: {e}\n" + \
                           "# Using default sample code.\n" + \
                           "func main() -> void {\n" + \
                           "    float32 scalar my_var = 10.0;\n" + \
                           "    probe(my_var);\n" + \
                           "}"

        self.code_editor.insert("1.0", initial_code)

    def create_side_panels(self, parent_frame):
        self.side_panel_frame = ctk.CTkFrame(parent_frame, corner_radius=8)
        self.side_panel_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.side_panel_frame.grid_columnconfigure(0, weight=1)
        self.side_panel_frame.grid_rowconfigure(0, weight=1)
        self.side_panel_frame.grid_rowconfigure(1, weight=1)

        # [B] Live Memory Map Panel
        self.memory_map_frame = ctk.CTkFrame(self.side_panel_frame, corner_radius=8)
        self.memory_map_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.memory_map_frame.grid_columnconfigure(0, weight=1)
        self.memory_map_frame.grid_rowconfigure(1, weight=1)

        self.memory_map_label = ctk.CTkLabel(self.memory_map_frame, text="Live Memory Map", font=ctk.CTkFont(weight="bold"))
        self.memory_map_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.memory_map_text = ctk.CTkTextbox(self.memory_map_frame, state="disabled")
        self.memory_map_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.memory_map_text.insert("1.0", "Variable | Type       | Value | Address\n---------------------------------------------\nmy_var   | scalar     | 10.0  | 0xABCDEF01")


        # [C] White Box Viewer Panel
        self.white_box_frame = ctk.CTkFrame(self.side_panel_frame, corner_radius=8)
        self.white_box_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.white_box_frame.grid_columnconfigure(0, weight=1)
        self.white_box_frame.grid_columnconfigure(1, weight=1)
        self.white_box_frame.grid_rowconfigure(1, weight=1)

        self.white_box_label = ctk.CTkLabel(self.white_box_frame, text="White Box Viewer", font=ctk.CTkFont(weight="bold"))
        self.white_box_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.original_code_text = ctk.CTkTextbox(self.white_box_frame, state="disabled")
        self.original_code_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.original_code_text.insert("1.0", "Original Quantel Code\n\nfunc main() {\n    my_var = 10.0;\n}")

        self.tac_code_text = ctk.CTkTextbox(self.white_box_frame, state="disabled")
        self.tac_code_text.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.tac_code_text.insert("1.0", "Three-Address Code\n\nt1 = 10.0\nmy_var = t1")

    def create_output_panel(self, parent_frame):
        self.output_tabview = ctk.CTkTabview(parent_frame, corner_radius=8)
        self.output_tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.output_tabview.add("Output")
        self.output_tabview.add("Errors")
        self.output_tabview.add("Debug")

        # Output Tab - using CTkTextbox
        self.output_tabview.tab("Output").grid_columnconfigure(0, weight=1)
        self.output_tabview.tab("Output").grid_rowconfigure(0, weight=1)
        self.output_text = ctk.CTkTextbox(self.output_tabview.tab("Output"), font=("Cascadia Code", 13, "normal"))
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.output_text.insert(tk.END, "Program output will appear here.\n")
        self.output_text.configure(state="disabled") # Make it read-only initially

        # Errors Tab - using CTkTextbox
        self.output_tabview.tab("Errors").grid_columnconfigure(0, weight=1)
        self.output_tabview.tab("Errors").grid_rowconfigure(0, weight=1)
        self.errors_text = ctk.CTkTextbox(self.output_tabview.tab("Errors"), font=("Cascadia Code", 13, "normal"))
        self.errors_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.errors_text.insert(tk.END, "Errors and warnings will be displayed here.\n")
        self.errors_text.configure(state="disabled") # Make it read-only initially

        # Debug Tab - using CTkTextbox
        self.output_tabview.tab("Debug").grid_columnconfigure(0, weight=1)
        self.output_tabview.tab("Debug").grid_rowconfigure(0, weight=1)
        self.debug_text = ctk.CTkTextbox(self.output_tabview.tab("Debug"), font=("Cascadia Code", 13, "normal"))
        self.debug_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.debug_text.insert(tk.END, "Debug information will appear here.\n")
        self.debug_text.configure(state="disabled") # Make it read-only initially

    def show_syntax_docs(self):
        # OCR content of CSC617M Syntax Definition.pdf (extracted previously)
        syntax_docs_content = """
Rodriguez, Kaizen Edwin C.
Asuncion, Enrico Jose
Abarquez, Jean Khladyn Stefanie
CSC615M G02
January 30, 2026
Preliminary Syntax Definition
Quantel Programming Language

The grammar G = (V, T, S, P) of our interpreter is defined by:

V = { <program>, <import list>, <stmt list>, <stmt>, <block>,
<decl>, <pointer_decl>, <dtype>, <shape_type>, <dim_list>,
<record_decl>, <field_list>, <func_decl>, <param_list>,
<assignment>, <assign_op>, <target>, <func_call>, <arg_list>,
<expr>, <add_op>, <comp_op>, <term>, <mul_op>, <factor>,
<primary>, <control_flow>, <if_stmt>, <for_stmt>, <while_stmt>,
<repeat_stmt>, <range>, <probe_call>, <id>, <num>, <letter>,
<digit>, <letter or digit*> }

T = { import, record, func, return, if, else, for, in, while,
repeat, until, probe, break, continue, float32, float64,
float16, int32, int64, bool, scalar, vector, matrix, tensor, =,
+=, -=, *=, /=, @=, +, *, /, @, %, ^, ==, !=, >, <, >=, <=,
&, ->, ;,,, {, }, (,), [,], a...z, A...Z, 0...9 }

S = <program>

P has the following productions:

Program Structure:

<program> -> <import_list> <stmt_list>
<import_list> -> import <id> ; <import list> | ∈
<stmt_list> -> <stmt> <stmt list> | <stmt>
<stmt> -> <decl> | <assignment> | <control_flow> |
<probe call> | <record_decl> | <func_decl>
| <block> | return <expr> ; | break; |
continue;
<block> -> { <stmt_list> }

Functions
<func_decl> -> func <id> ( <param list> ) -> <dtype>
<shape_type> <block>
<param_list> -> <dtype> <shape_type> <id> | <dtype>
<shape_type> <id> , <param list> | ε
<func_call> -> <id> ( <arg_list> )
<arg_list> -> <expr> | <expr> , <arg_list> | ε

Declarations and Types:
<decl> -> <dtype> <shape_type> <id> ; | <dtype>
<shape_type> <id> = <expr> ;
<pointer_decl> -> <dtype> <shape_type> * <id> = & <id> ;
<dtype> -> float32 | float64 | float16 | int32 | int64
| bool
<shape_type> -> scalar | vector < <num> > | matrix < <num>
, <num> > | tensor < <dim list> >
<dim_list> -> <num> | <num> , <dim_list>
<record_decl> -> record <id> { <field list> }
<field_list> -> <decl> | <decl> <field_list>

Assignment and Expressions
<assignment> -> <target> <assign_op> <expr> ;
<target> -> <id> | <id> [ <num> ] | <id> . <id>
<assign_op> -> = | += | -= | *= | /= | @=
<expr> -> <term> <add_op> <expr> | <term> <comp_op>
<term> | <term>
<add_op> -> + | -
<comp_op> -> == | != | > | < | >= | <=
<term> -> <factor> <mul_op> <term> | <factor>
<mul_op> -> * | / | @ | %
<factor> -> <primary> ^ <factor> | <primary>
<primary> -> ( <expr> ) | <id> | <num> | <primary> |
<func_call>

Control Flow
<control_flow> -> <if_stmt> | <for_stmt> | <while_stmt> |
<repeat_stmt>
<if_stmt> -> if ( <expr> ) <block> | if ( <expr> )
<block> else <block>
<for_stmt> -> for <id> in <range> <block>
<while_stmt> -> while ( <expr> ) <block>
<repeat_stmt> -> repeat <block> until ( <expr> ) ;
<range> -> <num> .. <num> | <num> .. <num> step <expr>

Debugging and Terminals
<probe_call> -> probe ( <target> );
<id> -> <letter> <letter_or_digit*>
<num> -> <digit> | <digit> <num>
<letter> -> a | b | ... | z | A | B | ... | Z
<digit> -> 0 | 1 | ... | 9
<letter_or_digit*> -> <letter> <letter_or_digit*> | <digit>
<letter_or_digit*> | ε
"""
        popup = ctk.CTkToplevel(self)
        popup.title("Quantel Syntax Documentation")
        popup.geometry("800x600")

        textbox = ctk.CTkTextbox(popup, wrap="word")
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        textbox.insert("1.0", syntax_docs_content)
        textbox.configure(state="disabled") # Make it read-only

    def show_about_quantel(self):
        # Filtered OCR content of CFG NOTES.pdf (extracted previously)
        about_quantel_content = """
Project Proposal: Quantel
Name: Quantel (Quantized Elements)
Implementation: Python 3.x (macOS)
Language Type: A Domain-Specific Language (DSL) designed
specifically for AI/ML development.

Problem Statement: Mainstream AI frameworks like PyTorch and
TensorFlow typically use Dynamic Shape Checking. This means they
only detect dimensional mismatches while the program is actually
running. If a model crashes 5 hours into a training session
because of a shape error, all that time and compute power is
wasted.

Core Purpose: It provides built-in safety for tensor
operations, ensuring that the mathematical "shape" of data is
correct before the model begins training.

1. Key Technical Features
Quantel uses static typing for shapes. This means the size of
data is checked before the code runs.
• Data Types:
Quantel uses a Composite Type System where a variable's
type is defined by its Precision (bit-width) and its Rank
(dimensions).
• <dtype> scalar: A 0th-order tensor representing a
single numerical value.
Ο Example: float32 scalar lr = 0.01;
• <dtype> vector<n>: A 1st-order tensor (1D array) with
exactly n elements.
Ο Example: float32 vector<128> bias;
• <dtype> matrix<r, c>: A 2nd-order tensor (2D grid)
with r rows and c columns.
Ο Example: float32 matrix<3, 2> weights;
• <dtype> tensor<d1, d2, ...dn>: An N-dimensional tensor
for high-order data (e.g., batches of images).
• Control Flow:
Supports if-else, for, while, and repeat-until.
• Debug Tool (probe):
A command that prints the variable's value, its dimensions
(shape), and its specific hex address in RAM.
• User-Defined Types (Bonus):
Use the record keyword to group data.
Ο Example: record Layer { tensor<64, 128> w; scalar
bias; }
• Reference Types (Bonus):
Uses pointers for tensors. Instead of copying a
10,000-element matrix into a function, Quantel passes the
memory address to save RAM.

2. Optimization Techniques (Bonus)
The compiler cleans up the Three-Address Code (TAC) before
execution:
1. Constant Folding:
If you write scalar x = 10 * 5;, the compiler replaces it
with 50 so the math isn't repeated during runtime.
2. Loop Unrolling:
If a loop runs a fixed number of times (e.g., 3), the
compiler repeats the code 3 times instead of using a jump
instruction.
3. Dead Code Elimination:
If a variable is calculated but never used, the compiler
removes it entirely to free up memory.

3. Standalone IDE & UI (Bonus)
We are building a desktop application for macOS using
CustomTkinter.
• Live Memory Map:
A UI panel that shows a table of all variables and their
current memory addresses as the code executes.
• White Box Viewer:
A split-screen window showing your original code on one
side and the Optimized TAC on the other.
• Distribution:
Compiled into a double-clickable .app file using
PyInstaller.

4. Testing & Validation
• Negative Parsing:
We will provide test files with "Bad Math" (e.g.,
multiplying a 2x3 matrix by a 5x5 matrix). The test is
successful if the Parser rejects the code with a dimension
error.
• Optimization Audit:
Comparing the number of lines in "Raw TAC" vs "Optimized
TAC" to prove the code is shorter and more efficient.
• Memory Tracking:
Using the IDE to confirm that record fields are correctly
mapped to adjacent memory slots.

5. Bonus Requirement Coverage Checklist
• Pointers:
Used in tensor references.
• Memory Manipulation:
Shown via the Live Memory Map.
• User-Defined Types:
Handled via record.
• Optimizations:
Constant Folding, Loop Unrolling, and Dead Code
Elimination.
• IDE:
Standalone macOS desktop application.
"""
        popup = ctk.CTkToplevel(self)
        popup.title("About Quantel")
        popup.geometry("800x600")

        textbox = ctk.CTkTextbox(popup, wrap="word")
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        textbox.insert("1.0", about_quantel_content)
        textbox.configure(state="disabled") # Make it read-only

if __name__ == "__main__":
    app = QuantelIDE()
    app.mainloop()
