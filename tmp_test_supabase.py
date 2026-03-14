import sys
try:
    from supabase import create_client
    log.info("SUCCESS: create_client imported from supabase")
except ImportError as e:
    log.info(f"FAILURE: ImportError: {e}")
except Exception as e:
    log.info(f"FAILURE: An unexpected error occurred: {e}")

log.info(f"Python version: {sys.version}")
log.info(f"Python path: {sys.path}")
