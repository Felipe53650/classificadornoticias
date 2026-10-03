"""Verificação opcional em navegador: pip install playwright; utiliza Microsoft Edge."""
import argparse
from pathlib import Path
import socket
import threading
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect
import uvicorn
from src.api.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default="models/demo")
    parser.add_argument("--screenshots", default="docs/screenshots")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    screenshots = root / args.screenshots
    screenshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pauta-ui-") as temporary:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        app = create_app(str(root / args.model_dir), f"sqlite:///{(Path(temporary) / 'ui.db').as_posix()}")
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{port}"
            for _ in range(100):
                try:
                    with urllib.request.urlopen(url + "/health", timeout=1):
                        break
                except OSError:
                    if not thread.is_alive():
                        raise RuntimeError("Servidor de teste encerrou antes da inicialização.")
                    time.sleep(.2)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1050})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url)
                expect(page.locator("#analyze")).to_be_enabled()
                page.screenshot(path=str(screenshots / "editor-desktop.png"), full_page=True)
                page.locator("#title").fill("Banco Central anuncia taxa de juros")
                page.locator("#content").fill("O mercado acompanha a inflação, a moeda e o investimento na economia.")
                page.locator("#analyze").click()
                expect(page.locator("#analysis-result")).to_be_visible()
                expect(page.locator("#candidates li")).to_have_count(3)
                expect(page.locator("#save")).to_be_disabled()
                predicted = page.locator("#suggested-category").inner_text()
                alternatives = page.locator("#final-category option").all_text_contents()
                page.locator("#final-category").select_option(next(c for c in alternatives if c != predicted))
                page.locator("#confirmed").check()
                page.screenshot(path=str(screenshots / "analysis-desktop.png"), full_page=True)
                page.locator("#save").click()
                expect(page.locator("#message")).to_contain_text("Decisão salva")
                page.goto(url + "/history")
                expect(page.locator("#history-body tr")).to_have_count(1)
                expect(page.locator("#history-body")).to_contain_text("Corrigida")
                page.locator("#filter-correction").select_option("false")
                expect(page.locator("#history-body tr")).to_have_count(0)
                page.locator("#filter-correction").select_option("true")
                expect(page.locator("#history-body tr")).to_have_count(1)
                page.screenshot(path=str(screenshots / "history-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(url)
                expect(page.locator("#analyze")).to_be_enabled()
                page.locator("#title").fill("Notícia sobre futebol e campeonato")
                page.locator("#analyze").click()
                expect(page.locator("#analysis-result")).to_be_visible()
                page.locator("#content").fill("O texto mudou.")
                expect(page.locator("#analysis-result")).to_be_hidden()
                expect(page.locator("#save")).to_be_disabled()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "editor-mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Navegador: desktop, mobile, análise, confirmação, correção, histórico e invalidação aprovados.")
        finally:
            server.should_exit = True
            thread.join(timeout=10)


if __name__ == "__main__":
    main()
