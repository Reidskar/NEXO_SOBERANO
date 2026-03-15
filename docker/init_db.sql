-- Este archivo es referenciado por docker-compose.yml
-- PostgreSQL ya crea el usuario y la BD via variables de entorno,
-- este script solo garantiza los permisos.
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nexo_soberano') THEN
      PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE nexo_soberano');
   END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE nexo_soberano TO nexo;
