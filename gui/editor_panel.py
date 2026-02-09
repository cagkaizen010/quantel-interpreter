import customtkinter as ctk
import tkinter as tk
from chlorophyll import CodeView
from gui.highlighter import QuantelHighlighter


class EditorPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Ensure the frame expands
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Initialize Chlorophyll CodeView
        self.code_view = CodeView(
            self,
            lexer=QuantelHighlighter,
            font=("Consolas", 14),
            color_scheme="monokai",
            undo=True
        )
        self.code_view.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Access the underlying Tkinter text widget
        if hasattr(self.code_view, '_code_view'):
            self.textbox = self.code_view._code_view
        elif hasattr(self.code_view, 'code_view'):
            self.textbox = self.code_view.code_view
        else:
            self.textbox = self.code_view

        # --- NEW HIGHLIGHT STYLES ---
        # Error: Bright Red Background with White Text
        self.textbox.tag_config("error", background="#880000", foreground="white")

        # Jump: Subtle Yellow/Gold background (for Lexer table clicks)
        self.textbox.tag_config("jump_highlight", background="#4a4a30")

        # Default text
        self.set_text("// Type your Quantel code here...\nfunc main {\n    print(\"Hello World\");\n}")

    def get_text(self):
        return self.code_view.get("1.0", "end-1c")

    def set_text(self, text):
        self.code_view.delete("1.0", "end")
        self.code_view.insert("1.0", text)

    def clear_indicators(self):
        """Removes all error highlights and jump highlights."""
        self.textbox.tag_remove("error", "1.0", "end")
        self.textbox.tag_remove("jump_highlight", "1.0", "end")

    def mark_error(self, line, column=None, length=1):
        """Highlights the background of the error line/token."""
        try:
            if column is not None:
                start = f"{line}.{column}"
                end = f"{line}.{column + length}"
            else:
                start = f"{line}.0"
                end = f"{line}.end"

            self.textbox.tag_add("error", start, end)
            self.textbox.see(start)
        except Exception as e:
            print(f"Highlighting error: {e}")

    def highlight_line(self, line_number):
        """Highlights the background when clicking items in the Output tab."""
        self.textbox.tag_remove("jump_highlight", "1.0", "end")
        index = f"{line_number}.0"
        self.textbox.tag_add("jump_highlight", f"{index} linestart", f"{index} lineend")
        self.textbox.see(index)