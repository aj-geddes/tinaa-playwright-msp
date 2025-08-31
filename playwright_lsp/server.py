# Simple version of server.py that doesn't depend on pygls

from playwright_lsp.handlers.completion import get_playwright_completions
from playwright_lsp.handlers.diagnostics import find_missing_awaits
from playwright_lsp.handlers.hover import get_hover_response


# Simple server object
class SimpleServer:
    def __init__(self, name, version):
        self.name = name
        self.version = version

    def get_completions(self, params=None):
        return get_playwright_completions()

    def get_hover(self, params=None):
        return get_hover_response(params)

    def get_diagnostics(self, text):
        return find_missing_awaits(text)

    def start_io(self):
        print(f"Starting {self.name} v{self.version} in IO mode")

    def start_tcp(self, host, port):
        print(f"Starting {self.name} v{self.version} in TCP mode on {host}:{port}")


# Initialize the language server
server = SimpleServer("playwright-lsp", "v0.1")

# Start the language server
if __name__ == "__main__":
    server.start_io()
