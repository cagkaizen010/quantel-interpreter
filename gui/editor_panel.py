import customtkinter as ctk
import tkinter as tk
from chlorophyll import CodeView
from gui.highlighter import QuantelHighlighter


class EditorPanel(ctk.CTkFrame):
    def __init__(self, parent, on_word_click=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_word_click = on_word_click

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Main Code View
        self.code_view = CodeView(
            self,
            lexer=QuantelHighlighter,
            font=("Consolas", 14),
            color_scheme="monokai",
            undo=True
        )
        self.code_view.grid(row=0, column=0, sticky="nsew")
        self.textbox = getattr(self.code_view, '_code_view', self.code_view)

        # 2. Configure Visual Tags
        self.textbox.tag_config("error", background="#880000", foreground="white")
        self.textbox.tag_config("jump_highlight", background="#4a4a30")
        self.textbox.tag_config("search_match", background="#FFCC00", foreground="black")

        # 3. Minimalist Search Bar UI
        self.search_frame = ctk.CTkFrame(self, fg_color="#333333", corner_radius=5, height=35)
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search...",
            width=150,
            height=25,
            border_width=0,
            fg_color="#222222"
        )
        self.search_entry.pack(side="left", padx=5, pady=5)

        self.close_btn = ctk.CTkButton(
            self.search_frame, text="×", width=20, height=20,
            fg_color="transparent", hover_color="#555555",
            command=self.hide_search
        )
        self.close_btn.pack(side="right", padx=5)

        # 4. Bindings
        self.textbox.bind("<Command-Button-1>", self._handle_jump_click)
        self.textbox.bind("<Control-Button-1>", self._handle_jump_click)
        self.search_entry.bind("<Return>", lambda e: self.search_text(self.search_entry.get()))
        self.search_entry.bind("<Escape>", lambda e: self.hide_search())

    # --- JUMP LOGIC ---
    def _handle_jump_click(self, event):
        """Finds the word under the cursor and triggers the IDE jump logic."""
        index = self.textbox.index(f"@{event.x},{event.y}")
        word = self.textbox.get(f"{index} wordstart", f"{index} wordend").strip()
        if word and self.on_word_click:
            self.on_word_click(word)

    def highlight_line(self, line_number):
        """THE MISSING METHOD: Highlights the line and scrolls to it."""
        self.textbox.tag_remove("jump_highlight", "1.0", "end")
        index = f"{line_number}.0"
        self.textbox.tag_add("jump_highlight", f"{index} linestart", f"{index} lineend")
        self.textbox.see(index)

    # --- SEARCH LOGIC ---
    def show_search(self):
        self.search_frame.place(x=50, y=10)
        self.search_entry.focus_set()

    def hide_search(self):
        self.search_frame.place_forget()
        self.textbox.tag_remove("search_match", "1.0", "end")
        self.textbox.focus_set()

    def search_text(self, query):
        self.textbox.tag_remove("search_match", "1.0", "end")
        if not query: return

        start_pos = "1.0"
        first_match = None
        while True:
            start_pos = self.textbox.search(query, start_pos, stopindex="end", nocase=True)
            if not start_pos: break
            if not first_match: first_match = start_pos
            end_pos = f"{start_pos}+{len(query)}c"
            self.textbox.tag_add("search_match", start_pos, end_pos)
            start_pos = end_pos

        if first_match:
            self.textbox.see(first_match)

    # --- STANDARD HELPERS ---
    def get_text(self):
        return self.code_view.get("1.0", "end-1c")

    def set_text(self, text):
        self.code_view.delete("1.0", "end")
        self.code_view.insert("1.0", text)

    def clear_indicators(self):
        """Clears errors and jumps, but keeps search matches if bar is open."""
        self.textbox.tag_remove("error", "1.0", "end")
        self.textbox.tag_remove("jump_highlight", "1.0", "end")

    def mark_error(self, line):
        start, end = f"{line}.0", f"{line}.end"
        self.textbox.tag_add("error", start, end)
        self.textbox.see(start)

    def toggle_comment(self, event=None):
        """Simple toggle for // comments."""
        try:
            # 1. Get Line Range
            try:
                start_line = int(self.textbox.index("sel.first").split('.')[0])
                end_line = int(self.textbox.index("sel.last").split('.')[0])
            except tk.TclError:
                start_line = end_line = int(self.textbox.index("insert").split('.')[0])

            # 2. Decide Action (Comment if any line is uncommented)
            do_comment = False
            for i in range(start_line, end_line + 1):
                text = self.textbox.get(f"{i}.0", f"{i}.end").strip()
                if text and not text.startswith("//"):
                    do_comment = True
                    break

            # 3. Apply
            for i in range(start_line, end_line + 1):
                line_text = self.textbox.get(f"{i}.0", f"{i}.end")
                if do_comment:
                    self.textbox.insert(f"{i}.0", "// ")
                elif line_text.strip().startswith("//"):
                    start_idx = line_text.find("//")
                    # Delete 3 chars if "// ", else 2 chars for "//"
                    count = 3 if line_text[start_idx:start_idx+3] == "// " else 2
                    self.textbox.delete(f"{i}.{start_idx}", f"{i}.{start_idx+count}")

            # 4. Keep selection
            self.textbox.tag_add("sel", f"{start_line}.0", f"{end_line}.end")
            return "break"
        except:
            return "break"