import customtkinter as ctk
import tkinter as tk
from tabulate import tabulate
import re


class TACViewerPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label = ctk.CTkLabel(self, text="TAC Viewer (White Box)", font=ctk.CTkFont(size=14, weight="bold"))
        self.label.grid(row=0, column=0, pady=(10, 5), sticky="ew")

        # Use Courier New for strictly aligned columns
        self.text_area = ctk.CTkTextbox(self, state="disabled", font=("Courier New", 12), wrap="none")
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def generate_and_show(self, ast_tree):
        self._clear()
        if not ast_tree:
            self._write("No AST available.")
            return

        try:
            from engine.tac_generator import TACGenerator
            tac_gen = TACGenerator()
            raw_tac = tac_gen.generate(ast_tree)

            # 1. Handle string or list input
            if isinstance(raw_tac, str):
                lines = raw_tac.strip().split('\n')
            else:
                lines = raw_tac

            # 2. Parse lines into [OP, ARG1, ARG2, RESULT]
            table_data = []
            for line in lines:
                line = line.strip()
                if not line: continue

                row = ["", "", "", ""]  # Default empty columns

                # Pattern: res = arg1 op arg2 (e.g., t3 = Weights @ input_vec)
                if '=' in line and any(op in line for op in ['+', '-', '*', '/', '@', '&&', '||']):
                    parts = re.split(r' = | ', line)
                    # result = parts[0], arg1 = parts[1], op = parts[2], arg2 = parts[3]
                    if len(parts) >= 4:
                        row = [parts[2], parts[1], parts[3], parts[0]]

                # Pattern: res = arg (e.g., epoch_counter = 0)
                elif '=' in line:
                    parts = line.split(' = ')
                    row = ["ASSIGN", parts[1], "", parts[0]]

                # Pattern: FUNC/LABEL/GOTO (e.g., FUNC relu_activation:)
                elif line.startswith(("FUNC", "L_", "GOTO", "IF_FALSE", "PROBE", "ENDFUNC")):
                    parts = line.split()
                    row[0] = parts[0]  # The Command
                    if len(parts) > 1: row[1] = parts[1]  # The Target/Label
                    if len(parts) > 2: row[2] = " ".join(parts[2:])  # Extra context

                else:
                    row[0] = line  # Catch-all for miscellaneous lines

                table_data.append(row)

            # 3. Generate the actual table
            formatted_table = tabulate(
                table_data,
                headers=["OP", "ARG 1", "ARG 2", "RESULT"],
                tablefmt="github",
                stralign="left"
            )

            self._write(formatted_table)

        except Exception as e:
            self._write(f"[Error] TAC Formatting failed:\n{str(e)}")

    def _write(self, content):
        self.text_area.configure(state="normal")
        self.text_area.insert("1.0", content)
        self.text_area.configure(state="disabled")

    def _clear(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.configure(state="disabled")