import customtkinter as ctk
import tkinter as tk
from tabulate import tabulate
import re

class OutputPanel(ctk.CTkFrame):
    def __init__(self, parent, on_line_click=None, **kwargs):
        # Remove custom arg before passing to CTkFrame to avoid ValueError
        super().__init__(parent, **kwargs)
        self.on_line_click = on_line_click

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.tabs = {}
        technical_font = ("Courier New", 12)

        for name in ["Output", "Lexer", "AST", "Symbols", "Errors", "Debug"]:
            self.tab_view.add(name)
            self.tab_view.tab(name).grid_columnconfigure(0, weight=1)
            self.tab_view.tab(name).grid_rowconfigure(0, weight=1)

            tb = ctk.CTkTextbox(self.tab_view.tab(name), font=technical_font, wrap="none")
            tb.grid(row=0, column=0, sticky="nsew")
            tb.configure(state="disabled")
            self.tabs[name] = tb

            if name == "Lexer":
                tb.bind("<Button-1>", self._handle_click)

        self.tabs["Lexer"].configure(text_color="#A9B7C6")
        self.tabs["Symbols"].configure(text_color="#58D68D")
        self.tabs["Errors"].configure(text_color="#FF5555")

    def _handle_click(self, event):
        if not self.on_line_click: return
        widget = event.widget
        click_pos = widget.index(f"@{event.x},{event.y}")
        line_content = widget.get(f"{click_pos} linestart", f"{click_pos} lineend")
        match = re.search(r"L(\d+)", line_content)
        if match:
            self.on_line_click(int(match.group(1)))

    def write(self, tab_name, content, clear_first=True):
        if tab_name not in self.tabs: return
        widget = self.tabs[tab_name]
        widget.configure(state="normal")
        if clear_first: widget.delete("1.0", "end")
        widget.insert(tk.END, content + "\n")
        widget.configure(state="disabled")

    def write_table(self, tab_name, data, headers):
        if tab_name not in self.tabs: return
        table_output = tabulate(data, headers=headers, tablefmt="github", stralign="left")
        self.write(tab_name, table_output, clear_first=True)

    def update_lexer_tab(self, token_list):
        rows = [[t.type, repr(t.value)[:37] + "..." if len(repr(t.value)) > 40 else repr(t.value), f"L{t.lineno}"] for t in token_list]
        self.write_table("Lexer", rows, headers=["TOKEN TYPE", "VALUE", "LINE"])

    def update_symbols_tab(self, analyzer):
        rows = []
        if hasattr(analyzer, 'history'):
            for name, sym in analyzer.history.items():
                rows.append([name, getattr(sym, 'symbol_type', 'unknown'), getattr(sym, 'category', 'var')])
        self.write_table("Symbols", rows, headers=["NAME", "TYPE", "CATEGORY"])

    def clear_all(self):
        for name in self.tabs: self.write(name, "", clear_first=True)

    def select_tab(self, tab_name): self.tab_view.set(tab_name)

    def show_error(self, title, error_list):
        content = f"--- {title} ---\n" + "\n".join([str(e) for e in error_list])
        self.write("Errors", content)
        self.select_tab("Errors")