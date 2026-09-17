"""Shared test setup; production code is never modified by the tests."""
import sys
from pathlib import Path


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))
    
from search_engine.factory import make_components, make_engine



def populated_engine():
    engine = make_engine()
    engine.add("doc-1", "python search search engine")
    engine.add("doc-2", "python web framework")
    engine.add("doc-3", "distributed search engine")
    return engine
