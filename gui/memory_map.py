import customtkinter as ctk
from tabulate import tabulate


class MemoryMapPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label = ctk.CTkLabel(self, text="Live Memory Map (Stack & Heap)", font=ctk.CTkFont(size=14, weight="bold"))
        self.label.grid(row=0, column=0, pady=(10, 5), sticky="ew")

        self.text_area = ctk.CTkTextbox(self, state="disabled", font=("Courier New", 12), wrap="none")
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def update_map(self, interpreter):
        """
        Modified to accept the full interpreter object so we can access
        both environment (Stack) and the separate Heap class.
        """
        self._clear()

        output = ""

        # --- SECTION 1: GLOBAL ENVIRONMENT (The Stack) ---
        env_data = []
        for name, val in interpreter.global_env.items():
            # Get type info if available
            type_info = interpreter.global_types.get(name)
            is_ptr = False
            dtype = type(val).__name__

            if type_info:
                # Format: (dtype, shape, is_pointer)
                if len(type_info) == 3:
                    dtype, shape, is_ptr = type_info
                else:
                    dtype, shape = type_info

            val_display = val
            val_type = dtype

            # If it's explicitly a pointer OR looks like a heap address, format it
            if is_ptr:
                val_type = f"*{dtype}"
                if isinstance(val, int) and 0 <= val < interpreter.heap.max_size:
                    val_display = f"-> @{val:02}"
            elif isinstance(val, int) and 0 <= val < interpreter.heap.max_size and name != 'total_activation':
                # Fallback for heap-like integers that aren't variables we know
                val_type = "PTR (HeapAddr)"
                val_display = f"-> @{val:02}"

            env_data.append([name, val_type, val_display])

        output += "=== GLOBAL VARIABLES (STACK) ===\n"
        output += tabulate(env_data, headers=["NAME", "TYPE", "VALUE"], tablefmt="github")
        output += "\n\n"

        # --- SECTION 2: THE HEAP (Showing the Gaps) ---
        heap_data = []
        # We loop through the full range of the heap to show the EMPTY slots
        for addr in range(interpreter.heap.max_size):
            if addr in interpreter.heap.memory:
                content = interpreter.heap.memory[addr]
                status = "ALLOCATED"
            else:
                content = "---"
                status = "[ FREE ]"

            heap_data.append([f"@{addr:02}", status, content])

        output += "=== HEAP MEMORY MAP ===\n"
        output += tabulate(heap_data, headers=["ADDR", "STATUS", "DATA"], tablefmt="github")

        self._write(output)

    def _write(self, content):
        self.text_area.configure(state="normal")
        self.text_area.insert("0.0", content)
        self.text_area.configure(state="disabled")

    def _clear(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("0.0", "end")
        self.text_area.configure(state="disabled")