from index import Index
from text_analyzer import Analyzer
from query import AndQuery, NotQuery, OrQuery, Query, QueryVisitor, TermQuery, PrefixQuery, PhraseQuery
from search_result import SearchResult
from math import log
from typing import Optional
from collections import defaultdict
from posting import Posting
from document import Document
from document import DocumentRef

class QueryEvaluator(QueryVisitor):
    def __init__(
        self,
        index: Index,
        analyzer: Analyzer,
    ):
        self._index = index
        self._analyzer = analyzer

    def evaluate(self, query: Query) -> set[DocumentRef]:
        return query.accept(self)

    def visit_term(self, query: TermQuery) -> set[DocumentRef]:
        term: str = self._validate_single_term(query.term)
        return self._index.postings(term)

    def visit_not(self, query: NotQuery) -> set[DocumentRef]:
        return set(self._index.document_refs()).difference(query.child.accept(self))
        
    def visit_and(self, query: AndQuery) -> set[DocumentRef]:
        results = [child.accept(self) for child in query.children]
        return set.intersection(*results)

    def visit_or(self, query: OrQuery) -> set[DocumentRef]:
        results = [child.accept(self) for child in query.children]
        return set.union(*results)

    def visit_prefix(self, query: PrefixQuery) -> set[DocumentRef]:
        term: str = self._validate_single_term(query.prefix)
        return self._index.prefix_search(term)

    def evaluate_ranked(self, query: str, limit: Optional[int] = None) -> list[SearchResult]:
        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")

        terms: list[str] = self._analyzer.analyze(query)
        corpus_size = len(self._index.document_refs())
        document_scores: dict[Document, float] = defaultdict(float)

        for term in terms:
            posting = self._index.get_posting(term)
            document_frequency = posting.document_frequency()

            for document_ref in posting.document_refs():
                document_scores[document_ref] += self.calculate_score(
                    frequency=posting.frequency(document_ref),
                    num_docs_appearing=document_frequency,
                    corpus_size=corpus_size,
                )

        results = [
            SearchResult(document_ref.external_id, score)
            for document_ref, score in document_scores.items()
        ]

        results.sort(key=lambda result: (-result.score, result.document_id))

        if limit is not None:
            return results[:limit]

        return results

    def calculate_score(
            self,
            frequency: int,
            num_docs_appearing: int,
            corpus_size: int
        ) -> float:
        term_frequency = 1 + log(frequency)
        inverse_document_frequency = log((1+corpus_size) / (1+num_docs_appearing)) + 1
        return term_frequency * inverse_document_frequency


    def _validate_single_term(self, term: str) -> str:
        terms: list[str] = self._analyzer.analyze(term)
                
        if len(terms) != 1:
            raise ValueError(
                "A term query must contain exactly one searchable word"
            )

        return terms[0]

    def visit_phrase(self, query: PhraseQuery) -> set[DocumentRef]:
        terms: list[str] = self._analyzer.analyze(query.phrase)
        postings: dict[str, Posting] = {}

        for term in terms:
            postings[term] = self._index.get_posting(term)

        postings_sets: set[str] = [posting.document_refs() for posting in postings.values()]
        document_refs: set[DocumentRef] = set.intersection(*postings_sets) if postings_sets else set()

        result: set[str] = set()
        for document_ref in document_refs:
            if self._matches_phrase(terms, postings, document_ref):
                result.add(document_ref)

        return result

    def _matches_phrase(
        self,
        terms: list[str],
        postings: dict[str, Posting],
        document_ref: DocumentRef,
    ) -> bool:
        positions = {}
        term_and_counts = []

        for offset, term in enumerate(terms):
            posting = postings[term]
            positions[term] = posting.positions(document_ref)
            frequency = posting.frequency(document_ref)

            term_and_counts.append(
                (term, frequency, offset)
            )

        term_and_counts.sort(key=lambda x: x[1])

        anchor_term, _, anchor_offset = term_and_counts[0]
        for position in positions[anchor_term]:
            phrase_start = position - anchor_offset

            if all(
                    phrase_start + term_offset in positions[term]
                    for term, _, term_offset in term_and_counts[1:]
            ):
                return True
            
        return False

            