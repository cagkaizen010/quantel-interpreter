import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import customtkinter as ctk

class FileExplorerPanel(ctk.CTkFrame):
    def __init__(self, parent, on_file_select, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_file_select = on_file_select
        self.root_path = os.getcwd()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.label_frame.grid(row=0, column=0, pady=(5, 2), sticky="ew")
        self.label_frame.columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self.label_frame, text="EXPLORER", font=ctk.CTkFont(size=11, weight="bold"))
        self.label.grid(row=0, column=0, padx=10, sticky="w")

        # Context Menu
        self.menu = tk.Menu(self, tearoff=0, bg="#333333", fg="white", activebackground="#1f538d")
        self.menu.add_command(label="New File", command=self.new_file)
        self.menu.add_command(label="New Folder", command=self.new_folder)
        self.menu.add_separator()
        self.menu.add_command(label="Move to...", command=self.move_item)
        self.menu.add_command(label="Rename", command=self.rename_item)
        self.menu.add_command(label="Delete", command=self.delete_item)
        self.menu.add_separator()
        self.menu.add_command(label="Refresh", command=self.refresh_tree)

        # Treeview Styling
        style = ttk.Style()
        style.configure("Treeview", background="#2b2b2b", foreground="#DCDCDC", fieldbackground="#2b2b2b", borderwidth=0, font=("Segoe UI", 10))
        style.map("Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 5))
        
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-2>", self._show_context_menu)
        self.tree.bind("<Button-3>", self._show_context_menu)
        
        self.refresh_tree()

    def set_project_root(self, path):
        if os.path.isdir(path):
            self.root_path = path
            self.refresh_tree()

    def get_open_folders(self):
        """Returns a set of absolute paths for folders currently expanded in the tree."""
        open_paths = set()
        def traverse(node):
            if self.tree.item(node, "open"):
                path = self.tree.item(node, "values")[0]
                open_paths.add(path)
            for child in self.tree.get_children(node):
                traverse(child)
        
        for root_node in self.tree.get_children(""):
            traverse(root_node)
        return open_paths

    def refresh_tree(self):
        # 1. Save state
        open_folders = self.get_open_folders()
        
        # 2. Rebuild
        self.tree.delete(*self.tree.get_children())
        self._populate_node("", self.root_path, open_folders)

    def _populate_node(self, parent, path, open_folders=None):
        try:
            items = sorted(os.listdir(path))
            for item in items:
                if item.startswith('.') or item == "__pycache__": continue
                abspath = os.path.join(path, item)
                is_dir = os.path.isdir(abspath)
                
                # Restore emojis and remove the custom arrow from the text
                if is_dir:
                    text = f"📁 {item}"
                else:
                    text = f"📄 {item}"
                
                # Should this node be open?
                is_open = False
                if open_folders and abspath in open_folders:
                    is_open = True
                
                node = self.tree.insert(parent, "end", text=text, open=is_open, values=(abspath,))
                if is_dir:
                    self._populate_node(node, abspath, open_folders)
        except Exception: pass

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
        self.menu.post(event.x_root, event.y_root)

    def get_selected_path(self):
        selected = self.tree.selection()
        if selected:
            return self.tree.item(selected[0], "values")[0]
        return self.root_path

    def new_file(self):
        target = self.get_selected_path()
        if os.path.isfile(target): target = os.path.dirname(target)
        
        name = simpledialog.askstring("New File", "Enter file name:", initialvalue="untitled.qtl")
        if name:
            path = os.path.join(target, name)
            if not os.path.exists(path):
                with open(path, 'w') as f: f.write("// New Quantel File\n")
                self.refresh_tree()
                # Open immediately
                self.on_file_select(path)
            else:
                messagebox.showerror("Error", "File already exists!")

    def new_folder(self):
        target = self.get_selected_path()
        if os.path.isfile(target): target = os.path.dirname(target)
        
        name = simpledialog.askstring("New Folder", "Enter folder name:")
        if name:
            path = os.path.join(target, name)
            os.makedirs(path, exist_ok=True)
            self.refresh_tree()

    def rename_item(self):
        old_path = self.get_selected_path()
        if old_path == self.root_path: return
        
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=os.path.basename(old_path))
        if new_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
                self.refresh_tree()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def move_item(self):
        src_path = self.get_selected_path()
        if src_path == self.root_path: return
        
        dest_dir = filedialog.askdirectory(title="Select Destination Folder", initialdir=self.root_path)
        if dest_dir:
            try:
                shutil.move(src_path, dest_dir)
                self.refresh_tree()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def delete_item(self):
        path = self.get_selected_path()
        if path == self.root_path: return
        
        if messagebox.askyesno("Delete", f"Permanently delete {os.path.basename(path)}?"):
            try:
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
                self.refresh_tree()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _on_double_click(self, event):
        item = self.tree.selection()
        if not item: return
        abspath = self.tree.item(item[0], "values")[0]
        if os.path.isfile(abspath):
            self.on_file_select(abspath)
