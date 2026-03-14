import sqlite3

c = sqlite3.connect('NEXO_SOBERANO/base_sqlite/boveda.db')
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    cols = c.execute(f"PRAGMA table_info({t[0]})").fetchall()
    log.info(t[0], [col[1] for col in cols])
c.close()
