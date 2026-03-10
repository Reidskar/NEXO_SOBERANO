#!/usr/bin/env python3
"""
migrate_sqlite_to_postgres.py
==============================
Migra todos los datos existentes de los 7 SQLite
al nuevo PostgreSQL multi-tenant.

Uso:
    python migrate_sqlite_to_postgres.py --tenant-slug demo

Requiere:
    pip install psycopg2-binary sqlalchemy tqdm
"""

import argparse
import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values, RealDictCursor
    from tqdm import tqdm
except ImportError:
    print("❌ Instala dependencias: pip install psycopg2-binary tqdm")
    sys.exit(1)

# ── Configuración ──────────────────────────────────────────────
POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://nexo:nexo_password@localhost:5432/nexo_soberano"
)

# Rutas de los SQLite originales (ajusta si están en otra carpeta)
SQLITE_PATHS = {
    "preferences": "./preferences.db",
    "notifications": "./notifications.db",
    "calendar": "./calendar.db",
    "conversations": "./conversations.db",
    "cost_tracking": "./cost_tracking.db",
    "auth": "./auth.db",
    "omnidiario": "./omnidiario.db",
}


def get_pg_conn():
    return psycopg2.connect(POSTGRES_URL)


def get_sqlite_conn(path: str):
    if not Path(path).exists():
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_tenant_schema(slug: str) -> str:
    return f"tenant_{slug.replace('-', '_')}"


def ensure_tenant_exists(pg_conn, slug: str, name: str = None):
    """Crea el tenant en Postgres si no existe."""
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM tenants WHERE slug = %s", (slug,)
        )
        row = cur.fetchone()
        if row:
            print(f"   ✅ Tenant '{slug}' ya existe (id={row[0]})")
            return row[0]

        cur.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, %s) RETURNING id",
            (slug, name or slug)
        )
        tenant_id = cur.fetchone()[0]

        # Crear schema
        schema = get_tenant_schema(slug)
        cur.execute(f"SELECT create_tenant_schema('{slug}')")
        pg_conn.commit()
        print(f"   ✅ Tenant '{slug}' creado (id={tenant_id}, schema={schema})")
        return tenant_id


def migrate_users(pg_conn, sqlite_auth_path: str, tenant_id: str):
    """Migra usuarios desde auth.db."""
    conn = get_sqlite_conn(sqlite_auth_path)
    if not conn:
        print("   ⚠️  auth.db no encontrado, saltando usuarios")
        return {}

    user_map = {}  # old_id -> new_uuid

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        rows = cur.fetchall()

        if not rows:
            print("   ⚠️  No hay usuarios en auth.db")
            return {}

        print(f"   📦 Migrando {len(rows)} usuarios...")
        with pg_conn.cursor() as pg_cur:
            for row in tqdm(rows, desc="   Usuarios"):
                pg_cur.execute("""
                    INSERT INTO users (tenant_id, email, hashed_password, role, active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
                    RETURNING id
                """, (
                    tenant_id,
                    row["email"],
                    row["hashed_password"],
                    row.get("role", "member"),
                    bool(row.get("active", True)),
                    row.get("created_at", datetime.now().isoformat()),
                ))
                new_id = pg_cur.fetchone()[0]
                user_map[str(row["id"])] = str(new_id)

        pg_conn.commit()
        print(f"   ✅ {len(user_map)} usuarios migrados")
    finally:
        conn.close()

    return user_map


