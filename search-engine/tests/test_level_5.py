"""Segments and merging: preserve logical results while replacing physical data."""

import random
import unittest
from unittest.mock import patch

from support import make_components, make_engine
from search_engine.analysis import TextAnalyzer
from search_engine.config import Configuration
from search_engine.indexing.posting import FrozenPosting
from search_engine.indexing.index import Index
from search_engine.indexing.trie import TrieIndex


def query_snapshot(engine):
    return (
        engine.search("search"),
        engine.search("engine"),
        engine.prefix_search("sea"),
        engine.phrase_search("search engine"),
        engine.query('NOT("python")'),
        engine.query('AND(PREFIX("sea"), NOT("python"))'),
        engine.ranked_search("search engine python"),
        engine.ranked_search("search engine python", limit=1),
    )


class Level5MergeTests(unittest.TestCase):
    def setUp(self):
        self.policy = patch.object(Configuration, "MINIMUM_TERM_LENGHT_TO_PREFIX", 3)
        self.policy.start()
        self.addCleanup(self.policy.stop)
        self.engine, self.index, _ = make_components()

    def two_segments(self):
        self.engine.add("a", "search search engine")
        self.engine.flush()
        self.engine.add("b", "search engine python")
        self.engine.flush()

    def test_trie_factory_is_shared_by_buffer_flushes_and_merging(self):
        class CustomTrie(TrieIndex):
            pass

        index = Index(trie_factory=CustomTrie)
        self.assertIsInstance(index._buffer._trie_index, CustomTrie)

        index.add("a", "search", ["search"])
        index.flush()
        index.add("b", "engine", ["engine"])
        index.flush()

        self.assertTrue(
            all(isinstance(segment._trie_index, CustomTrie) for segment in index._segments)
        )
        self.assertIsInstance(index._buffer._trie_index, CustomTrie)

        index.merge_segments()
        self.assertIsInstance(index._segments[0]._trie_index, CustomTrie)

    def test_merge_preserves_results_scores_and_positions(self):
        self.two_segments()
        before = query_snapshot(self.engine)
        source = self.index.get_posting("search")
        positions = {ref: source.positions(ref) for ref in source.document_refs()}
        self.engine.merge_segments()
        self.assertEqual(1, len(self.index._segments))
        self.assertEqual(before, query_snapshot(self.engine))
        merged = self.index.get_posting("search")
        self.assertEqual(positions, {ref: merged.positions(ref) for ref in merged.document_refs()})

    def test_merge_keeps_nonempty_buffer_and_its_tombstones(self):
        self.two_segments()
        self.engine.delete("a")
        self.engine.add("buffer-deleted", "search buffered")
        deleted_ref = next(ref for ref in self.index.document_refs() if ref.external_id == "buffer-deleted")
        self.engine.delete("buffer-deleted")
        self.engine.add("buffer-live", "search engine")
        buffer = self.index._buffer
        before = query_snapshot(self.engine)
        self.engine.merge_segments()
        self.assertIs(buffer, self.index._buffer)
        self.assertEqual({deleted_ref.internal_id}, self.index._deleted_documents)
        self.assertEqual(before, query_snapshot(self.engine))
        self.assertEqual([], self.engine.search("buffered"))
        self.engine.flush()
        self.assertEqual([], self.engine.search("buffered"))
        self.engine.merge_segments()
        self.assertEqual(set(), self.index._deleted_documents)
        self.assertEqual(before, query_snapshot(self.engine))

    def test_reused_external_ids_keep_only_the_new_version(self):
        self.engine.add("same", "search engine oldword")
        self.engine.flush()
        self.engine.delete("same")
        self.engine.add("same", "search newword")
        self.engine.add("other", "python")
        self.engine.flush()
        before = query_snapshot(self.engine)
        self.engine.merge_segments()
        self.assertEqual(before, query_snapshot(self.engine))
        self.assertEqual([], self.engine.search("oldword"))
        self.assertEqual(["same"], self.engine.search("newword"))
        self.assertEqual([], self.engine.phrase_search("search engine"))
        self.assertEqual(set(), self.index._deleted_documents)
        self.engine.delete("same")
        self.assertEqual([], self.engine.search("search"))

    def test_new_version_can_stay_in_buffer_while_old_version_is_removed(self):
        self.two_segments()
        self.engine.delete("a")
        self.engine.add("a", "newword search")
        before = query_snapshot(self.engine)
        self.engine.merge_segments()
        self.assertEqual(before, query_snapshot(self.engine))
        self.assertEqual(["a"], self.engine.search("newword"))
        self.assertEqual(["b"], self.engine.phrase_search("search engine"))
        self.assertEqual({"b"}, self.index._segments[0].external_document_ids())

    def test_deleted_short_terms_do_not_crash_trie_cleanup(self):
        self.engine.add("short", "an a")
        self.engine.flush()
        self.engine.add("keep", "search")
        self.engine.flush()
        self.engine.delete("short")
        self.engine.merge_segments()
        self.assertEqual([], self.engine.search("an"))
        self.assertEqual(["keep"], self.engine.prefix_search("sea"))
        self.assertEqual({"search"}, set(self.index._segments[0]._postings))

    def test_trie_pruning_preserves_shared_prefixes_and_removes_dead_branches(self):
        self.engine.add("deleted", "car cat obsolete")
        self.engine.flush()
        self.engine.add("keep", "cart search")
        self.engine.flush()
        self.engine.delete("deleted")
        self.engine.merge_segments()
        segment = self.index._segments[0]
        self.assertEqual([], self.engine.search("car"))
        self.assertEqual(["keep"], self.engine.prefix_search("car"))
        self.assertEqual(["cart"], segment._trie_index.terms_with_prefix("car"))
        self.assertNotIn("o", segment._trie_index._root.children)
        self.assertEqual({"cart", "search"}, set(segment._postings))

    def test_merge_removes_all_deleted_documents(self):
        self.two_segments()
        self.engine.delete("a")
        self.engine.delete("b")
        self.engine.merge_segments()
        segment = self.index._segments[0]
        self.assertEqual(set(), segment.external_document_ids())
        self.assertEqual({}, dict(segment._postings))
        self.assertEqual({}, segment._trie_index._root.children)
        self.assertEqual(set(), self.index._deleted_documents)
        self.assertEqual([], self.engine.query('NOT("missing")'))
        self.assertEqual([], self.engine.ranked_search("search"))

    def test_empty_documents_survive_and_deleted_empty_documents_are_removed(self):
        self.engine.add("empty-live", "")
        self.engine.add("empty-deleted", "")
        self.engine.flush()
        self.engine.add("keep", "search")
        self.engine.flush()
        self.engine.delete("empty-deleted")
        before = query_snapshot(self.engine)
        self.engine.merge_segments()
        self.assertEqual(before, query_snapshot(self.engine))
        self.assertEqual({"empty-live", "keep"}, self.index._segments[0].external_document_ids())
        self.assertEqual(set(), self.index._deleted_documents)

    def test_replacement_contains_frozen_postings_and_leaves_sources_unchanged(self):
        self.two_segments()
        sources = list(self.index._segments)
        original_refs = sources[0].document_refs("search")
        self.engine.delete("a")
        self.engine.merge_segments()
        for posting in self.index._segments[0]._postings.values():
            self.assertIsInstance(posting, FrozenPosting)
        self.assertEqual(original_refs, sources[0].document_refs("search"))
        self.assertEqual({"a"}, sources[0].external_document_ids())
        self.assertEqual(["search"], sources[0]._trie_index.terms_with_prefix("sea"))

    def test_merge_does_not_reanalyze_document_text(self):
        self.two_segments()
        before = query_snapshot(self.engine)
        with patch.object(TextAnalyzer, "analyze", side_effect=AssertionError("re-analysis during merge")):
            self.engine.merge_segments()
        self.assertEqual(before, query_snapshot(self.engine))

    def test_failure_during_freezing_or_construction_preserves_old_state(self):
        self.two_segments()
        self.engine.delete("a")
        self.engine.add("buffer", "search engine")
        before = query_snapshot(self.engine)
        segments = self.index._segments
        buffer = self.index._buffer
        tombstones = set(self.index._deleted_documents)
        live_refs = self.index.document_refs()
        for target in (
            "search_engine.indexing.posting.MutablePosting.freeze",
            "search_engine.indexing.index.Segment",
        ):
            with self.subTest(target=target):
                with patch(target, side_effect=RuntimeError("simulated failure")):
                    with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                        self.engine.merge_segments()
                self.assertIs(segments, self.index._segments)
                self.assertIs(buffer, self.index._buffer)
                self.assertEqual(tombstones, self.index._deleted_documents)
                self.assertEqual(live_refs, self.index.document_refs())
                self.assertEqual(before, query_snapshot(self.engine))
        self.engine.merge_segments()
        self.assertEqual(before, query_snapshot(self.engine))

    def test_empty_single_and_repeated_merge_preserve_results(self):
        # Current policy: fewer than two segments is a no-op, not compaction.
        self.engine.merge_segments()
        self.engine.add("a", "search engine")
        self.engine.flush()
        self.engine.delete("a")
        before = query_snapshot(self.engine)
        self.engine.merge_segments()
        self.assertEqual(before, query_snapshot(self.engine))
        self.engine.flush()
        self.engine.merge_segments()
        self.engine.merge_segments()
        self.assertEqual(before, query_snapshot(self.engine))

    def test_seeded_lifecycle_matches_fresh_live_corpus(self):
        # Reference engine has only live documents and never flushes or merges.
        for seed in range(3):
            rng = random.Random(seed)
            engine = make_engine()
            live = {}
            for step in range(50):
                action = rng.choice(("add", "add", "delete", "flush", "merge"))
                doc_id = str(rng.randrange(8))
                if action == "add" and doc_id not in live:
                    text = rng.choice(("", "an", "search engine", "search search python", "searching"))
                    engine.add(doc_id, text)
                    live[doc_id] = text
                elif action == "delete" and live:
                    doc_id = rng.choice(sorted(live))
                    engine.delete(doc_id)
                    del live[doc_id]
                elif action == "flush":
                    engine.flush()
                elif action == "merge":
                    engine.merge_segments()

                reference = make_engine()
                for current_id, text in live.items():
                    reference.add(current_id, text)
                with self.subTest(seed=seed, step=step, action=action):
                    self.assertEqual(query_snapshot(reference), query_snapshot(engine))


if __name__ == "__main__":
    unittest.main()
