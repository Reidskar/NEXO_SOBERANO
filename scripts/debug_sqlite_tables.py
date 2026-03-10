import sqlite3
import os

def list_tables():
    # El usuario sugiere 'data/'. Probamos también 'NEXO_SOBERANO/base_sqlite/'
    search_paths = ['data', 'NEXO_SOBERANO/base_sqlite', 'base_sqlite', '.']
    db_files = ['boveda.db', 'nexo.db', 'usuarios.db', 'sesiones.db']
    
    for f in db_files:
        found = False
        for folder in search_paths:
            path = os.path.join(folder, f)
            if os.path.exists(path):
                try:
                    conn = sqlite3.connect(path)
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    print(f"{path}: {[t[0] for t in tables]}")
                    conn.close()
                    found = True
                    break
                except Exception as e:
                    print(f"Error reading {path}: {e}")
        if not found:
            print(f"{f}: NOT FOUND")

if __name__ == "__main__":
    list_tables()