def migrate_conversations(pg_conn, sqlite_path: str, tenant_slug: str, user_map: dict):
    """Migra conversaciones y mensajes."""
    conn = get_sqlite_conn(sqlite_path)
    if not conn:
        print("   ⚠️  conversations.db no encontrado")
        return

    schema = get_tenant_schema(tenant_slug)

    try:
        cur = conn.cursor()

        # Conversaciones
        cur.execute("SELECT * FROM conversations")
        convs = cur.fetchall()
        print(f"   📦 Migrando {len(convs)} conversaciones...")

        conv_map = {}
        with pg_conn.cursor() as pg_cur:
            for conv in tqdm(convs, desc="   Conversaciones"):
                old_user_id = str(conv.get("user_id", ""))
                new_user_id = user_map.get(old_user_id)

                if not new_user_id:
                    continue  # Usuario no migrado, saltar

                pg_cur.execute(f"""
                    INSERT INTO {schema}.conversations (user_id, title, created_at)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (new_user_id, conv.get("title"), conv.get("created_at")))
                conv_map[str(conv["id"])] = str(pg_cur.fetchone()[0])

        # Mensajes
        cur.execute("SELECT * FROM messages ORDER BY timestamp ASC")
        messages = cur.fetchall()
        print(f"   📦 Migrando {len(messages)} mensajes...")

        with pg_conn.cursor() as pg_cur:
            batch = []
            for msg in tqdm(messages, desc="   Mensajes"):
                new_conv_id = conv_map.get(str(msg.get("conversation_id", "")))
                old_user_id = str(msg.get("user_id", ""))
                new_user_id = user_map.get(old_user_id)

                if not new_conv_id or not new_user_id:
                    continue

                batch.append((
                    new_conv_id, new_user_id,
                    msg["role"], msg["content"],
                    msg.get("timestamp"),
                ))

                if len(batch) >= 500:
                    execute_values(pg_cur, f"""
                        INSERT INTO {schema}.messages
                        (conversation_id, user_id, role, content, created_at)
                        VALUES %s
                    """, batch)
                    batch = []

            if batch:
                execute_values(pg_cur, f"""
                    INSERT INTO {schema}.messages
                    (conversation_id, user_id, role, content, created_at)
                    VALUES %s
                """, batch)

        pg_conn.commit()
        print(f"   ✅ Conversaciones y mensajes migrados")
    finally:
        conn.close()


def migrate_costs(pg_conn, sqlite_path: str, tenant_slug: str):
    """Migra historial de costos."""
    conn = get_sqlite_conn(sqlite_path)
    if not conn:
        print("   ⚠️  cost_tracking.db no encontrado")
        return

    schema = get_tenant_schema(tenant_slug)

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM costos_api")
        rows = cur.fetchall()
        print(f"   📦 Migrando {len(rows)} registros de costos...")

        with pg_conn.cursor() as pg_cur:
            batch = []
            for row in tqdm(rows, desc="   Costos"):
                batch.append((
                    row["modelo"],
                    row.get("tokens_in", 0),
                    row.get("tokens_out", 0),
                    row.get("operacion", "migrado"),
                    row.get("fecha"),
                ))
                if len(batch) >= 1000:
                    execute_values(pg_cur, f"""
                        INSERT INTO {schema}.api_costs
                        (model, tokens_in, tokens_out, operation, fecha)
                        VALUES %s
                    """, batch)
                    batch = []

            if batch:
                execute_values(pg_cur, f"""
                    INSERT INTO {schema}.api_costs
                    (model, tokens_in, tokens_out, operation, fecha)
                    VALUES %s
                """, batch)

        pg_conn.commit()
        print(f"   ✅ Costos migrados")
    finally:
        conn.close()


def migrate_preferences(pg_conn, sqlite_path: str, tenant_slug: str, user_map: dict):
    """Migra perfiles cognitivos."""
    conn = get_sqlite_conn(sqlite_path)
    if not conn:
        print("   ⚠️  preferences.db no encontrado")
        return

    schema = get_tenant_schema(tenant_slug)

    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM cognitive_profile")
        except sqlite3.OperationalError:
            print("   ⚠️  Tabla cognitive_profile no existe en preferences.db")
            return

        rows = cur.fetchall()
        print(f"   📦 Migrando {len(rows)} perfiles cognitivos...")

        with pg_conn.cursor() as pg_cur:
            for row in tqdm(rows, desc="   Perfiles"):
                old_user_id = str(row.get("user_id", ""))
                new_user_id = user_map.get(old_user_id)
                if not new_user_id:
                    continue

                pg_cur.execute(f"""
                    INSERT INTO {schema}.cognitive_profiles
                    (user_id, learning_style, vocabulary, content_length, tone,
                     presentation, sequence, depth_level, example_mode, format_pref)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        learning_style = EXCLUDED.learning_style,
                        updated_at = NOW()
                """, (
                    new_user_id,
                    row.get("learning_style", "reading"),
                    row.get("vocabulary", "simple"),
                    row.get("content_length", "200w"),
                    row.get("tone", "casual"),
                    row.get("presentation", "bullet"),
                    row.get("sequence", "linear"),
                    row.get("depth_level", "surface"),
                    row.get("example_mode", "practical"),
                    row.get("format", "text"),
                ))

        pg_conn.commit()
        print(f"   ✅ Perfiles cognitivos migrados")
    finally:
        conn.close()


def run_migration(tenant_slug: str, tenant_name: str = None, sqlite_dir: str = "."):
    """Ejecuta la migración completa."""
    print(f"\n{'='*55}")
    print(f"  MIGRACIÓN NEXO SOBERANO → PostgreSQL")
    print(f"  Tenant: {tenant_slug}")
    print(f"  Directorio SQLite: {sqlite_dir}")
    print(f"{'='*55}\n")

    # Actualizar rutas según directorio indicado
    paths = {k: os.path.join(sqlite_dir, Path(v).name) for k, v in SQLITE_PATHS.items()}

    pg_conn = get_pg_conn()
    print("✅ Conectado a PostgreSQL\n")

    try:
        # 1. Asegurar tenant
        print("── Paso 1/5: Configurando tenant...")
        tenant_id = ensure_tenant_exists(pg_conn, tenant_slug, tenant_name)

        # 2. Usuarios
        print("\n── Paso 2/5: Migrando usuarios...")
        user_map = migrate_users(pg_conn, paths["auth"], tenant_id)

        # 3. Conversaciones y mensajes
        print("\n── Paso 3/5: Migrando conversaciones...")
        migrate_conversations(pg_conn, paths["conversations"], tenant_slug, user_map)

        # 4. Costos
        print("\n── Paso 4/5: Migrando historial de costos...")
        migrate_costs(pg_conn, paths["cost_tracking"], tenant_slug)

        # 5. Preferencias cognitivas
        print("\n── Paso 5/5: Migrando perfiles cognitivos...")
        migrate_preferences(pg_conn, paths["preferences"], tenant_slug, user_map)

        print(f"\n{'='*55}")
        print(f"  ✅ MIGRACIÓN COMPLETADA para tenant '{tenant_slug}'")
        print(f"  Schema: tenant_{tenant_slug.replace('-','_')}")
        print(f"{'='*55}\n")

    except Exception as e:
        pg_conn.rollback()
        print(f"\n❌ ERROR en migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        pg_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrar SQLite → PostgreSQL")
    parser.add_argument("--tenant-slug", required=True, help="Slug del tenant (ej: mi-empresa)")
    parser.add_argument("--tenant-name", help="Nombre del tenant")
    parser.add_argument("--sqlite-dir", default=".", help="Directorio donde están los .db")
    args = parser.parse_args()

    run_migration(args.tenant_slug, args.tenant_name, args.sqlite_dir)
