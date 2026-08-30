from index import InvertedIndex
from text_analyzer import Analyzer
from query import AndQuery, NotQuery, OrQuery, Query, QueryVisitor, TermQuery, PrefixQuery, PhraseQuery
from search_result import SearchResult
from math import log
from typing import Optional
from collections import defaultdict
from posting import Posting

class QueryEvaluator(QueryVisitor):
    def __init__(
        self,
        index: InvertedIndex,
        analyzer: Analyzer,
    ):
        self._index = index
        self._analyzer = analyzer

    def evaluate(self, query: Query) -> set[str]:
        return query.accept(self)

    def visit_term(self, query: TermQuery) -> set[str]:
        term: str = self._validate_single_term(query.term)
        return self._index.postings(term)

    def visit_not(self, query: NotQuery) -> set[str]:
        return set(self._index.document_ids()).difference(query.child.accept(self))
        

    def visit_and(self, query: AndQuery) -> set[str]:
        results = [child.accept(self) for child in query.children]
        return set.intersection(*results)

    def visit_or(self, query: OrQuery) -> set[str]:
        results = [child.accept(self) for child in query.children]
        return set.union(*results)

    def visit_prefix(self, query: PrefixQuery) -> set[str]:
        term: str = self._validate_single_term(query.prefix)
        return self._index.prefix_search(term)

    def evaluate_ranked(self, query: str, limit: Optional[int] = None) -> list[SearchResult]:
        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")

        terms: list[str] = self._analyzer.analyze(query)
        corpus_size = len(self._index.document_ids())
        document_scores: dict[str, float] = defaultdict(float)

        for term in terms:
            posting = self._index.get_posting(term)
            document_frequency = posting.document_frequency()

            for document_id in posting.document_ids():
                document_scores[document_id] += self.calculate_score(
                    frequency=posting.frequency(document_id),
                    num_docs_appearing=document_frequency,
                    corpus_size=corpus_size,
                )

        results = [
            SearchResult(document_id, score)
            for document_id, score in document_scores.items()
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

    def visit_phrase(self, query: PhraseQuery) -> set[str]:
        terms: list[str] = self._analyzer.analyze(query.phrase)
        postings: dict[str, Posting] = {}

        for term in terms:
            postings[term] = self._index.get_posting(term)

        postings_sets = [posting.document_ids() for posting in postings.values()]
        document_ids = set.intersection(*postings_sets) if postings_sets else set()

        result: set[str] = set()
        for document_id in document_ids:
            if self._matches_phrase(terms, postings, document_id):
                result.add(document_id)

        return result

    def _matches_phrase(
        self,
        terms: list[str],
        postings: dict[str, Posting],
        document_id: str,
    ) -> bool:
        positions = {}
        term_and_counts = []

        for offset, term in enumerate(terms):
            posting = postings[term]
            positions[term] = posting.positions(document_id)
            frequency = posting.frequency(document_id)

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

            