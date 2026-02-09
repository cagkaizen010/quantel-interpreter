# gui/editor_panel.py
import customtkinter as ctk
from chlorophyll import CodeView
from gui.highlighter import QuantelHighlighter


class EditorPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Ensure the frame expands
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Initialize Chlorophyll CodeView
        self.code_view = CodeView(self, lexer=QuantelHighlighter, font=("Consolas", 14),
                                  color_scheme="monokai", undo=True)
        self.code_view.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Default text
        self.set_text("// Type your Quantel code here...\nfunc main {\n    print(\"Hello World\");\n}")

    def get_text(self):
        return self.code_view.get("1.0", "end-1c")

    def set_text(self, text):
        self.code_view.delete("1.0", "end")
        self.code_view.insert("1.0", text)