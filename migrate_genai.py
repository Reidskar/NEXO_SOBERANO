import os

root = r"c:\Users\Admn\Desktop\NEXO_SOBERANO"
skip_dirs = ['camilo_el_bkn', 'camilo_extract', 'backend_legacy_dup', 'nexo_backend', '.venv', 'node_modules', '__pycache__']

for path, subdirs, files in os.walk(root):
    subdirs[:] = [d for d in subdirs if not any(skip in os.path.join(path, d) for skip in skip_dirs)]
    for name in files:
        if name.endswith('.py'):
            filepath = os.path.join(path, name)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'from google import genai' in content:
                    new_content = content.replace('from google import genai', 'from google import genai')
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Migrated import in: {filepath}")
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
