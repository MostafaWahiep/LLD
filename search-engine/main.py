from search_engine import SearchEngine
from query_parser import Parser
from text_analyzer import TextAnalyzer
from index import InvertedIndex
from evaluator import QueryEvaluator


def make_engine():
    index = InvertedIndex()
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


if __name__ == "__main__":
    main()
