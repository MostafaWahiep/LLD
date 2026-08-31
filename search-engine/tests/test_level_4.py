"""Level 4: positions, phrase matching, trie prefixes, and composition."""

from itertools import product
from uuid import UUID
import unittest
from unittest.mock import patch

from support import make_components, make_engine
from config import Configuration
from document_ref import DocumentRef
from posting import MutablePosting
from query import AndQuery, NotQuery, OrQuery, PhraseQuery, PrefixQuery, TermQuery
from trie_index import TrieIndex


class PhraseTests(unittest.TestCase):
    def test_order_and_adjacency(self):
        engine = make_engine()
        engine.add("match", "distributed search engine")
        engine.add("reversed", "search distributed engine")
        engine.add("gap", "distributed fast search engine")
        self.assertEqual(["match"], engine.phrase_search("distributed search"))

    def test_multiple_anchors_need_only_one_complete_match(self):
        engine = make_engine()
        engine.add("doc", "search unrelated search engine search")
        self.assertEqual(["doc"], engine.phrase_search("search engine"))

    def test_repeated_phrase_words_keep_distinct_offsets(self):
        engine = make_engine()
        engine.add("yes", "very very fast")
        engine.add("no", "very fast")
        self.assertEqual(["yes"], engine.phrase_search("very very fast"))
        self.assertEqual([], engine.phrase_search("very very very"))

    def test_rarest_anchor_can_be_in_middle_or_at_end(self):
        engine = make_engine()
        engine.add("doc", "common common rare tail common")
        self.assertEqual(["doc"], engine.phrase_search("common rare tail"))
        self.assertEqual(["doc"], engine.phrase_search("common rare"))

    def test_matches_at_document_boundaries(self):
        engine = make_engine()
        engine.add("doc", "alpha beta gamma")
        for phrase in ("alpha beta", "beta gamma", "alpha beta gamma"):
            with self.subTest(phrase=phrase):
                self.assertEqual(["doc"], engine.phrase_search(phrase))
        self.assertEqual([], engine.phrase_search("gamma alpha"))

    def test_analysis_applies_to_phrase_and_document(self):
        engine = make_engine()
        engine.add("doc", "Distributed, SEARCH-engine!")
        self.assertEqual(["doc"], engine.phrase_search("DISTRIBUTED search"))
        self.assertEqual(["doc"], engine.phrase_search("search-engine"))

    def test_single_word_empty_and_missing_phrases(self):
        engine = make_engine()
        engine.add("doc", "search engine")
        self.assertEqual(engine.search("search"), engine.phrase_search("search"))
        for phrase in ("", "!!!", "search missing", "search engine beyond"):
            with self.subTest(phrase=phrase):
                self.assertEqual([], engine.phrase_search(phrase))
        self.assertEqual([], make_engine().phrase_search("search engine"))

    def test_phrase_cannot_span_documents(self):
        engine = make_engine()
        engine.add("a", "search")
        engine.add("b", "engine")
        self.assertEqual([], engine.phrase_search("search engine"))

    def test_results_are_unique_and_sorted(self):
        engine = make_engine()
        engine.add("z", "search engine search engine")
        engine.add("a", "search engine")
        self.assertEqual(["a", "z"], engine.phrase_search("search engine"))

    def test_generated_phrases_against_independent_token_oracle(self):
        engine = make_engine()
        documents = {}
        vocabulary = ("alpha", "beta", "gamma")
        for length in range(6):
            for words in product(vocabulary, repeat=length):
                doc_id = str(len(documents))
                documents[doc_id] = words
                engine.add(doc_id, " ".join(words))
        for length in range(1, 4):
            for phrase in product(vocabulary, repeat=length):
                expected = {
                    doc_id for doc_id, words in documents.items()
                    if any(words[i:i + length] == phrase
                           for i in range(len(words) - length + 1))
                }
                with self.subTest(phrase=phrase):
                    self.assertEqual(expected, set(engine.phrase_search(" ".join(phrase))))


