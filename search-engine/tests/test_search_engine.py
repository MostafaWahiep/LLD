import math
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluator import QueryEvaluator
from index import InvertedIndex
from query_parser import Parser
from search_engine import SearchEngine
from text_analyzer import TextAnalyzer


def make_engine() -> SearchEngine:
    index = InvertedIndex()
    analyzer = TextAnalyzer()
    evaluator = QueryEvaluator(index, analyzer)
    return SearchEngine(Parser(), analyzer, index, evaluator)


class SearchEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine()
        self.engine.add("doc-1", "python search search engine")
        self.engine.add("doc-2", "python web framework")
        self.engine.add("doc-3", "distributed search engine")

    def test_term_search_is_normalized_and_sorted(self):
        self.assertEqual(["doc-1", "doc-2"], self.engine.search("PYTHON!"))

    def test_boolean_queries(self):
        self.assertEqual(
            ["doc-1"],
            self.engine.query('AND("python", "search")'),
        )
        self.assertEqual(
            ["doc-3"],
            self.engine.query('AND("search", NOT("python"))'),
        )

    def test_ranked_search_orders_by_tf_idf(self):
        results = self.engine.ranked_search("python search")

        self.assertEqual(
            ["doc-1", "doc-2", "doc-3"],
            [result.document_id for result in results],
        )
        self.assertGreater(results[0].score, results[1].score)
        self.assertTrue(math.isclose(results[1].score, results[2].score))

    def test_ranked_search_limit(self):
        results = self.engine.ranked_search("python search", limit=1)

        self.assertEqual(["doc-1"], [result.document_id for result in results])

    def test_missing_and_empty_ranked_queries(self):
        self.assertEqual([], self.engine.ranked_search("missing"))
        self.assertEqual([], self.engine.ranked_search(""))

    def test_rejects_negative_limit(self):
        with self.assertRaises(ValueError):
            self.engine.ranked_search("python", limit=-1)

    def test_duplicate_document_is_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.add("doc-1", "replacement")


if __name__ == "__main__":
    unittest.main()
