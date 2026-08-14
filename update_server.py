"""Azra Converter güncelleme dosyalarını bu bilgisayardan dağıtır."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PORT = 8765
UPDATES_FOLDER = Path(__file__).resolve().parent / "updates"


class UpdateHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    UPDATES_FOLDER.mkdir(exist_ok=True)
    handler = partial(UpdateHandler, directory=str(UPDATES_FOLDER))
    server = ThreadingHTTPServer(("0.0.0.0", PORT), handler)
    print(f"Güncelleme sunucusu çalışıyor: http://0.0.0.0:{PORT}")
    print(f"Paylaşılan klasör: {UPDATES_FOLDER}")
    print("Durdurmak için Ctrl+C tuşlarına basın.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu durduruldu.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
