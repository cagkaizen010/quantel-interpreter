# gui/output_panel.py
import customtkinter as ctk
import tkinter as tk


class OutputPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Create Tabs
        self.tabs = {}
        for name in ["Output", "Lexer", "AST", "Errors", "Debug"]:
            self.tab_view.add(name)
            self.tab_view.tab(name).grid_columnconfigure(0, weight=1)
            self.tab_view.tab(name).grid_rowconfigure(0, weight=1)

            # Create Textbox for each tab
            tb = ctk.CTkTextbox(self.tab_view.tab(name), font=("Cascadia Code", 13))
            tb.grid(row=0, column=0, sticky="nsew")
            tb.configure(state="disabled")

            # Store reference
            self.tabs[name] = tb

        # Custom colors
        self.tabs["Lexer"].configure(text_color="#A9B7C6")
        self.tabs["AST"].configure(text_color="#FFC66D")
        self.tabs["Errors"].configure(text_color="#FF5555")

    def write(self, tab_name, content, clear_first=True):
        if tab_name not in self.tabs: return
        widget = self.tabs[tab_name]

        widget.configure(state="normal")
        if clear_first:
            widget.delete("1.0", "end")
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def clear_all(self):
        for name in self.tabs:
            self.write(name, "", clear_first=True)

    def select_tab(self, tab_name):
        self.tab_view.set(tab_name)

    def show_error(self, title, error_list):
        content = f"--- {title} ---\n" + "\n".join([str(e) for e in error_list])
        self.write("Errors", content)
        self.select_tab("Errors")