import sys
from pathlib import Path


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from search_engine.factory import make_engine, open_engine


def main():
    engine = make_engine()
    engine.add("doc-1", "python search search engine")
    engine.add("doc-2", "python web framework")
    engine.add("doc-3", "distributed search engine")

    print(engine.search("search"))
    print(engine.query('AND("search", NOT("python"))'))

    for result in engine.ranked_search("python search"):
        print(result)

    engine.flush()

    engine.add("doc-4", "searching searchable content")

    print(engine.prefix_search("search"))
    print(engine.prefix_search("sear"))
    print(engine.prefix_search("content"))

    print(engine.phrase_search("distributed search"))
    print(engine.phrase_search("distributed engine"))

    engine.delete("doc-3")

    engine.flush()
    engine.merge_segments()

    engine.add("doc-5", "search unrelated search engine")
    print(engine.phrase_search("search engine"))
    print(engine.query('PHRASE("search engine")'))

    engine.flush()
    engine.commit()

def test_main():
    path = Path("/Users/moustafa/Projects/LLD/search-engine/examples")
    engine = open_engine(path)

    print(engine.search("search"))
    print(engine.query('AND("search", NOT("python"))'))

    for result in engine.ranked_search("python search"):
        print(result)

    print(engine.prefix_search("search"))
    print(engine.prefix_search("sear"))
    print(engine.prefix_search("content"))

    print(engine.phrase_search("distributed search"))
    print(engine.phrase_search("distributed engine"))

    print(engine.phrase_search("search engine"))
    print(engine.query('PHRASE("search engine")'))

if __name__ == "__main__":
    main()
