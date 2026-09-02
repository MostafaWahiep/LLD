# Build a Search Engine

This project develops a small Lucene-style search engine one working level at a
time. Each level adds requirements while preserving behavior from previous
levels.

## Running the project

From this directory, run:

```sh
PYTHONPATH=src python3 -B -m unittest discover -s tests -v
PYTHONPATH=src python3 -B examples/demo.py
```

You can also install the package in editable mode with
`python3 -m pip install -e .`.

Do not design later levels prematurely. Implement the simplest design that
satisfies the current requirements, but keep responsibilities separated enough
to change it safely.

## Roadmap

1. In-memory exact-term search
2. Text analysis and boolean queries
3. Relevance ranking
4. Phrase and prefix queries
5. Immutable segments, deletion, and merging
6. Persistence and crash-safe commits
7. Concurrent indexing and searching
8. Sharding, replication, and distributed search

## Level 1 — In-memory exact-term search

Start with a small search engine that stores documents in memory.

```python
engine = SearchEngine()

engine.add("doc-1", "Python search engine")
engine.add("doc-2", "Python web framework")
engine.add("doc-3", "Distributed search system")
```

Search for a complete word:

```python
engine.search("python")
# ["doc-1", "doc-2"]

engine.search("search")
# ["doc-1", "doc-3"]

engine.search("sea")
# []
```

Search should be case-insensitive:

```python
engine.search("PYTHON")
# ["doc-1", "doc-2"]
```

The basic API could be:

```python
class SearchEngine:
    def add(self, document_id: str, text: str) -> None:
        ...

    def search(self, term: str) -> list[str]:
        ...
```

---

Searching should remain efficient as more documents are added. It should not
read every document for every search.

You will probably need a structure that looks conceptually like:

```text
"python" → {"doc-1", "doc-2"}
"search" → {"doc-1", "doc-3"}
```

This is an **inverted index**: instead of mapping a document to its words, it
maps a word to the documents containing it.

---

Requirements:

- Store documents in memory.
- Search by complete words, not substrings.
- Normalize indexed words and search terms to lowercase.
- Return the IDs of matching documents.
- Use an index rather than scanning every document.

Input validation, duplicate document IDs, result ordering, and other edge cases
are decisions for you to discover and document.

---

## Level 2 — Text analysis and boolean queries

First, improve how text is converted into searchable words.

```python
engine.add("doc-1", "Python, search-engine!")

engine.search("python")
# ["doc-1"]

engine.search("search")
# ["doc-1"]
```

Punctuation should separate words, and document text and search terms should be
processed in the same way.

This suggests a new component:

```text
TextAnalyzer
     │
     └── "Python, search-engine!"
              ↓
         ["python", "search", "engine"]
```

The analyzer should be used when adding documents and when searching.

---

Now allow users to combine terms with boolean operations.

Given these documents:

```text
doc-1: "Python search engine"
doc-2: "Python web framework"
doc-3: "Distributed search system"
```

Support:

```text
AND("python", "search") -> ["doc-1"]
OR("framework", "distributed") -> ["doc-2", "doc-3"]
AND("search", NOT("python")) -> ["doc-3"]
```

Queries may also be nested:

```text
AND("python", OR("search", "framework"))
```

Boolean queries combine sets of matching document IDs:

```text
AND → intersection
OR  → union
NOT → difference from all document IDs
```

---

You may accept a query string and parse it:

```python
engine.query('AND("python", "search")')
```

Or let callers construct query objects:

```python
engine.query(
    AndQuery(
        TermQuery("python"),
        TermQuery("search"),
    )
)
```

If you parse strings, the design may start to separate into:

```text
query string
     ↓
Tokenizer
     ↓
Parser
     ↓
Query objects
     ↓
Evaluator
     ↓
matching document IDs
```

Do not feel required to create every class immediately. Separate responsibilities
when the current design becomes difficult to understand or test.

---

Requirements:

- Use one text-analysis component for documents and search terms.
- Treat punctuation as a word separator.
- Support `AND`, `OR`, and `NOT`.
- Allow boolean queries to be nested.
- Evaluate queries using the inverted index.
- Keep Level 1 behavior working.

