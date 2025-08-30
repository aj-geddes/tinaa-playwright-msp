# Simple version of hover.py that doesn't depend on pygls.lsp.types

from playwright_lsp.utils.ast_utils import get_word_at_position
from playwright_lsp.utils.playwright_docs import PLAYWRIGHT_DOCS


# Provide hover documentation for recognized Playwright terms
def get_hover_response(params):
    word = get_word_at_position(params)
    doc = PLAYWRIGHT_DOCS.get(word)
    if doc:
        # Return a simple dictionary instead of a Hover object
        return {"contents": {"kind": "markdown", "value": doc}}
    return None