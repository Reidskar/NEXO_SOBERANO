import os
import psycopg2
from dotenv import load_dotenv

def test_conn():
    load_dotenv()
    
    # 1. Pooler (el que dio el agente)
    url1 = "postgresql://postgres.rokxchapzhgshrvmuuus:Yosoloyo%2312@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    # 2. Directo (el que suele funcionar siempre)
    url2 = "postgresql://postgres:Yosoloyo%2312@db.rokxchapzhgshrvmuuus.supabase.co:5432/postgres"
    
    urls = [
        ("Pooler (Session)", url1),
        ("Direct Connection", url2)
    ]
    
    for label, url in urls:
        print(f"--- Probando: {label} ---")
        try:
            conn = psycopg2.connect(url)
            print(f"Connection SUCCESS for {label}!")
            conn.close()
            # Si tiene éxito, actualizamos el .env
            update_env(url)
            print(f"Updated .env with working {label} URL.")
            return True
        except Exception as e:
            print(f"Connection FAILED for {label}: {e}")
    return False

def update_env(new_url):
    env_path = ".env"
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={new_url}\n")
        else:
            new_lines.append(line)
            
    with open(env_path, 'w') as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    if test_conn():
        print("Done.")
    else:
        print("All connection attempts failed.")
        exit(1)