The exact query API, invalid syntax behavior, result ordering, and edge cases are
your decisions.

---

For every level, add automated tests and be ready to explain your object model,
data structures, complexity, assumptions, and edge cases.

---

## Level 3 — Relevance ranking

Until now, search returned matching document IDs, but it did not tell us which
match was best.

Now add ranked search:

```python
engine.add("doc-1", "python search search engine")
engine.add("doc-2", "python web framework")
engine.add("doc-3", "distributed search engine")

engine.ranked_search("python search")
```

A possible result is:

```python
[
    SearchResult(document_id="doc-1", score=...),
    SearchResult(document_id="doc-2", score=...),
    SearchResult(document_id="doc-3", score=...),
]
```

`doc-1` should appear first because it contains both query words, and it contains
`search` more than once.

Results should be ordered from the highest score to the lowest score.

---

To calculate the score, use two ideas.

**Term frequency (TF)** asks:

```text
How many times does this word appear in this document?
```

If `search` appears twice in `doc-1`, its term frequency is `2`.

**Inverse document frequency (IDF)** asks:

```text
How rare is this word across all documents?
```

A rare word should contribute more to the score than a word found in almost
every document.

For each query word, calculate a TF-IDF value and add those values together to
produce the document's final score. Choose and document the exact formula.

---

Your current index probably looks conceptually like this:

```text
"search" → {"doc-1", "doc-3"}
```

That tells you which documents contain the word, but not how many times it
appears in each document.

You now need something closer to:

```text
"search"
    ├── "doc-1" → 2 occurrences
    └── "doc-3" → 1 occurrence
```

This is the main storage change in Level 3.

---

Requirements:

- `ranked_search(query)` accepts multiple words.
- Return a document ID and score for each result.
- Return higher-scoring documents first.
- Repeated query words in a document should affect its score.
- Rare words should be worth more than common words.
- Support returning only the top results.
- Use the index instead of reading every stored document.
- Existing term search and boolean queries should still work.

A basic result model could be:

```python
class SearchResult:
    document_id: str
    score: float
```

And the new API could look like:

```python
class SearchEngine:
    def ranked_search(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[SearchResult]:
        ...
```

The exact TF-IDF formula, class design, score rounding, tie-breaking behavior,
and edge cases are your decisions.

---

## Level 4 — Phrase and prefix queries

The engine can find individual words, but it cannot understand where those
words appear inside a document.

For example:

```python
engine.add("doc-1", "distributed search engine")
engine.add("doc-2", "search distributed engine")
engine.add("doc-3", "distributed fast search engine")
```

Now add phrase search:

```python
engine.phrase_search("distributed search")
# ["doc-1"]
```

`doc-1` matches because `distributed` is immediately followed by `search`.

`doc-2` contains both words, but in the wrong order. `doc-3` contains both
words, but another word appears between them.

---

Your current posting probably stores a frequency:

```text
"search"
    └── "doc-1" → 2 occurrences
```

Frequency does not tell you where those occurrences are. Phrase search needs
word positions:

```text
"search"
    └── "doc-1" → [1, 4]
```

A document can match `"distributed search"` when it contains:

```text
"distributed" → position 0
"search"      → position 1
```

For a phrase with more words, every next word must appear at the next position.

The posting structure now becomes conceptually:

```text
term
 └── document ID
      └── positions
```

Term frequency can now be calculated from the number of stored positions, so
the same structure can still support Level 3 ranking.

---

Also add prefix search. It finds all indexed words beginning with a prefix:

```python
engine.add("doc-4", "searching searchable content")

engine.prefix_search("sear")
# documents containing "search", "searching", or "searchable"
```

A normal term lookup only works when the complete term is known:

```text
index["search"]
```

Prefix search must first find all indexed terms beginning with `sear`, then
combine their document IDs.

Think about how the term dictionary should support this efficiently. Possible
directions include a sorted term collection or a trie. Choose one and explain
the tradeoff.

---

If you are using query objects, the model could grow to include:

