import re


# Extract the current word/token at the cursor position
def get_word_at_position(params):
    document = params.textDocument.uri
    position = params.position
    # This is a simplified version - in a real implementation,
    # you would get the document text from a document manager
    # For now, we'll just extract from a line
    line_text = get_document_line(document, position.line)
    if not line_text:
        return None

    # Extract the word at the current position
    word_match = re.search(
        r"[\w_]+", line_text[max(0, position.character - 10) : position.character + 10]
    )
    if word_match:
        return word_match.group(0)

    return None


# Get a document line from the document store
def get_document_line(document_uri, line_number):
    """
    Get a specific line from a document.

    Args:
        document_uri: URI of the document
        line_number: Zero-based line number

    Returns:
        Line text or None if document not found or line out of range
    """
    from playwright_lsp.document_store import get_document_store

    store = get_document_store()
    document = store.get(document_uri)

    if document:
        return document.get_line(line_number)

    # If document not in store, return None
    return None
