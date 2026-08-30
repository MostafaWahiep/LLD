from search_engine import SearchEngine
from query_parser import Parser
from text_analyzer import TextAnalyzer
from index import InvertedIndex
from evaluator import QueryEvaluator
from trie_index import TrieIndex


def make_engine():
    index = InvertedIndex(TrieIndex())
    analyzer = TextAnalyzer()
    evaluator = QueryEvaluator(index, analyzer)
    return SearchEngine(Parser(), analyzer, index, evaluator)


def main():
    engine = make_engine()
    engine.add("doc-1", "python search search engine")
    engine.add("doc-2", "python web framework")
    engine.add("doc-3", "distributed search engine")

    print(engine.search("search"))
    print(engine.query('AND("search", NOT("python"))'))

    for result in engine.ranked_search("python search"):
        print(result)

    engine.add("doc-4", "searching searchable content")

    print(engine.prefix_search("search"))
    print(engine.prefix_search("sear"))
    print(engine.prefix_search("content"))

    print(engine.phrase_search("distributed search"))
    print(engine.phrase_search("distributed engine"))

    engine.add("doc-5", "search unrelated search engine")
    print(engine.phrase_search("search engine"))
    print(engine.query('PHRASE("search engine")'))


if __name__ == "__main__":
    main()
