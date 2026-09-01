from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, order=True)
class DocumentRef:
    internal_id: UUID 
    external_id: str = field(compare=False)


class Document:
    def __init__(self, document_ref: DocumentRef, text: str):
        self.document_ref = document_ref
        self.text = text

    def external_id(self):
        return self.document_ref.external_id

    def internal_id(self):
        return self.document_ref.internal_id
