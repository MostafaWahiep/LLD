"""Level 2: shared analysis, boolean semantics, and query syntax."""

import unittest

from support import make_engine, populated_engine


class Level2Tests(unittest.TestCase):
    def setUp(self):
        self.engine = populated_engine()

    def test_shared_punctuation_and_case_normalization(self):
        engine = make_engine()
        engine.add("doc", "Python, SEARCH-engine!\nfast\tindex")
        for term in ("python!", "SEARCH", "engine", "fast", "index"):
            with self.subTest(term=term):
                self.assertEqual(["doc"], engine.search(term))

    def test_quoted_term_query(self):
        self.assertEqual(["doc-1", "doc-2"], self.engine.query('"PYTHON!"'))

    def test_and_or_not(self):
        cases = [
            ('AND("python", "search")', ["doc-1"]),
            ('OR("python", "search")', ["doc-1", "doc-2", "doc-3"]),
            ('NOT("python")', ["doc-3"]),
            ('AND("search", NOT("python"))', ["doc-3"]),
            ('AND("python", OR("search", "framework"))', ["doc-1", "doc-2"]),
            ('NOT(NOT("python"))', ["doc-1", "doc-2"]),
            ('AND("python", NOT("python"))', []),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(expected, self.engine.query(query))

    def test_missing_term_in_boolean_operations(self):
        cases = [
            ('AND("python", "missing")', []),
            ('OR("python", "missing")', ["doc-1", "doc-2"]),
            ('NOT("missing")', ["doc-1", "doc-2", "doc-3"]),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(expected, self.engine.query(query))

    def test_empty_documents_participate_in_not(self):
        self.engine.add("empty", "")
        self.assertEqual(["doc-3", "empty"], self.engine.query('NOT("python")'))

    def test_boolean_queries_on_empty_engine(self):
        engine = make_engine()
        for query in ('NOT("word")', 'AND("a", "b")', 'OR("a", "b")'):
            with self.subTest(query=query):
                self.assertEqual([], engine.query(query))

    def test_rejects_invalid_single_terms(self):
        for term in ("", "  ", "!!!", "python search"):
            with self.subTest(term=term), self.assertRaises(ValueError):
                self.engine.search(term)

    def test_rejects_malformed_queries(self):
        # The current parser uses both IndexError and ValueError for syntax errors.
        cases = ["", "  ", '"unterminated', 'AND("python")',
                 'AND("python",)', 'NOT()', 'AND("a", "b"',
                 '"a" "b"', 'NOT("a", "b")', 'OR("a", @)']
        before = self.engine.search("python")
        for query in cases:
            with self.subTest(query=query), self.assertRaises((ValueError, IndexError)):
                self.engine.query(query)
        self.assertEqual(before, self.engine.search("python"))

    def test_operators_can_be_searched_as_quoted_words(self):
        self.engine.add("operators", "and or not")
        self.assertEqual(["operators"], self.engine.query('"AND"'))


if __name__ == "__main__":
    unittest.main()
