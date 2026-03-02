import sys, os

# add backend services path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_services = os.path.join(project_root, "backend", "services")
sys.path.insert(0, backend_services)

from test_phase9_complete import demo_polymarket, demo_smart_donations, demo_link_security

if __name__ == "__main__":
    # reset databases to ensure clean run
    for db in ["polymarket.db", "smart_donations.db", "link_security.db"]:
        try:
            os.remove(os.path.join(project_root, db))
            log.info(f"Removed existing {db}")
        except FileNotFoundError:
            pass
    
    log.info("Running polymarket demo...")
    try:
        demo_polymarket()
    except Exception as e:
        log.info(f"Polymarket demo failed: {e}")
    
    log.info("Running smart donations demo...")
    try:
        demo_smart_donations()
    except Exception as e:
        log.info(f"Smart donations demo failed: {e}")
    
    log.info("Running link security demo...")
    try:
        demo_link_security()
    except Exception as e:
        log.info(f"Link security demo failed: {e}")

    log.info("\nAll demos completed.")