```python
PhraseQuery("distributed search")
PrefixQuery("sear")
```

They should also be usable inside boolean queries:

```text
AND(PHRASE("distributed search"), NOT(PREFIX("legacy")))
```

The exact query-string syntax is your decision.

---

Requirements:

- Support exact phrase matching.
- Words in a phrase must be adjacent and in the same order.
- Store word positions in the inverted index.
- Keep relevance ranking working with the new posting structure.
- Support prefix queries over indexed terms.
- Avoid scanning every stored document.
- Allow phrase and prefix queries to participate in boolean queries.
- Keep all previous levels working.

Phrase normalization, empty prefixes, repeated words, duplicate matches,
prefix-query performance, result ordering, and other edge cases are your
decisions.

---

## Level 5 — Segments, deletion, and merging

Until now, every document has gone into one mutable index.

Now split the index into smaller pieces called **segments**. New documents go
into a writable buffer. Calling `flush()` turns that buffer into a read-only
segment and starts a new buffer.

Everything still lives in memory. Here, `flush()` does not mean writing to disk.

```python
engine.add("doc-1", "python search engine")
engine.add("doc-2", "python web framework")
engine.flush()

engine.add("doc-3", "distributed search engine")
```

The engine now contains:

```text
SearchEngine
 ├── Segment 1 — read-only
 │    ├── doc-1
 │    └── doc-2
 └── Writable buffer
      └── doc-3
```

Search should still find all three documents where appropriate, including
documents that have not been flushed:

```python
engine.search("search")
# ["doc-1", "doc-3"]
```

Call `flush()` again:

```text
SearchEngine
 ├── Segment 1 — doc-1, doc-2
 ├── Segment 2 — doc-3
 └── Writable buffer — empty
```

Each segment contains its own index data. Existing segments are not modified
when new documents arrive.

---

Now add document deletion:

```python
engine.delete("doc-1")

engine.search("search")
# ["doc-3"]
```

But `doc-1` lives inside a read-only segment. How can it disappear from search
without rewriting that segment?

Keep deletion information separately. This is often called a **tombstone**:
the document's data is still stored, but searches treat it as deleted.

Deletion should be visible immediately, including for documents still in the
writable buffer.

---

Over time, repeated flushes create many segments. Searches then have more pieces
to visit, and deleted documents still occupy space.

Add a merge operation:

```python
engine.merge_segments()
```

Conceptually:

```text
Before:
  Segment 1: doc-1 (deleted), doc-2
  Segment 2: doc-3

After:
  New segment: doc-2, doc-3
```

Build a new segment from the live documents' index data, then replace the old
segments. Do not modify the old segments in place or rebuild the index by
re-analyzing stored document text.

Search behavior should be the same before and after merging. Merging is
maintenance, not a change to the searchable documents.

---

Requirements:

- Add documents to a writable buffer.
- `flush()` turns buffered data into an immutable segment.
- Search across all segments and the current buffer.
- `delete(document_id)` immediately hides a document from every query type.
- Keep deletion state separate from immutable segment data.
- `merge_segments()` combines existing segments and removes deleted documents
  from the merged data.
- Preserve term positions, phrase matching, prefix matching, and ranking.
- Calculate ranking statistics across all live documents, not independently
  for each segment. Flushing or merging alone must not change scores.
- Keep the existing duplicate-ID rejection behavior for live documents.

A possible API addition is:

```python
class SearchEngine:
    def flush(self) -> None:
        ...

    def delete(self, document_id: str) -> None:
        ...

    def merge_segments(self) -> None:
        ...
```

The segment model, deletion bookkeeping, missing-ID behavior, reuse of deleted
IDs, empty operations, and other edge cases are your decisions.

**Do not worry about disk persistence, threads, or background merging yet.**

Add tests showing that query results survive flushes and merges, deleted
documents stay hidden, and ranking remains consistent across segment boundaries.

---

## Level 6 — Persistence and crash-safe commits

Everything disappears when the process exits. Now make committed index state
survive a restart.

Open an engine using a directory:

