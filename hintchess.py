import json
import subprocess
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# CHANGE THIS TO YOUR REAL STOCKFISH PATH
STOCKFISH_PATH = r"C:\Users\oweng\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"

HOST = "127.0.0.1"
PORT = 8765

engine_lock = threading.Lock()


class StockfishEngine:
    def __init__(self, path):
        self.engine = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        self.send("uci")
        self.wait_for("uciok")

        self.send("isready")
        self.wait_for("readyok")

    def send(self, command):
        self.engine.stdin.write(command + "\n")
        self.engine.stdin.flush()

    def wait_for(self, target):
        while True:
            line = self.engine.stdout.readline().strip()
            if line == target:
                return

    def get_best_move(self, fen, movetime=600):
        with engine_lock:
            self.send("ucinewgame")
            self.send("isready")
            self.wait_for("readyok")

            self.send(f"position fen {fen}")
            self.send(f"go movetime {movetime}")

            while True:
                line = self.engine.stdout.readline().strip()

                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
                    return None


engine = StockfishEngine(STOCKFISH_PATH)


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.add_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/best":
            self.send_json({"error": "Use /best?fen=..."}, 404)
            return

        query = urllib.parse.parse_qs(parsed.query)
        fen = query.get("fen", [""])[0]

        if not fen:
            self.send_json({"error": "Missing FEN"}, 400)
            return

        try:
            bestmove = engine.get_best_move(fen)

            self.send_json({
                "fen": fen,
                "bestmove": bestmove
            })

        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def add_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Type", "application/json")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.add_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print("Stockfish bot hint server is running.")
    print(f"Open test link: http://{HOST}:{PORT}/best?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20-%20-%200%201")
    print("Keep this window open.")
    HTTPServer((HOST, PORT), Handler).serve_forever()