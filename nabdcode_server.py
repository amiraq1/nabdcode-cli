import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from nabdcode.ui.console import ConsoleUI
from nabdcode.memory.vector_db import VectorDB
from nabdcode.core.agent import NabdAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NabdCodeServer")

# Initialize Agent once at startup
logger.info("Initializing NabdAgent...")
ui = ConsoleUI()
vector_db = VectorDB()
agent = NabdAgent(ui=ui, vector_db=vector_db)
logger.info("Agent initialized and ready.")

class NabdRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "ok", "message": "NabdCode Server is running"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                prompt = data.get("prompt", "")
                
                if not prompt:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Missing prompt parameter"}).encode('utf-8'))
                    return
                
                logger.info(f"Processing request: {prompt}")
                # Execute agent request synchronously
                response_text = agent.process_request_sync(prompt)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response_body = {"response": response_text}
                self.wfile.write(json.dumps(response_body).encode('utf-8'))
                
            except Exception as e:
                logger.error(f"Error handling post request: {e}", exc_info=True)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, NabdRequestHandler)
    logger.info(f"NabdCode API Server running on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        httpd.server_close()

if __name__ == '__main__':
    run()
