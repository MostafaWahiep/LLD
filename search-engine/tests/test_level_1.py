"""Level 1: exact-term lookup and in-memory document lifecycle."""

import unittest

from support import make_components, make_engine


class Level1Tests(unittest.TestCase):
    def test_empty_engine_and_missing_word(self):
        engine = make_engine()
        self.assertEqual([], engine.search("missing"))
        engine.add("doc", "python")
        self.assertEqual([], engine.search("missing"))

    def test_case_insensitive_complete_words(self):
        engine = make_engine()
        engine.add("doc", "Python searching")
        self.assertEqual(["doc"], engine.search("PYTHON"))
        self.assertEqual([], engine.search("pyth"))
        self.assertEqual([], engine.search("search"))

    def test_repeated_words_return_unique_sorted_ids(self):
        engine = make_engine()
        engine.add("z", "search search search")
        engine.add("a", "search")
        self.assertEqual(["a", "z"], engine.search("search"))

    def test_duplicate_document_rejected_without_replacement(self):
        engine = make_engine()
        engine.add("doc", "original")
        with self.assertRaises(ValueError):
            engine.add("doc", "replacement")
        self.assertEqual(["doc"], engine.search("original"))
        self.assertEqual([], engine.search("replacement"))

    def test_document_id_can_equal_an_indexed_term(self):
        engine = make_engine()
        engine.add("first", "python")
        engine.add("python", "search")
        self.assertEqual(["python"], engine.search("search"))

    def test_empty_document_still_reserves_its_id(self):
        engine = make_engine()
        engine.add("empty", "")
        with self.assertRaises(ValueError):
            engine.add("empty", "replacement")
        self.assertEqual([], engine.search("replacement"))

    def test_engines_are_independent(self):
        first, second = make_engine(), make_engine()
        first.add("same-id", "python")
        second.add("same-id", "java")
        self.assertEqual([], second.search("python"))
        self.assertEqual([], first.search("java"))

    def test_failed_analysis_does_not_reserve_document_id(self):
        engine = make_engine()
        with self.assertRaises((TypeError, ValueError)):
            engine.add("doc", None)
        engine.add("doc", "valid")
        self.assertEqual(["doc"], engine.search("valid"))

    def test_returned_ids_cannot_mutate_index(self):
        engine, index, _ = make_components()
        engine.add("doc", "python")
        engine.search("python").clear()
        index.postings("python").clear()
        index.document_ids().clear()
        self.assertEqual(["doc"], engine.search("python"))
        self.assertEqual({"doc"}, index.document_ids())


if __name__ == "__main__":
    unittest.main()
