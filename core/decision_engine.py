"""Decision engine that prioritizes content and determines workflows.

Responsibilities include:

* Ranking new files based on category, impact, age, or other metadata.
* Deciding what to analyze, what to promote to clipping, what to archive.
* Applying rules to minimize cost (skip large low-impact docs, etc.).
* Storing a small knowledge base of past decisions to improve over time.

"""
from typing import List, Dict

class DecisionEngine:
    def __init__(self):
        # state could be persisted in SQLite or a simple JSON
        self.history = []

    def rank_documents(self, docs: List[Dict]) -> List[Dict]:
        """Return documents sorted by priority.  

        Each doc is expected to have fields like 'categoria', 'impacto',
        'fecha_ingesta', etc. This is a stub implementation.
        """
        # simple example: highest impacto first
        return sorted(docs, key=lambda d: d.get("impacto", "").lower())

    def should_vectorize(self, doc: Dict) -> bool:
        """Determine if we should send this document to vector memory."""
        # placeholder: always true
        return True

    def record_decision(self, doc: Dict, decision: str):
        self.history.append({"doc": doc, "decision": decision})
        # TODO: persist history

    # more methods for prioritization, reuse, clipping, etc.

if __name__ == "__main__":
    engine = DecisionEngine()
    sample = [{"impacto": "Alto", "categoria": "Rusia"}, {"impacto": "Bajo"}]
    log.info(engine.rank_documents(sample))
