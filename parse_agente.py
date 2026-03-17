import ast

path = r"c:\Users\Admn\Desktop\NEXO_SOBERANO\backend\routes\agente.py"
with open(path, "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)

for node in ast.iter_child_nodes(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        is_endpoint = False
        route = ""
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, 'attr', '') in ['get', 'post', 'put', 'delete']:
                is_endpoint = True
                if dec.args and isinstance(dec.args[0], ast.Constant):
                    route = dec.args[0].value
        
        start = node.lineno
        if node.decorator_list:
            start = node.decorator_list[0].lineno
        end = node.end_lineno
        
        if is_endpoint:
            log.info(f"ENDPOINT: {route} -> func: {node.name} (Lines: {start}-{end})")
        else:
            log.info(f"HELPER: func: {node.name} (Lines: {start}-{end})")
