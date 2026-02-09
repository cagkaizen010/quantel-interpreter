import customtkinter as ctk
import tkinter as tk


class TACViewerPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.label = ctk.CTkLabel(self, text="TAC Viewer (White Box)", font=ctk.CTkFont(weight="bold"))
        self.label.grid(row=0, column=0, pady=(5, 0), sticky="ew")

        # Text Area
        self.text_area = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 11))
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def generate_and_show(self, ast_tree):
        """
        Imports the generator dynamically (to prevent circular imports)
        and renders the output.
        """
        self._clear()

        if not ast_tree:
            self._write("No AST available.")
            return

        try:
            # Dynamic import to ensure engine exists
            from engine.tac_generator import TACGenerator

            tac_gen = TACGenerator()
            tac_output = tac_gen.generate(ast_tree)
            self._write(tac_output)

        except ImportError:
            self._write("[Error] engine/tac_generator.py not found.\nCannot generate intermediate code.")
        except Exception as e:
            self._write(f"[Error] TAC Generation failed:\n{str(e)}")

    def _write(self, content):
        self.text_area.configure(state="normal")
        self.text_area.insert("0.0", content)
        self.text_area.configure(state="disabled")

    def _clear(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("0.0", "end")
        self.text_area.configure(state="disabled")