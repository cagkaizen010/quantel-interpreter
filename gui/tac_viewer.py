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
                bin_op_match = re.match(r"(\w+) = (\w+) ([\+\-\*/@%^&|<>!]=?|==|!=|&&|\|\|) (\w+)", line)
                
                # Pattern: res = op arg (e.g., t4 = -t3)
                unary_op_match = re.match(r"(\w+) = ([\-!&])(\w+)", line)

                # Pattern: res = arg (e.g., x = 5)
                assign_match = re.match(r"(\w+) = (.+)", line)

                if bin_op_match:
                    res, arg1, op, arg2 = bin_op_match.groups()
                    row = [op, arg1, arg2, res]
                elif unary_op_match:
                    res, op, arg = unary_op_match.groups()
                    row = [op, arg, "", res]
                elif assign_match:
                    res, val = assign_match.groups()
                    row = ["ASSIGN", val, "", res]
                elif line.startswith(("FUNC", "L_", "GOTO", "IF", "PROBE", "RETURN", "ENDFUNC", "ALLOC")):
                    parts = line.split()
                    row[0] = parts[0]
                    if len(parts) > 1: row[1] = parts[1]
                    if len(parts) > 2: row[2] = " ".join(parts[2:])
                else:
                    row[0] = line

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

    def highlight_instruction(self, node):
        """Highlighter for debugging: finds the closest line matching the node and marks it."""
        if not node: return
        
        lineno = getattr(node, 'lineno', None)
        if not lineno: return

        # Get the name of the operation (e.g., 'Assignment', 'BinOp')
        cls_name = node.__class__.__name__.upper()
        
        # We try to find a line in the text area that looks like this node
        self.text_area.tag_remove("debug", "1.0", "end")
        
        content = self.text_area.get("1.0", "end")
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Very basic heuristic: if the line contains a keyword from the instruction
            # Or if the RESULT column matches the target name
            target_name = getattr(node, 'name', getattr(node, 'target', None))
            if isinstance(target_name, str) and target_name in line:
                start_index = f"{i+1}.0"
                end_index = f"{i+1}.end"
                self.text_area.tag_add("debug", start_index, end_index)
                self.text_area.tag_config("debug", background="#1e3a5f", foreground="#ffffff")
                self.text_area.see(start_index)
                break

    def _write(self, content):
        self.text_area.configure(state="normal")
        self.text_area.insert("1.0", content)
        self.text_area.configure(state="disabled")

    def _clear(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.configure(state="disabled")