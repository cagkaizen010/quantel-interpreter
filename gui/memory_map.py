import customtkinter as ctk
import tkinter as tk
from tabulate import tabulate

class MemoryMapPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Label
        self.label = ctk.CTkLabel(self, text="Live Memory Map", font=ctk.CTkFont(size=14, weight="bold"))
        self.label.grid(row=0, column=0, pady=(10, 5), sticky="ew")

        # Text Area (Read-only) - Use a Monospaced font for table alignment
        self.text_area = ctk.CTkTextbox(self, state="disabled", font=("Courier New", 12), wrap="none")
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def update_map(self, environment):
        """
        Takes the Interpreter's global_env dictionary and formats it using tabulate.
        """
        self._clear()

        if not environment:
            self._write("Memory is empty.")
            return

        # 1. Prepare data rows for tabulate
        table_data = []
        for name, val in environment.items():
            # Get Address
            mem_addr = f"0x{id(val):x}"

            # Get Type (with Shape support for Tensors/Arrays)
            val_type = type(val).__name__
            if hasattr(val, 'shape'):
                # Formats as Arr(3,3) or Arr(3,)
                val_type = f"Arr{tuple(val.shape)}" if len(val.shape) > 0 else "Arr()"

            # Get Value and clean it up
            val_str = str(val).replace('\n', ' ')
            if len(val_str) > 50:
                val_str = val_str[:47] + "..."

            table_data.append([mem_addr, name, val_type, val_str])

        # 2. Generate the table using tabulate
        # 'github' format creates clean separators that look good in a terminal/textbox
        formatted_table = tabulate(
            table_data,
            headers=["ADDRESS", "NAME", "TYPE", "VALUE"],
            tablefmt="github",
            stralign="left"
        )

        self._write(formatted_table)

    def _write(self, content):
        self.text_area.configure(state="normal")
        self.text_area.insert("0.0", content)
        # Scroll to top after inserting
        self.text_area.see("1.0")
        self.text_area.configure(state="disabled")

    def _clear(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("0.0", "end")
        self.text_area.configure(state="disabled")