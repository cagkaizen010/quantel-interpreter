import customtkinter as ctk
import tkinter as tk
from tabulate import tabulate


class OutputPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.tabs = {}
        # Monospaced font is the key to that clean "White Box" alignment
        technical_font = ("Courier New", 12)

        for name in ["Output", "Lexer", "AST", "Symbols", "Errors", "Debug"]:
            self.tab_view.add(name)
            self.tab_view.tab(name).grid_columnconfigure(0, weight=1)
            self.tab_view.tab(name).grid_rowconfigure(0, weight=1)

            tb = ctk.CTkTextbox(self.tab_view.tab(name), font=technical_font, wrap="none")
            tb.grid(row=0, column=0, sticky="nsew")
            tb.configure(state="disabled")
            self.tabs[name] = tb

        self.tabs["Lexer"].configure(text_color="#A9B7C6")
        self.tabs["Symbols"].configure(text_color="#58D68D")
        self.tabs["Errors"].configure(text_color="#FF5555")

    def write(self, tab_name, content, clear_first=True):
        """The core write method (now named correctly to prevent crashes)."""
        if tab_name not in self.tabs: return
        widget = self.tabs[tab_name]
        widget.configure(state="normal")
        if clear_first:
            widget.delete("1.0", "end")
        widget.insert(tk.END, content + "\n")
        widget.configure(state="disabled")

    def write_table(self, tab_name, data, headers):
        """Standardized table renderer."""
        if tab_name not in self.tabs: return
        table_output = tabulate(data, headers=headers, tablefmt="github", stralign="left")
        self.write(tab_name, table_output, clear_first=True)

    def update_lexer_tab(self, token_list):
        """Renders the Lexer results as a beautiful table."""
        rows = []
        for t in token_list:
            val_str = repr(t.value)
            if len(val_str) > 40:
                val_str = val_str[:37] + "..."
            rows.append([t.type, val_str, f"L{t.lineno}"])

        self.write_table("Lexer", rows, headers=["TOKEN TYPE", "VALUE", "LINE"])

    def update_symbols_tab(self, symbol_table):
        """Renders the Symbol Table as a beautiful table."""
        rows = []
        # Checks if symbol_table is a dict (standard) or a list
        items = symbol_table.items() if hasattr(symbol_table, 'items') else symbol_table

        for name, sym in items:
            dtype = getattr(sym, 'dtype', 'unknown')
            category = getattr(sym, 'category', 'var')
            rows.append([name, dtype, category])

        self.write_table("Symbols", rows, headers=["NAME", "DTYPE", "CATEGORY"])

    def clear_all(self):
        """Resets every tab for a clean run."""
        for name in self.tabs:
            self.write(name, "", clear_first=True)

    def select_tab(self, tab_name):
        self.tab_view.set(tab_name)

    def show_error(self, title, error_list):
        content = f"--- {title} ---\n" + "\n".join([str(e) for e in error_list])
        self.write("Errors", content)
        self.select_tab("Errors")