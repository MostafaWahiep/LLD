# Search engine regression tests

Run from the `search-engine` directory:

```sh
PYTHONPATH=src python3 -B -m unittest discover -s tests -v
```

Run one level:

```sh
PYTHONPATH=src python3 -B -m unittest discover -s tests -p 'test_level_4.py' -v
```

- `test_level_1.py`: exact lookup, document lifecycle, isolation.
- `test_level_2.py`: shared analysis, boolean operations, parser errors.
- `test_level_3.py`: TF-IDF formula, frequencies, corpus changes, limits, ties.
- `test_level_4.py`: positions, phrases, trie prefixes, boolean composition.
- `test_level_5.py`: merge preservation, tombstone cleanup, ID reuse, buffer
  isolation, trie pruning, immutable replacement postings, and failure safety.
- `test_posting.py`: shared posting reads, immutable snapshots, flush ownership,
  live views, and query preservation across mutable/frozen sources.
- `support.py`: shared construction helpers (not production code).

The fixtures construct `Index()`. Public APIs still return
external document IDs; posting and evaluator tests use `DocumentRef` values.
Reference identity must use internal IDs, including when two references happen
to have the same external label. Level 2 and Level 3 public behavior tests remain
unchanged. Posting integration tests cover flush boundaries; Level 5 tests add
merge/deletion lifecycles, failure injection during replacement construction,
and seeded operation sequences compared with a freshly indexed live corpus.
They retain the current policy that merging fewer than two segments is a no-op.

## Policies recorded by these tests

Tests retain current choices: sorted document IDs, duplicate-ID rejection,
empty documents allowed, empty ranked/phrase queries returning no results,
and repeated ranked-query terms contributing repeatedly to scores. Prefix
tests temporarily fix the minimum length to three and restore it afterward.
Short prefixes return no results, while exact short-word queries remain valid.

Level 4 also includes deliberate regression targets for the reviewed gaps:
returned positions must not let a caller corrupt the index, and phrase/prefix
queries must compose through the public search API. The latter tests use the
exercise's proposed `PHRASE(...)` and `PREFIX(...)` syntax. If a public
query-object API is chosen instead, adapt those two tests to that API while
keeping the same expected results. These tests are not skipped or marked as
expected failures, so unfinished behavior remains visible.

Level 4 includes regressions for long trie paths and rejection of compound
arguments to `PHRASE`/`PREFIX`.

## Posting views and snapshots

`Posting` is the four-method read interface. `StoredPosting` extends it with
`view()` and `freeze()` for buffer/segment storage. Shared `SegmentReads`
lookup calls `view()` without branching on posting type:

- A mutable posting returns a read-only `PostingView`, which reflects later
  changes to the same backing posting. It does not expose write methods.
- A frozen posting returns itself from both `view()` and `freeze()`.
- Flush creates independent frozen snapshots and a new buffer generation.
  A retained view remains attached to its original backing posting.
- Missing-term lookups return empty frozen postings, not views that begin
  matching terms inserted later.

Buffer reads no longer freeze entire postings. Returned position collections
are immutable and document-reference sets are defensive copies. Index-level
aggregation still materializes combined postings. These live views do not
provide concurrent point-in-time query isolation.

The generated phrase test uses a separate contiguous-token-slice oracle over
364 documents and 39 phrases, including repeated words. It does not reproduce
the optimized anchor-position algorithm.
