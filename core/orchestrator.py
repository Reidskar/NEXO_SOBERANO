"""Central controller that coordinates connectors, ingestion, vectorization,
and cost/priority logic.

This module represents the core engine of NEXO Soberano. It should:

* Accept high-level commands (scan, sync, analyze, query).  
* Enforce daily limits, cost budgets, and scheduling.  
* Dispatch work to workers (ingestor, vectorizer, connectors).  
* Maintain a lightweight state (e.g. quotas, last-run times).  
* Expose simple API for CLI or future UI to control.

"""
from datetime import datetime, timedelta
import logging

# example quota definitions (could be loaded from config)
DAILY_IMAGE_LIMIT = 200
DAILY_VIDEO_LIMIT = 60

class Orchestrator:
    def __init__(self):
        self.logger = logging.getLogger("Orchestrator")
        from typing import Any
        # persistent state could live in a small sqlite table or json file
        self.state: dict[str, Any] = {
            "last_run": None,
            "images_processed": 0,
            "videos_processed": 0,
            "costs": 0.0,
        }

    def load_state(self):
        """implement loading from disk"""
        import json
        from pathlib import Path
        path = Path("orchestrator_state.json")
        if path.exists():
            try:
                self.state = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                self.logger.error(f"Error loading state: {e}")

    def save_state(self):
        """implement persistence"""
        import json
        from pathlib import Path
        try:
            Path("orchestrator_state.json").write_text(json.dumps(self.state, indent=4), encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def can_process(self, media_type: str) -> bool:
        """Check daily quota before scheduling a new task."""
        today = datetime.now().date().isoformat()
        # reset daily counters if last_run is not today
        if self.state.get("last_run") != today:
            self.state["last_run"] = today
            self.state["images_processed"] = 0
            self.state["videos_processed"] = 0
            self.save_state()
            
        if media_type == "image":
            return int(self.state.get("images_processed") or 0) < DAILY_IMAGE_LIMIT
        elif media_type == "video":
            return int(self.state.get("videos_processed") or 0) < DAILY_VIDEO_LIMIT
        return True

    def schedule_ingest(self):
        """Kick off ingestion worker if quotas allow."""
        if self.can_process("video"):
            self.logger.info("Ingestion task scheduled.")
            self.state["videos_processed"] = int(self.state.get("videos_processed") or 0) + 1
            self.save_state()
        else:
            self.logger.warning("Quota reached for video ingestion.")

    def schedule_vectorize(self):
        """Schedule vectorization process."""
        self.logger.info("Vectorization task scheduled.")
        self.save_state()

    def report_cost(self, amount: float):
        self.state["costs"] = float(self.state.get("costs") or 0.0) + amount
        self.save_state()

    # more orchestration helpers to come


if __name__ == "__main__":
    orch = Orchestrator()
    orch.load_state()
    orch.schedule_ingest()
    orch.schedule_vectorize()
    orch.logger.info("Orchestrator executed")
