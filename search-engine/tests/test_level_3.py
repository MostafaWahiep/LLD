"""Level 3: scores, corpus statistics, ordering, and limits."""

from dataclasses import FrozenInstanceError
from math import log
import unittest

from support import make_engine, populated_engine
from search_result import SearchResult


class Level3Tests(unittest.TestCase):
    def setUp(self):
        self.engine = populated_engine()

    def test_exact_smoothed_tf_idf_scores(self):
        results = self.engine.ranked_search("python search")
        self.assertEqual(["doc-1", "doc-2", "doc-3"], [r.document_id for r in results])
        idf = 1 + log(4 / 3)
        self.assertAlmostEqual((2 + log(2)) * idf, results[0].score)
        self.assertAlmostEqual(idf, results[1].score)
        self.assertAlmostEqual(idf, results[2].score)

    def test_repeated_document_term_increases_score(self):
        engine = make_engine()
        engine.add("once", "search")
        engine.add("twice", "search search")
        results = engine.ranked_search("search")
        self.assertEqual(["twice", "once"], [r.document_id for r in results])
        self.assertGreater(results[0].score, results[1].score)

    def test_rare_term_has_more_weight(self):
        engine = make_engine()
        engine.add("rare", "rareword")
        engine.add("common-a", "commonword")
        engine.add("common-b", "commonword")
        results = engine.ranked_search("rareword commonword")
        self.assertEqual("rare", results[0].document_id)
        self.assertGreater(results[0].score, results[1].score)

    def test_new_documents_update_idf(self):
        engine = make_engine()
        engine.add("a", "search")
        self.assertAlmostEqual(1.0, engine.ranked_search("search")[0].score)
        engine.add("b", "other")
        self.assertAlmostEqual(1 + log(3 / 2), engine.ranked_search("search")[0].score)
        engine.add("c", "search")
        self.assertAlmostEqual(1 + log(4 / 3), engine.ranked_search("search")[0].score)

    def test_limit_applies_after_aggregating_all_terms(self):
        engine = make_engine()
        engine.add("a", "alpha alpha alpha")
        engine.add("b", "beta beta beta")
        engine.add("winner", "alpha alpha beta beta")
        self.assertEqual(["winner"], [r.document_id for r in engine.ranked_search("alpha beta", 1)])

    def test_limits_zero_one_exact_and_oversized(self):
        all_results = self.engine.ranked_search("python search")
        for limit in (0, 1, 3, 100):
            with self.subTest(limit=limit):
                self.assertEqual(all_results[:limit], self.engine.ranked_search("python search", limit))

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.ranked_search("python", -1)

    def test_equal_scores_sorted_by_id_not_insertion_order(self):
        engine = make_engine()
        for doc_id in ("z", "m", "a"):
            engine.add(doc_id, "search")
        self.assertEqual(["a", "m", "z"], [r.document_id for r in engine.ranked_search("search")])

    def test_empty_and_missing_queries(self):
        for query in ("", "  ", "!!!", "missing"):
            with self.subTest(query=query):
                self.assertEqual([], self.engine.ranked_search(query))
        self.assertEqual([], make_engine().ranked_search("search"))

    def test_normalization_and_missing_terms(self):
        expected = self.engine.ranked_search("python search")
        self.assertEqual(expected, self.engine.ranked_search("PYTHON, SEARCH!"))
        self.assertEqual(expected, self.engine.ranked_search("python search missing"))

    def test_repeated_query_terms_retain_current_weighting(self):
        # Existing policy: each query occurrence contributes separately.
        once = self.engine.ranked_search("python")
        twice = self.engine.ranked_search("python python")
        self.assertEqual([r.document_id for r in once], [r.document_id for r in twice])
        for first, second in zip(once, twice):
            self.assertAlmostEqual(2 * first.score, second.score)

    def test_result_is_immutable_value_object(self):
        result = SearchResult("doc", 1.0)
        self.assertEqual(result, SearchResult("doc", 1.0))
        self.assertNotEqual(result, SearchResult("doc", 2.0))
        with self.assertRaises(FrozenInstanceError):
            result.score = 2.0


if __name__ == "__main__":
    unittest.main()
