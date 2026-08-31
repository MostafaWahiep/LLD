from document_ref import DocumentRef

class Document:
    def __init__(self, document_ref: DocumentRef, text: str):
        self.document_ref = document_ref
        self.text = text

    def external_id(self):
        return self.document_ref.external_id

    def internal_id(self):
        return self.document_ref.internal_id