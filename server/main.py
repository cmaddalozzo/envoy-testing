from http.server import BaseHTTPRequestHandler
import functools
import socketserver
import json
import argparse
from typing import List, Tuple
import logging
import mimetypes


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_PORT = 8000
DEFAULT_NAME = 'test-server'

class Handler(BaseHTTPRequestHandler):
    name: str
    return_code: int
    response_body: Tuple[str,bytes] | None
    custom_headers: List[Tuple[str, str]]
    log_request_body: bool
    def __init__(self, *args, name: str, return_code=200, headers=[], response_body=None, log_request_body=True):
        self.name = name
        self.return_code = return_code
        self.custom_headers = headers
        self.response_body = response_body
        self.log_request_body = log_request_body
        super().__init__(*args)

    def log_request_data(self):
        log.info("Headers: %s", ", ".join(f"{name}={value}" for name, value in self.headers.items()))
        if self.command == 'POST':
            body = self.read_body()
            if self.headers['content-type'].startswith('text') or self.headers['content-type'] == 'application/json':
                body = body.decode('utf-8')
            if self.log_request_body:
                log.info("Request: body=%s", body)

    def respond(self):
        response_code = self.get_response_code()
        if self.response_body is not None:
            mime_type, response_body = self.response_body
        else:
            mime_type = 'application/json'
            response_body = json.dumps({"status": response_code}).encode('utf-8')

        self.send_response(response_code)
        self.send_header('Content-type', mime_type)
        self.send_header('Content-length', str(len(response_body)))
        self.send_header('X-Handled-By', self.name)
        for header in self.custom_headers:
            self.send_header(*header)
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self) -> None:
        if self.path == '/health':
            self.return_code = 200
            self.response_body = ('application/json', json.dumps({"status": "ok"}).encode('utf-8'))
            return

        self.log_request_data()
        self.respond()

    def do_POST(self) -> None:
        self.log_request_data()
        self.respond()

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

    def get_response_code(self) -> int:
        response_code = self.return_code
        if 'x-response-code' in self.headers:
            header_code = self.headers['x-response-code']
            try:
                return int(header_code)
            except ValueError:
                pass

            codes = header_code.split(' ')
            header_map = {}
            for part in codes:
                name, value = part.split('=')
                header_map[name] = value
            return int(header_map.get(self.name, response_code))
        return response_code



if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Simple Python Webserver")
    parser.add_argument(
        '--name', 
        type=str, 
        default=DEFAULT_NAME,
        help=f'Name of the server (default: {DEFAULT_NAME})'
    )
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
    parser.add_argument(
        '--response-body-file',
        type=argparse.FileType('rb'),
        default=None,
        help=f'Content to return in response body'
    )
    parser.add_argument(
        '--log-request-body',
        type=bool,
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Log the request body to the console',
    )
    args = parser.parse_args()

    log = logging.getLogger(args.name)

    response_body = None

    log.info(args)

    if args.response_body_file is not None:
        content = args.response_body_file.read()
        mime_type, _ = mimetypes.guess_type(args.response_body_file.name)
        if mime_type == None:
            mime_type = 'text/plain'
            log.warn(f"Couldn't detect MIME type of file, defaulting to {mime_type}")
        response_body = (mime_type, content)

    handler_factory = functools.partial(Handler,
                                        name=args.name,
                                        return_code=args.return_code,
                                        headers=args.header,
                                        log_request_body=args.log_request_body,
                                        response_body=response_body)
    class MyTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    # Run the server with the specified or default port
    with MyTCPServer(("", args.port), handler_factory) as httpd:
        log.info(f"Started HTTP server: :{args.port}")
        httpd.serve_forever()
