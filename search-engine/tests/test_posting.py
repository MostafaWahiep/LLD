"""Read protocol, frozen snapshots, and buffer-to-segment ownership."""

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch
from uuid import UUID

from support import make_components
from buffer import Buffer
from document import Document
from document_ref import DocumentRef
from posting import FrozenPosting, MutablePosting, Posting, PostingView, StoredPosting
from trie_index import TrieIndex


class PostingTests(unittest.TestCase):
    def setUp(self):
        self.ref = DocumentRef(UUID(int=1), "doc")

    def test_both_implement_same_read_protocol(self):
        mutable = MutablePosting("search")
        mutable.add_positions(self.ref, {0, 2})
        missing = DocumentRef(UUID(int=2), "missing")
        for posting in (mutable, mutable.freeze(), mutable.view()):
            with self.subTest(kind=type(posting).__name__):
                self.assertIsInstance(posting, Posting)
                self.assertEqual({self.ref}, posting.document_refs())
                self.assertEqual(frozenset({0, 2}), posting.positions(self.ref))
                self.assertEqual(2, posting.frequency(self.ref))
                self.assertEqual(1, posting.document_frequency())
                self.assertEqual(frozenset(), posting.positions(missing))
                self.assertEqual(0, posting.frequency(missing))
                self.assertEqual(1, posting.document_frequency())

    def test_mutable_reads_do_not_expose_writable_positions(self):
        mutable = MutablePosting("search")
        mutable.add(self.ref, 0)
        positions = mutable.positions(self.ref)
        self.assertIsInstance(positions, frozenset)
        mutable.add(self.ref, 1)
        self.assertEqual(frozenset({0}), positions)

    def test_frozen_posting_has_no_write_methods(self):
        frozen = FrozenPosting("search", {self.ref: {0}})
        self.assertFalse(hasattr(frozen, "add"))
        self.assertFalse(hasattr(frozen, "add_positions"))
        with self.assertRaises(FrozenInstanceError):
            frozen.term = "changed"
        with self.assertRaises(FrozenInstanceError):
            frozen._positions = {}
        with self.assertRaises(TypeError):
            frozen._positions[self.ref] = frozenset({9})
        with self.assertRaises(AttributeError):
            frozen.positions(self.ref).add(9)

    def test_frozen_snapshot_does_not_alias_constructor_inputs(self):
        positions = {0, 2}
        source = {self.ref: positions}
        frozen = FrozenPosting("search", source)
        positions.add(100)
        source.clear()
        self.assertEqual({self.ref}, frozen.document_refs())
        self.assertEqual(frozenset({0, 2}), frozen.positions(self.ref))

    def test_freeze_is_independent_of_later_mutable_writes(self):
        mutable = MutablePosting("search")
        mutable.add(self.ref, 0)
        frozen = mutable.freeze()
        mutable.add(self.ref, 1)
        mutable.add(DocumentRef(UUID(int=2), "new"), 5)
        self.assertEqual(frozenset({0}), frozen.positions(self.ref))
        self.assertEqual(1, frozen.document_frequency())

    def test_mutable_view_is_live_and_cannot_write(self):
        mutable = MutablePosting("search")
        mutable.add(self.ref, 0)
        view = mutable.view()
        frozen = mutable.freeze()
        self.assertIsInstance(mutable, StoredPosting)
        self.assertIsInstance(view, PostingView)
        self.assertIsInstance(view, Posting)
        self.assertNotIsInstance(view, StoredPosting)
        for method in ("add", "add_positions", "freeze", "view"):
            self.assertFalse(hasattr(view, method))
        old_positions = view.positions(self.ref)
        view.document_refs().clear()
        mutable.add(self.ref, 2)
        self.assertEqual(frozenset({0, 2}), view.positions(self.ref))
        self.assertEqual(frozenset({0}), old_positions)
        self.assertEqual(frozenset({0}), frozen.positions(self.ref))
        self.assertEqual({self.ref}, view.document_refs())

    def test_frozen_view_and_freeze_reuse_the_same_snapshot(self):
        frozen = FrozenPosting("search", {self.ref: {0}})
        self.assertIsInstance(frozen, StoredPosting)
        self.assertIs(frozen, frozen.view())
        self.assertIs(frozen, frozen.freeze())

    def test_returned_document_refs_are_independent(self):
        frozen = FrozenPosting("search", {self.ref: {0}})
        frozen.document_refs().clear()
        self.assertEqual({self.ref}, frozen.document_refs())

    def test_duplicate_bulk_insert_still_rejected(self):
        mutable = MutablePosting("search")
        mutable.add_positions(self.ref, {0})
        with self.assertRaises(ValueError):
            mutable.add_positions(self.ref, {5})
        self.assertEqual(frozenset({0}), mutable.positions(self.ref))

    def test_index_merge_requires_only_the_four_read_methods(self):
        # No term attribute and no write methods: only the requested protocol.
        ref = self.ref

        class ReadOnlyPosting:
            def document_refs(self):
                return {ref}

            def positions(self, document_ref):
                return frozenset({0, 2}) if document_ref == ref else frozenset()

            def frequency(self, document_ref):
                return len(self.positions(document_ref))

            def document_frequency(self):
                return 1

        _, index, _ = make_components()
        combined = index._merge_postings("search", [ReadOnlyPosting()])
        self.assertEqual(frozenset({0, 2}), combined.positions(ref))


