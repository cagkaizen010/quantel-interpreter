import customtkinter as ctk
import tkinter as tk
from tabulate import tabulate
import re
import queue

class OutputPanel(ctk.CTkFrame):
    def __init__(self, parent, on_line_click=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_line_click = on_line_click
        self.input_queue = queue.Queue()
        self.prompt_mark = "input_start"

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.tabs = {}
        technical_font = ("Courier New", 12)

        for name in ["Output", "Lexer", "AST", "Symbols", "Errors"]:
            self.tab_view.add(name)
            self.tab_view.tab(name).grid_columnconfigure(0, weight=1)
            self.tab_view.tab(name).grid_rowconfigure(0, weight=1)

            tb = ctk.CTkTextbox(self.tab_view.tab(name), font=technical_font, wrap="none")
            tb.grid(row=0, column=0, sticky="nsew")
            
            # Universal key-handler to prevent typing but allow selection/copying
            tb.bind("<Key>", lambda e, n=name: self._on_key(e, n))

            if name == "Output":
                tb.bind("<Return>", self._handle_return)
                # Initialize the prompt mark
                tb.mark_set(self.prompt_mark, "1.0")
                tb.mark_gravity(self.prompt_mark, tk.LEFT)
            
            # Setup tags for color
            tb.tag_config("red", foreground="#FF5555")
                
            self.tabs[name] = tb

            if name == "Lexer":
                tb.bind("<Button-1>", self._handle_click)

        self.tabs["Lexer"].configure(text_color="#A9B7C6")
        self.tabs["Symbols"].configure(text_color="#58D68D")
        self.tabs["Errors"].configure(text_color="#FF5555")

    def _on_key(self, event, tab_name="Output"):
        """Universal handler: allows navigation/copying, but blocks modification."""
        widget = self.tabs[tab_name]

        # Navigation/Copying keys are always allowed
        allowed_keys = [
            "Left", "Right", "Up", "Down", "Prior", "Next", 
            "Home", "End", "c", "C", "a", "A", "v", "V"
        ]

        # Allow Ctrl+C (Copy), Ctrl+A (Select All)
        if (event.state & 0x4):
            if event.keysym.lower() in ["c", "a"]:
                return None 
            if tab_name == "Output" and event.keysym.lower() == "v":
                return None

        if event.keysym in allowed_keys:
            return None 

        # Output Tab has special "terminal" behavior
        if tab_name == "Output":
            if widget.compare("insert", "<", self.prompt_mark):
                return "break"
            if event.keysym == "BackSpace":
                if widget.compare("insert", "<=", self.prompt_mark):
                    return "break"
            return None 

        return "break"

    def _handle_return(self, event):
        """Captures input and sends it to the queue."""
        widget = self.tabs["Output"]
        
        # Get everything from the prompt mark to the end
        user_input = widget.get(self.prompt_mark, "end-1c").strip("\n")
        self.input_queue.put(user_input)
        
        # Advance the prompt mark to the end of this input (after the newline)
        # We'll do this after the newline is actually inserted by the default handler
        self.after(1, self._move_prompt_to_end)
        
        # Allow the default Return behavior to insert the newline

    def _move_prompt_to_end(self):
        widget = self.tabs["Output"]
        widget.mark_set(self.prompt_mark, "end-1c")
        widget.see(tk.END)

    def _handle_click(self, event):
        if not self.on_line_click: return
        widget = event.widget
        click_pos = widget.index(f"@{event.x},{event.y}")
        line_content = widget.get(f"{click_pos} linestart", f"{click_pos} lineend")
        match = re.search(r"L(\d+)", line_content)
        if match:
            self.on_line_click(int(match.group(1)))

    def write(self, tab_name, content, clear_first=True, tag=None):
        if tab_name not in self.tabs: return
        widget = self.tabs[tab_name]
        
        # Only toggle state for tabs that are normally disabled
        should_toggle = (tab_name != "Output")
        if should_toggle: 
            widget.configure(state="normal")
        
        if clear_first: 
            widget.delete("1.0", "end")
            if tab_name == "Output":
                widget.mark_set(self.prompt_mark, "1.0")
            
        if tag:
            widget.insert(tk.END, content, tag)
        else:
            widget.insert(tk.END, content)
        
        if tab_name == "Output":
            # Update prompt mark to the end of the newly written output (the prompt)
            widget.mark_set(self.prompt_mark, "end-1c")
            widget.see(tk.END)
            # Focus so user can type immediately
            widget.focus_set()
        
        if should_toggle: 
            widget.configure(state="disabled")

    def write_table(self, tab_name, data, headers):
        if tab_name not in self.tabs: return
        table_output = tabulate(data, headers=headers, tablefmt="github", stralign="left")
        self.write(tab_name, table_output + "\n", clear_first=True)

    def update_lexer_tab(self, token_list):
        rows = [[t.type, repr(t.value)[:37] + "..." if len(repr(t.value)) > 40 else repr(t.value), f"L{t.lineno}"] for t in token_list]
        self.write_table("Lexer", rows, headers=["TOKEN TYPE", "VALUE", "LINE"])

    def update_symbols_tab(self, analyzer):
        rows = []
        built_ins = {'print', 'load_csv'}
        if hasattr(analyzer, 'history'):
            for name, sym in analyzer.history.items():
                if name not in built_ins:
                    rows.append([name, getattr(sym, 'symbol_type', 'unknown'), getattr(sym, 'category', 'var')])
        self.write_table("Symbols", rows, headers=["NAME", "TYPE", "CATEGORY"])

    def clear_all(self):
        for name in self.tabs: self.write(name, "", clear_first=True)

    def select_tab(self, tab_name): self.tab_view.set(tab_name)

    def show_error(self, title, error_list, tab="Errors"):
        content = f"--- {title} ---\n" + "\n".join([str(e) for e in error_list])
        self.write(tab, content + "\n")
        self.select_tab(tab)

    def get_input(self):
        """Blocks until input is available in the queue."""
        return self.input_queue.get()