class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.policy = patch.object(Configuration, "MINIMUM_TERM_LENGHT_TO_PREFIX", 3)
        self.policy.start()
        self.addCleanup(self.policy.stop)

    def test_prefix_includes_terminal_and_descendant_words(self):
        engine = make_engine()
        engine.add("exact", "search")
        engine.add("longer", "searching searchable")
        engine.add("other", "research")
        self.assertEqual(["exact", "longer"], engine.prefix_search("search"))
        self.assertEqual(["exact", "longer"], engine.prefix_search("sear"))
        self.assertEqual(["exact"], engine.search("search"))

    def test_shared_document_is_not_duplicated(self):
        engine = make_engine()
        engine.add("doc", "search searching searchable search")
        self.assertEqual(["doc"], engine.prefix_search("sear"))

    def test_normalization(self):
        engine = make_engine()
        engine.add("doc", "SEARCHING")
        self.assertEqual(["doc"], engine.prefix_search("SEAR!"))

    def test_missing_and_overlong_prefixes(self):
        engine = make_engine()
        engine.add("doc", "search")
        for prefix in ("xyz", "searches"):
            with self.subTest(prefix=prefix):
                self.assertEqual([], engine.prefix_search(prefix))
        self.assertEqual([], make_engine().prefix_search("sea"))

    def test_minimum_length_does_not_restrict_exact_search(self):
        engine = make_engine()
        engine.add("doc", "an ant anthem")
        self.assertEqual(["doc"], engine.search("an"))
        self.assertEqual([], engine.prefix_search("an"))
        self.assertEqual(["doc"], engine.prefix_search("ant"))

    def test_invalid_prefixes(self):
        engine = make_engine()
        for prefix in ("", "!!!", "two words"):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                engine.prefix_search(prefix)

    def test_new_and_existing_terms_after_indexing(self):
        engine = make_engine()
        engine.add("a", "search")
        self.assertEqual(["a"], engine.prefix_search("sear"))
        engine.add("b", "search searching")
        self.assertEqual(["a", "b"], engine.prefix_search("sear"))
        self.assertEqual(["b"], engine.prefix_search("searchi"))

    def test_trie_lookup_matches_vocabulary_prefixes(self):
        trie = TrieIndex()
        terms = {"sea", "search", "searching", "searchable", "season", "python"}
        for term in terms:
            trie.prefix_term(term)
            trie.prefix_term(term)
        for prefix in ("sea", "sear", "search", "searchi", "seafood", "pyt"):
            with self.subTest(prefix=prefix):
                actual = trie.terms_with_prefix(prefix)
                self.assertEqual({t for t in terms if t.startswith(prefix)}, set(actual))
                self.assertEqual(len(actual), len(set(actual)))

    def test_long_term_prefix_does_not_require_recursion(self):
        engine = make_engine()
        long_term = "abc" + "x" * 1500
        engine.add("long", long_term)
        self.assertEqual(["long"], engine.prefix_search("abc"))
        self.assertEqual(["long"], engine.search(long_term))


class PositionTests(unittest.TestCase):
    def test_bulk_positions_isolation_from_caller(self):
        ref = DocumentRef(UUID(int=1), "doc")
        supplied = {0, 2}
        posting = MutablePosting("search")
        posting.add_positions(ref, supplied)

        supplied.add(4)
        self.assertEqual({0, 2}, posting.positions(ref))
        posting.add(ref, 6)
        self.assertEqual({0, 2, 4}, supplied)

    def test_combined_posting_isolation_from_sources(self):
        _, index, _ = make_components()
        first_ref = DocumentRef(UUID(int=1), "first")
        second_ref = DocumentRef(UUID(int=2), "second")
        first = MutablePosting("search")
        second = MutablePosting("search")
        first.add(first_ref, 0)
        second.add(second_ref, 2)
        combined = index._merge_postings("search", [first, second])

        self.assertEqual({first_ref, second_ref}, combined.document_refs())
        combined.add(first_ref, 4)
        combined.add(second_ref, 5)
        self.assertEqual({0}, first.positions(first_ref))
        self.assertEqual({2}, second.positions(second_ref))

        first.add(first_ref, 6)
        second.add(second_ref, 7)
        self.assertEqual({0, 4}, combined.positions(first_ref))
        self.assertEqual({2, 5}, combined.positions(second_ref))

    def test_get_posting_isolation_from_index(self):
        engine, index, _ = make_components()
        engine.add("doc", "search engine search")
        combined = index.get_posting("search")
        ref = next(iter(combined.document_refs()))
        combined.add(ref, 100)

        self.assertEqual({0, 2}, index.get_posting("search").positions(ref))
        self.assertEqual(2, index.get_posting("search").frequency(ref))

    def test_index_records_zero_based_positions_and_frequency(self):
        engine, index, _ = make_components()
        engine.add("doc", "search engine search")
        posting = index.get_posting("search")
        refs = posting.document_refs()
        self.assertEqual(1, len(refs))
        ref = next(iter(refs))
        self.assertIsInstance(ref, DocumentRef)
        self.assertEqual("doc", ref.external_id)
        self.assertEqual({0, 2}, set(posting.positions(ref)))
        self.assertEqual(2, posting.frequency(ref))
        self.assertEqual(1, posting.document_frequency())

    def test_missing_position_lookup_does_not_modify_posting(self):
        posting = MutablePosting("search")
        missing = DocumentRef(UUID(int=1), "missing")
        self.assertEqual(set(), set(posting.positions(missing)))
        self.assertEqual(0, posting.frequency(missing))
        self.assertEqual(set(), posting.document_refs())

    def test_returned_positions_cannot_corrupt_index(self):
        posting = MutablePosting("search")
        ref = DocumentRef(UUID(int=1), "doc")
        posting.add(ref, 0)
        positions = posting.positions(ref)
        # Accept either an immutable collection or a defensive mutable copy.
        try:
            positions.clear()
        except (AttributeError, TypeError):
            pass
        self.assertEqual({0}, set(posting.positions(ref)))
        self.assertEqual(1, posting.frequency(ref))

    def test_returned_document_refs_cannot_mutate_posting(self):
        posting = MutablePosting("search")
        ref = DocumentRef(UUID(int=1), "doc")
        posting.add(ref, 0)
        posting.document_refs().clear()
        self.assertEqual({ref}, posting.document_refs())

    def test_posting_identity_uses_internal_id(self):
        # This is an identity-unit test, not a Level 5 deletion/reuse scenario.
        first = DocumentRef(UUID(int=1), "same-external-id")
        second = DocumentRef(UUID(int=2), "same-external-id")
        posting = MutablePosting("search")
        posting.add(first, 0)
        posting.add(second, 3)
        self.assertEqual(2, posting.document_frequency())
        self.assertEqual({0}, posting.positions(first))
        self.assertEqual({3}, posting.positions(second))


