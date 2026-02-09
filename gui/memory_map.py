import customtkinter as ctk
import tkinter as tk

class MemoryMapPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Label
        self.label = ctk.CTkLabel(self, text="Live Memory Map", font=ctk.CTkFont(weight="bold"))
        self.label.grid(row=0, column=0, pady=(5, 0), sticky="ew")

        # Text Area (Read-only)
        self.text_area = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 12))
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def update_map(self, environment):
        """
        Takes the Interpreter's global_env dictionary and formats it into a table.
        """
        self._clear()

        if not environment:
            self._write("Memory is empty.")
            return

        # Table Header
        header = f"{'ADDRESS':<14} | {'NAME':<12} | {'TYPE':<10} | {'VALUE'}"
        lines = [header, "-" * len(header)]

        for name, val in environment.items():
            # 1. GET ADDRESS (Simulated using Python's id())
            mem_addr = f"0x{id(val):x}"

            # 2. GET TYPE
            val_type = type(val).__name__
            if hasattr(val, 'shape'):  # Numpy/Tensor support
                val_type = f"Arr{val.shape}"

            # 3. GET VALUE (Truncate if too long)
            val_str = str(val).replace('\n', ' ')
            if len(val_str) > 40:
                val_str = val_str[:37] + "..."

            # Format the row
            row = f"{mem_addr:<14} | {name:<12} | {val_type:<10} | {val_str}"
            lines.append(row)

        self._write("\n".join(lines))

    def _write(self, content):
        self.text_area.configure(state="normal")
        self.text_area.insert("0.0", content)
        self.text_area.configure(state="disabled")

    def _clear(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("0.0", "end")
        self.text_area.configure(state="disabled")