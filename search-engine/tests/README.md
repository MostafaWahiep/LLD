# Search engine regression tests

Run from the repository root:

```sh
python3 -B -m unittest discover -s search-engine/tests -v
```

Run one level:

```sh
python3 -B -m unittest discover -s search-engine/tests -p 'test_level_4.py' -v
```

- `test_level_1.py`: exact lookup, document lifecycle, isolation.
- `test_level_2.py`: shared analysis, boolean operations, parser errors.
- `test_level_3.py`: TF-IDF formula, frequencies, corpus changes, limits, ties.
- `test_level_4.py`: positions, phrases, trie prefixes, boolean composition.
- `support.py`: shared construction helpers (not production code).

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

The generated phrase test uses a separate contiguous-token-slice oracle over
364 documents and 39 phrases, including repeated words. It does not reproduce
the optimized anchor-position algorithm.
