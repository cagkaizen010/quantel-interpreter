import customtkinter as ctk
from tabulate import tabulate

class StackMapPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label = ctk.CTkLabel(self, text="Stack (Global Variables)", font=ctk.CTkFont(size=12, weight="bold"))
        self.label.grid(row=0, column=0, pady=(5, 2), sticky="ew")

        self.text_area = ctk.CTkTextbox(self, font=("Courier New", 12), wrap="none")
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        # Make read-only but copyable
        self.text_area.bind("<Key>", lambda e: "break")

    def update_map(self, interpreter):
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        
        env_data = []
        for name, val in interpreter.global_env.items():
            type_info = interpreter.global_types.get(name)
            is_ptr = False
            dtype = type(val).__name__

            if type_info:
                if len(type_info) == 3: dtype, shape, is_ptr = type_info
                else: dtype, shape = type_info

            val_display = val
            val_type = f"*{dtype}" if is_ptr else dtype
            
            if is_ptr and isinstance(val, int) and 0 <= val < interpreter.heap.max_size:
                val_display = f"-> @{val:02}"

            env_data.append([name, val_type, val_display])

        output = tabulate(env_data, headers=["NAME", "TYPE", "VALUE"], tablefmt="github")
        self.text_area.insert("1.0", output)
        self.text_area.configure(state="normal") # Keep normal for selection but blocked by bind

class HeapMapPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label = ctk.CTkLabel(self, text="Heap Memory Map", font=ctk.CTkFont(size=12, weight="bold"))
        self.label.grid(row=0, column=0, pady=(5, 2), sticky="ew")

        self.text_area = ctk.CTkTextbox(self, font=("Courier New", 12), wrap="none")
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self.text_area.bind("<Key>", lambda e: "break")

    def update_map(self, interpreter):
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        
        heap_data = []
        for addr in range(interpreter.heap.max_size):
            if addr in interpreter.heap.memory:
                content = interpreter.heap.memory[addr]
                status = "ALLOCATED"
            else:
                content = "---"
                status = "[ FREE ]"
            heap_data.append([f"@{addr:02}", status, content])

        output = tabulate(heap_data, headers=["ADDR", "STATUS", "DATA"], tablefmt="github")
        self.text_area.insert("1.0", output)
