import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def run_admin_sql():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in .env")
        return

    print(f"Connecting to database...")
    conn = await asyncpg.connect(db_url)
    
    try:
        # 1. Crear tabla alerts
        print("Creating public.alerts table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS public.alerts (
                id uuid primary key default gen_random_uuid(),
                level text,
                source text,
                title text,
                body text,
                meta jsonb,
                created_at timestamptz default now()
            );
        """)

        # 2. Habilitar RLS en nexo_documentos
        print("Enabling RLS on public.nexo_documentos...")
        await conn.execute("ALTER TABLE public.nexo_documentos ENABLE ROW LEVEL SECURITY;")

        # 3. Crear políticas RLS para nexo_documentos
        print("Creating RLS policies for nexo_documentos...")
        await conn.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE tablename = 'nexo_documentos' AND policyname = 'Allow Select for Authenticated'
                ) THEN
                    CREATE POLICY "Allow Select for Authenticated" ON public.nexo_documentos
                    FOR SELECT TO authenticated USING (true);
                END IF;
            END $$;
        """)

        # 4. Crear índice HNSW para embeddings
        print("Creating HNSW index on nexo_documentos(embedding)...")
        # Nota: Esto puede tardar. Se asume que la extensión vector ya existe.
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS nexo_documentos_embedding_idx 
            ON public.nexo_documentos USING hnsw (embedding vector_cosine_ops);
        """)

        # 5. RLS para alerts
        print("Configuring RLS for public.alerts...")
        await conn.execute("ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;")
        await conn.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE tablename = 'alerts' AND policyname = 'Allow Insert for Authenticated'
                ) THEN
                    CREATE POLICY "Allow Insert for Authenticated" ON public.alerts
                    FOR INSERT TO authenticated WITH CHECK (true);
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE tablename = 'alerts' AND policyname = 'Allow Select for Authenticated'
                ) THEN
                    CREATE POLICY "Allow Select for Authenticated" ON public.alerts
                    FOR SELECT TO authenticated USING (true);
                END IF;
            END $$;
        """)

        print("✅ Database administration tasks completed successfully.")
        
    except Exception as e:
        print(f"❌ Error executing SQL: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_admin_sql())
