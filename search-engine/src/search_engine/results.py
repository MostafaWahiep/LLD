from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    score: float
