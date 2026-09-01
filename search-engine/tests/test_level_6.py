"""Persistence publication: immutable segments and atomic manifest replacement."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from search_engine.analysis import TextAnalyzer
from search_engine.engine import SearchEngine
from search_engine.factory import open_engine
from search_engine.indexing.codec import ManifestCodec, SegmentCodec
from search_engine.indexing.index import Index
from search_engine.indexing.segment import Segment
from search_engine.indexing.trie import TrieIndex
from search_engine.querying.evaluator import QueryEvaluator
from search_engine.querying.parser import Parser


class FakeManifest:
    def __init__(self, value: str):
        self._value = value

    def to_dict(self) -> dict:
        return {"value": self._value}


def make_persistent_engine(directory: Path) -> SearchEngine:
    index = Index()
    analyzer = TextAnalyzer()
    evaluator = QueryEvaluator(index, analyzer)
    return SearchEngine(directory, Parser(), analyzer, index, evaluator)


def query_snapshot(engine: SearchEngine) -> tuple:
    return (
        engine.search("search"),
        engine.query('NOT("python")'),
        engine.query('AND(PREFIX("sea"), NOT("python"))'),
        engine.prefix_search("sea"),
        engine.phrase_search("distributed search"),
        engine.ranked_search("search engine python"),
        engine.ranked_search("search engine python", limit=2),
    )


class AtomicPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)

    def test_existing_immutable_segment_is_reused(self):
        segment = Segment({}, {}, TrieIndex())
        SegmentCodec.write(segment, self.directory)
        segment_path = self.directory / f"{segment.id()}.json"
        original_bytes = segment_path.read_bytes()

        with patch.object(
            SegmentCodec,
            "_serialize_segment",
            side_effect=AssertionError("existing segment should not be serialized"),
        ):
            SegmentCodec.write(segment, self.directory)

        self.assertEqual(original_bytes, segment_path.read_bytes())

    def test_failed_segment_write_never_publishes_final_filename(self):
        segment = Segment({}, {}, TrieIndex())
        segment_path = self.directory / f"{segment.id()}.json"

        with patch(
            "search_engine.indexing.codec.json.dump",
            side_effect=RuntimeError("simulated write failure"),
        ):
            with self.assertRaises(RuntimeError):
                SegmentCodec.write(segment, self.directory)

        self.assertFalse(segment_path.exists())
        self.assertEqual([], list(self.directory.glob("*.tmp")))

    def test_failed_manifest_write_preserves_previous_manifest(self):
        manifest_path = self.directory / "manifest.json"
        ManifestCodec.write(FakeManifest("previous"), self.directory)

        with patch(
            "search_engine.indexing.codec.json.dump",
            side_effect=RuntimeError("simulated write failure"),
        ):
            with self.assertRaises(RuntimeError):
                ManifestCodec.write(FakeManifest("new"), self.directory)

        self.assertEqual(
            {"value": "previous"},
            json.loads(manifest_path.read_text()),
        )
        self.assertEqual([], list(self.directory.glob("*.tmp")))

    def test_segment_path_directory_collision_is_rejected(self):
        segment = Segment({}, {}, TrieIndex())
        segment_path = self.directory / f"{segment.id()}.json"
        segment_path.mkdir()

        with self.assertRaises(ValueError):
            SegmentCodec.write(segment, self.directory)


class RestartRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)

    def test_commit_reopen_preserves_queries_and_document_lifecycle(self):
        engine = make_persistent_engine(self.directory)
        engine.add("deleted", "python search engine")
        engine.add("distributed", "distributed search engine")
        engine.flush()

        engine.add("python", "python web framework")
        engine.add("prefix", "searching searchable content")
        engine.delete("deleted")

        before_commit = query_snapshot(engine)
        live_ids_before_commit = engine._index.external_document_ids()
        engine.commit()

        reopened = open_engine(self.directory)
        self.assertEqual(before_commit, query_snapshot(reopened))
        self.assertEqual(
            live_ids_before_commit,
            reopened._index.external_document_ids(),
        )
        self.assertNotIn("deleted", reopened.search("search"))

        with self.assertRaises(ValueError):
            reopened.add("distributed", "duplicate live ID")

        reopened.add("after-restart", "distributed search persistence")
        after_restart = query_snapshot(reopened)
        reopened.commit()

        reopened_again = open_engine(self.directory)
        self.assertEqual(after_restart, query_snapshot(reopened_again))
        self.assertEqual(
            {
                "distributed",
                "python",
                "prefix",
                "after-restart",
            },
            reopened_again._index.external_document_ids(),
        )


if __name__ == "__main__":
    unittest.main()
