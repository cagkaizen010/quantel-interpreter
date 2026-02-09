# gui/utils.py

def render_ast_tree(node, prefix="", is_last=True):
    """
    Recursively converts a Python object (AST) into a pretty ASCII tree string.
    """
    lines = []
    connector = "└── " if is_last else "├── "

    if isinstance(node, (str, int, float, bool, type(None))):
        return f"{prefix}{connector}{repr(node)}"

    if isinstance(node, list):
        if not node:
            return f"{prefix}{connector}[]"
        lines.append(f"{prefix}{connector}[]")
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, item in enumerate(node):
            lines.append(render_ast_tree(item, new_prefix, i == len(node) - 1))
        return "\n".join(lines)

    node_name = node.__class__.__name__
    lines.append(f"{prefix}{connector}{node_name}")
    new_prefix = prefix + ("    " if is_last else "│   ")

    if hasattr(node, "__dict__"):
        attrs = {k: v for k, v in node.__dict__.items() if not k.startswith('_')}
        sorted_attrs = sorted(attrs.items())
        for i, (key, val) in enumerate(sorted_attrs):
            lines.append(render_ast_tree(val, new_prefix + ("└── " if i == len(sorted_attrs) - 1 else "├── "),
                                         i == len(sorted_attrs) - 1))

    return "\n".join(lines)