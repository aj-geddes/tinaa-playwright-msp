"""
Simple document store for LSP server

Maintains in-memory cache of document contents for LSP operations.
"""


class Document:
    """Represents a text document in the workspace."""

    def __init__(self, uri: str, text: str = "", version: int = 0):
        """
        Initialize a document.

        Args:
            uri: Document URI
            text: Document text content
            version: Document version number
        """
        self.uri = uri
        self.version = version
        self._text = text
        self._lines: list[str] | None = None

    @property
    def text(self) -> str:
        """Get document text."""
        return self._text

    @text.setter
    def text(self, value: str):
        """Set document text and invalidate cached lines."""
        self._text = value
        self._lines = None

    @property
    def lines(self) -> list[str]:
        """Get document lines (cached)."""
        if self._lines is None:
            self._lines = self._text.splitlines()
        return self._lines

    def get_line(self, line_number: int) -> str | None:
        """
        Get a specific line from the document.

        Args:
            line_number: Zero-based line number

        Returns:
            Line text or None if line number is out of range
        """
        if 0 <= line_number < len(self.lines):
            return self.lines[line_number]
        return None

    def update(self, text: str, version: int):
        """
        Update document content.

        Args:
            text: New document text
            version: New version number
        """
        self.text = text
        self.version = version


class DocumentStore:
    """Manages all open documents in the workspace."""

    def __init__(self):
        """Initialize empty document store."""
        self._documents: dict[str, Document] = {}

    def open(self, uri: str, text: str, version: int = 0) -> Document:
        """
        Open a document and add it to the store.

        Args:
            uri: Document URI
            text: Document text content
            version: Document version

        Returns:
            The opened document
        """
        document = Document(uri, text, version)
        self._documents[uri] = document
        return document

    def close(self, uri: str) -> None:
        """
        Close a document and remove it from the store.

        Args:
            uri: Document URI
        """
        if uri in self._documents:
            del self._documents[uri]

    def get(self, uri: str) -> Document | None:
        """
        Get a document by URI.

        Args:
            uri: Document URI

        Returns:
            Document or None if not found
        """
        return self._documents.get(uri)

    def update(self, uri: str, text: str, version: int) -> Document | None:
        """
        Update an existing document.

        Args:
            uri: Document URI
            text: New document text
            version: New version number

        Returns:
            Updated document or None if document not found
        """
        document = self.get(uri)
        if document:
            document.update(text, version)
        return document

    def has(self, uri: str) -> bool:
        """
        Check if a document exists in the store.

        Args:
            uri: Document URI

        Returns:
            True if document exists, False otherwise
        """
        return uri in self._documents

    def all_uris(self) -> list[str]:
        """
        Get all document URIs in the store.

        Returns:
            List of document URIs
        """
        return list(self._documents.keys())


# Global document store instance
_document_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    """Get the global document store instance."""
    global _document_store
    if _document_store is None:
        _document_store = DocumentStore()
    return _document_store
