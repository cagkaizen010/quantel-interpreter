# gui/main_menu.py
import tkinter as tk

class MainMenu(tk.Menu):
    def __init__(self, parent_window, commands):
        super().__init__(parent_window)
        self.commands = commands  # Dictionary of callback functions

        # File Menu
        file_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=commands['new'], accelerator="Cmd+N")
        file_menu.add_command(label="Open...", command=commands['open'], accelerator="Cmd+O")
        file_menu.add_command(label="Save", command=commands['save'], accelerator="Cmd+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=parent_window.quit, accelerator="Cmd+Q")

        # Run Menu
        run_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Program", command=commands['run'], accelerator="F5")

        # View Menu
        view_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Memory Map", command=commands['toggle_mem'])
        view_menu.add_command(label="Toggle White Box", command=commands['toggle_tac'])

        # Attach to parent
        parent_window.config(menu=self)