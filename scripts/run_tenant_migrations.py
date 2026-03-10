"""
scripts/run_tenant_migrations.py
==================================
Aplica migraciones Alembic a todos los tenants activos en la DB.

Por qué existe este script:
    `alembic upgrade head` por defecto solo actúa sobre el schema "public".
    Cada tenant vive en su propio schema (tenant_demo, tenant_empresa_abc, ...).
    Este script itera todos los tenants y ejecuta la migración en cada uno.

Cuándo correrlo:
    - Cada vez que crees una nueva revisión de Alembic con cambios de schema
    - Al registrar un tenant nuevo (también llama a create_tenant_schema_and_tables)

Uso:
    # Todos los tenants
    python scripts/run_tenant_migrations.py

    # Solo un tenant específico
    python scripts/run_tenant_migrations.py --tenant demo

    # Solo el schema public (tablas globales: tenants, users, sessions)
    python scripts/run_tenant_migrations.py --public-only

    # Ver qué se ejecutaría sin hacerlo
    python scripts/run_tenant_migrations.py --dry-run
"""

import os
import sys
import subprocess
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://nexo_user:nexo_password@localhost:5432/nexo_db"
)


# ── Helpers ────────────────────────────────────────────────────

def get_active_tenants() -> list[dict]:
    """Obtiene todos los tenants activos desde el schema public."""
    try:
        with psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, slug, name, plan FROM tenants WHERE active = TRUE ORDER BY created_at")
                return [dict(r) for r in cur.fetchall()]
    except psycopg2.errors.UndefinedTable:
        # La tabla tenants aún no existe (primera migración)
        return []
    except Exception as e:
        print(f"⚠️  No se pudo conectar a la DB para obtener tenants: {e}")
        return []


def run_alembic(target_schema: str, dry_run: bool = False) -> bool:
    """
    Ejecuta `alembic upgrade head` con el schema objetivo.

    Returns:
        True si exitoso, False si hubo error.
    """
    env = {**os.environ, "ALEMBIC_TARGET_SCHEMA": target_schema}
    cmd = ["alembic", "upgrade", "head"]

    if dry_run:
        cmd = ["alembic", "upgrade", "head", "--sql"]
        print(f"\n📋 SQL que se ejecutaría en schema '{target_schema}':")
    else:
        print(f"  🔄 Migrando schema: {target_schema} ...", end=" ", flush=True)

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),  # raíz del proyecto
        )

        if result.returncode == 0:
            if dry_run:
                print(result.stdout or "(sin cambios pendientes)")
            else:
                print("✅")
            return True
        else:
            if dry_run:
                print(result.stdout)
            else:
                print("❌")
            if result.stderr:
                print(f"     Error: {result.stderr.strip()}")
            return False

    except FileNotFoundError:
        print("❌")
        print("  Error: 'alembic' no encontrado. ¿Está el .venv activado?")
        print("  Ejecuta: .venv/Scripts/activate  (Windows)")
        print("           source .venv/bin/activate  (Linux/Mac)")
        return False


def ensure_public_schema_first(dry_run: bool = False) -> bool:
    """
    Migra primero el schema public (tablas globales: tenants, users, sessions).
    Debe correr antes que cualquier schema de tenant.
    """
    print("\n[1/2] Schema público (tenants · users · sessions)")
    return run_alembic("public", dry_run=dry_run)


# ── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Aplica migraciones Alembic a todos los tenants de NEXO SOBERANO"
    )
    parser.add_argument(
        "--tenant", "-t",
        help="Slug del tenant específico a migrar (omitir = todos)",
        default=None,
    )
    parser.add_argument(
        "--public-only",
        action="store_true",
        help="Solo migrar el schema public (tablas globales)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar el SQL que se ejecutaría sin aplicar cambios",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  NEXO SOBERANO — Migraciones Alembic Multi-tenant")
    print("=" * 60)

    if args.dry_run:
        print("  Modo DRY-RUN: solo se muestra el SQL, no se ejecuta nada.\n")

    # 1. Schema public siempre primero
    ok = ensure_public_schema_first(dry_run=args.dry_run)
    if not ok and not args.dry_run:
        print("\n❌ Fallo en schema public. Abortando.")
        sys.exit(1)

    if args.public_only:
        print("\n✅ Solo schema public solicitado. Fin.")
        return

    # 2. Obtener tenants
    if args.tenant:
        tenants = [{"slug": args.tenant, "name": args.tenant, "plan": "?"}]
    else:
        tenants = get_active_tenants()

    if not tenants:
        if not args.tenant:
            print("\n  ℹ️  No hay tenants activos en la DB todavía.")
            print("  (Normal en la primera ejecución antes de registrar empresas)")
        return

    print(f"\n[2/2] Schemas de tenants ({len(tenants)} encontrados)")

    exitosos = 0
    fallidos = []

    for tenant in tenants:
        slug   = tenant["slug"]
        name   = tenant.get("name", slug)
        plan   = tenant.get("plan", "?")
        schema = f"tenant_{slug.lower().replace('-', '_').replace(' ', '_')}"

        print(f"  → {name} [{plan}] (schema: {schema})", end="")

        if not args.dry_run:
            print()  # newline antes del ✅/❌ de run_alembic

        ok = run_alembic(schema, dry_run=args.dry_run)

        if ok:
            exitosos += 1
        else:
            fallidos.append(slug)

    # ── Resumen ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Resultado: {exitosos}/{len(tenants)} schemas migrados correctamente")

    if fallidos:
        print(f"  ❌ Fallidos: {', '.join(fallidos)}")
        print("\n  Para reintentar un tenant específico:")
        print(f"    python scripts/run_tenant_migrations.py --tenant {fallidos[0]}")
        sys.exit(1)
    else:
        print("  ✅ Todas las migraciones completadas.")


if __name__ == "__main__":
    main()
