import ast
import os

def debug_ast_parsing():
    file_path = r"C:\HB TRACK\Hb Track - Backend\tests\training\invariants\test_inv_train_001_focus_sum_constraint.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                print(f"Found class: {node.name}")
                for item in node.body:
                    if isinstance(item, ast.AsyncFunctionDef) or isinstance(item, ast.FunctionDef):
                        print(f"  Method: {item.name}")
                        if item.name.startswith('test_'):
                            print(f"    TEST METHOD FOUND: {item.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_ast_parsing()