class PostingFreezeIntegrationTests(unittest.TestCase):
    def test_buffer_freeze_preserves_snapshot_and_detaches_new_writes(self):
        buffer = Buffer(TrieIndex())
        ref = DocumentRef(UUID(int=1), "doc")
        buffer.add(Document(ref, "search engine"), ["search", "engine"])
        old_posting = buffer.get_posting("search")
        segment = buffer.freeze()

        self.assertIsInstance(old_posting, PostingView)
        self.assertFalse(hasattr(old_posting, "add"))
        new_ref = DocumentRef(UUID(int=2), "new")
        buffer.add(Document(new_ref, "search"), ["search"])
        self.assertEqual({ref}, old_posting.document_refs())
        self.assertEqual(frozenset({0}), segment.get_posting("search").positions(ref))
        self.assertEqual({ref}, segment.document_refs("search"))
        self.assertEqual({new_ref}, buffer.document_refs("search"))
        self.assertIsInstance(segment.get_posting("search"), FrozenPosting)
        self.assertIsInstance(segment.get_posting("missing"), FrozenPosting)
        self.assertEqual(set(), segment.get_posting("missing").document_refs())

    def test_shared_buffer_lookup_uses_live_views_without_freezing(self):
        buffer = Buffer(TrieIndex())
        first = DocumentRef(UUID(int=1), "first")
        second = DocumentRef(UUID(int=2), "second")
        buffer.add(Document(first, "search search"), ["search", "search"])
        with patch.object(MutablePosting, "freeze", side_effect=AssertionError("snapshot on read")):
            view = buffer.get_posting("SEARCH")
            self.assertIsInstance(view, PostingView)
            self.assertEqual(2, view.frequency(first))
            self.assertEqual({first}, buffer.prefix_search("sea"))
            buffer.add(Document(second, "search"), ["search"])
            self.assertEqual({first, second}, view.document_refs())
            self.assertEqual({first, second}, buffer.document_refs("search"))

    def test_shared_segment_lookup_returns_existing_frozen_posting(self):
        buffer = Buffer(TrieIndex())
        ref = DocumentRef(UUID(int=1), "doc")
        buffer.add(Document(ref, "search"), ["search"])
        segment = buffer.freeze()
        with patch.object(FrozenPosting, "freeze", side_effect=AssertionError("refreeze on read")):
            posting = segment.get_posting("search")
            self.assertIsInstance(posting, FrozenPosting)
            self.assertIs(posting, segment.get_posting("SEARCH"))
            self.assertEqual({ref}, segment.document_refs("search"))

    def test_missing_lookup_stays_empty_after_new_term_is_added(self):
        buffer = Buffer(TrieIndex())
        missing = buffer.get_posting("search")
        self.assertIsInstance(missing, FrozenPosting)
        self.assertEqual(set(), missing.document_refs())
        ref = DocumentRef(UUID(int=1), "doc")
        buffer.add(Document(ref, "search"), ["search"])
        self.assertEqual(set(), missing.document_refs())
        self.assertEqual({ref}, buffer.get_posting("search").document_refs())

    def test_flush_preserves_all_query_types_and_scores(self):
        engine, _, _ = make_components()
        engine.add("a", "search search engine")
        engine.add("b", "searching python")

        def results():
            return (
                engine.search("search"),
                engine.prefix_search("sear"),
                engine.phrase_search("search engine"),
                engine.query('AND(PREFIX("sear"), NOT("python"))'),
                engine.ranked_search("search engine"),
            )

        before = results()
        engine.flush()
        self.assertEqual(before, results())
        engine.add("c", "search engine")
        before = results()
        engine.flush()
        self.assertEqual(before, results())
        engine.delete("a")
        self.assertEqual(["c"], engine.search("search"))
        self.assertEqual(["c"], engine.phrase_search("search engine"))


if __name__ == "__main__":
    unittest.main()