```python
engine = open_engine("./search-data")

engine.add("doc-1", "python search engine")
engine.add("doc-2", "distributed search")
engine.commit()
```

Create a new engine using the same directory:

```python
reopened = open_engine("./search-data")

reopened.search("search")
# ["doc-1", "doc-2"]
```

The new engine must recover the committed segments, live document IDs, and
deletion information. It should not need to analyze all stored document text
again.

`commit()` is the durability boundary. Changes made after the most recent
successful commit are not guaranteed to survive a process crash.

```python
engine.delete("doc-1")
engine.commit()

reopened = open_engine("./search-data")
reopened.search("search")
# ["doc-2"]
```

Committing must be atomic from the reader's perspective. If the process fails
partway through a commit, reopening the engine should observe either the
previous successful commit or the complete new commit—never a mixture of both.

The same rule applies when a merge replaces several old segments with a new
one. A crash must not leave the engine with missing or partially replaced
search data.

---

Requirements:

- Store immutable segments on disk.
- `commit()` makes the current searchable state durable, including buffered
  documents and deletions.
- Opening an existing index restores the most recent successful commit.
- Preserve exact, boolean, ranked, phrase, and prefix query behavior after a
  restart.
- Preserve external-to-internal document identity across restarts.
- Do not rebuild postings by re-analyzing document text during startup.
- A failed or interrupted commit must not corrupt the previous committed state.
- Merging and committing must not change query results or ranking scores.
- Two index directories should remain independent.

A possible API is:

```python
def open_engine(directory: str) -> SearchEngine:
    ...


class SearchEngine:
    def commit(self) -> None:
        ...

    def close(self) -> None:
        ...
```

The file format, directory layout, commit metadata, temporary files, startup
recovery, obsolete segment cleanup, empty commits, and corruption handling are
your design decisions.

**Do not worry about multiple processes, concurrent readers and writers,
memory-mapped files, compression, or a write-ahead log yet.**

Add restart tests that use a temporary directory. Also simulate failures at
different points during a commit and verify that reopening never exposes a
partially committed index.

---

## Level 7 — Concurrent indexing and searching

The engine currently assumes that one operation runs at a time. Now allow
multiple threads to use the same engine safely.

One thread may add documents while another searches:

```python
engine = open_engine("./search-data")

# Thread A
engine.add("doc-1", "python search engine")

# Thread B
engine.search("search")
```

Searching must never observe a partially indexed document. A query may run
before or after the add becomes visible, but its result must correspond to one
valid state of the index.

The same applies when maintenance runs concurrently:

```text
Thread A: search
Thread B: add and delete documents
Thread C: flush, merge, or commit
```

A query should use one consistent view of the segments, writable buffer,
live-document map, and tombstones. For example, ranking must not read postings
from one state and calculate corpus size from another state.

Immutable segments should help here: readers can retain an old segment while a
writer publishes a new segment list. Existing readers finish with their old
view; later readers receive the new one.

---

Requirements:

- Support concurrent calls from multiple threads in one process.
- A document must not become searchable until all its terms and positions are
  indexed.
- Deletion must become visible as one complete state change.
- Each query must use a consistent index view for matching and ranking.
- Flushing must not lose documents added around the buffer swap.
- Merging must not remove segments or tombstones created after the merge began.
- A commit persists one consistent snapshot. Changes outside that snapshot may
  be included in the next commit.
- Concurrent operations must not corrupt postings, tries, document maps,
  segment lists, or manifest files.
- Preserve all behavior and restart guarantees from previous levels.

Keep the public API unchanged:

```python
engine.add(document_id, text)
engine.delete(document_id)
engine.search(term)
engine.flush()
engine.merge_segments()
engine.commit()
```

Lock placement, snapshot representation, write serialization, merge retry
behavior, and operation visibility are your design decisions.

**Only support threads within one process. Do not worry about multiple writer
processes, distributed locks, background scheduling, or lock-free data
structures yet.**

Write deterministic concurrency tests using barriers or events to control when
operations pause and resume. Avoid tests that depend only on timing or
`sleep()`.