class Level4CompositionTests(unittest.TestCase):
    def setUp(self):
        self.engine, _, self.evaluator = make_components()
        self.engine.add("keep", "distributed search engine")
        self.engine.add("exclude", "distributed search legacycode")
        self.engine.add("other", "searching")

    def test_query_objects_compose_through_visitor(self):
        query = AndQuery(PhraseQuery("distributed search"), NotQuery(PrefixQuery("legacy")))
        expected = self.evaluator.evaluate(TermQuery("engine"))
        self.assertEqual(1, len(expected))
        self.assertTrue(all(isinstance(ref, DocumentRef) for ref in expected))
        self.assertEqual({"keep"}, {ref.external_id for ref in expected})
        self.assertEqual(expected, self.evaluator.evaluate(query))
        query = OrQuery(PrefixQuery("searchi"), TermQuery("engine"))
        expected = expected | self.evaluator.evaluate(TermQuery("searching"))
        self.assertEqual({"keep", "other"}, {ref.external_id for ref in expected})
        self.assertEqual(expected, self.evaluator.evaluate(query))

    def test_evaluator_returns_refs_for_every_query_type(self):
        cases = [
            (TermQuery("engine"), {"keep"}),
            (PrefixQuery("legacy"), {"exclude"}),
            (PhraseQuery("distributed search"), {"keep", "exclude"}),
            (NotQuery(TermQuery("legacycode")), {"keep", "other"}),
        ]
        for query, expected in cases:
            with self.subTest(query=type(query).__name__):
                matches = self.evaluator.evaluate(query)
                self.assertIsInstance(matches, set)
                self.assertTrue(all(isinstance(ref, DocumentRef) for ref in matches))
                self.assertEqual(expected, {ref.external_id for ref in matches})

    def test_phrase_and_prefix_reject_compound_arguments(self):
        for source in (
            'PREFIX(AND("search", "engine"))',
            'PHRASE(NOT("search"))',
            'PREFIX(PHRASE("search engine"))',
            'PHRASE(PREFIX("sear"))',
        ):
            with self.subTest(source=source), self.assertRaises(SyntaxError):
                self.engine.query(source)

    def test_public_boolean_phrase_composition(self):
        # Proposed syntax from the Level 4 exercise; intentionally tests the public API.
        self.assertEqual(
            ["keep"],
            self.engine.query('AND(PHRASE("distributed search"), NOT("legacycode"))'),
        )

    def test_public_boolean_prefix_composition(self):
        self.assertEqual(
            ["keep"],
            self.engine.query('AND(PREFIX("sear"), "engine")'),
        )


if __name__ == "__main__":
    unittest.main()
