from http.server import SimpleHTTPRequestHandler
import functools
import socketserver
import json
import argparse
from typing import List, Tuple
import logging


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_PORT = 8000

class Handler(SimpleHTTPRequestHandler):
    return_code: int
    custom_headers: List[Tuple[str, str]]
    def __init__(self, *args, return_code=200, headers=[]):
        self.return_code = return_code
        self.custom_headers = headers
        super().__init__(*args)

    def log_request_data(self):
        log.info("Headers: %s", ", ".join(f"{name}={value}" for name, value in self.headers.items()))
        log.info("Request: body=%s", self.read_body().decode('utf8'))

    def do_GET(self) -> None:
        self.log_request_data()
        # Send response status code
        self.send_response(self.return_code)

        output = json.dumps({"status": self.return_code}).encode('utf-8')
        # Send headers
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-length', str(len(output)))
        for header in self.custom_headers:
            self.send_header(*header)
        self.end_headers()
        self.wfile.write(output)

    def do_POST(self) -> None:
        self.log_request_data()
        # Send response status code
        self.send_response(self.return_code)

        output = json.dumps({"status": self.return_code}).encode('utf-8')
        # Send headers
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-length', str(len(output)))
        for header in self.custom_headers:
            self.send_header(*header)
        self.end_headers()
        self.wfile.write(output)

    def read_body(self) -> bytes:
        body = b""
        if "Content-Length" in self.headers:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
        elif "chunked" in self.headers.get("Transfer-Encoding", ""):
            while True:
                line = self.rfile.readline().strip()
                chunk_length = int(line, 16)

                if chunk_length != 0:
                    body += self.rfile.read(chunk_length)

                # Each chunk is followed by an additional empty newline
                # that we have to consume.
                self.rfile.readline()

                # Finally, a chunk size of 0 is an end indication
                if chunk_length == 0:
                    break
        return body


if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Simple Python Webserver")
    parser.add_argument(
        '--port', 
        type=int, 
        default=DEFAULT_PORT, 
        help=f'Specify the port to listen on (default: {DEFAULT_PORT})'
    )
    parser.add_argument(
        '--return-code',
        type=int,
        default=200,
        help=f'The status code to return'
    )
    parser.add_argument(
        '--header',
        type=lambda v: [s.strip() for s in v.split(':')],
        default=[],
        action='append',
        help=f'Header to send in response'
    )
    args = parser.parse_args()

    handler_factory = functools.partial(Handler, return_code=args.return_code, headers=args.header)
    class MyTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    # Run the server with the specified or default port
    with MyTCPServer(("", args.port), handler_factory) as httpd:
        log.info(f"Started HTTP server: :{args.port}")
        httpd.serve_forever()
