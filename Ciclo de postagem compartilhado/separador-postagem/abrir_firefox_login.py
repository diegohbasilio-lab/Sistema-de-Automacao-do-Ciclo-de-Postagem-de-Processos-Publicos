from pathlib import Path
from playwright.sync_api import sync_playwright


URL_SITE = "https://licitacoeseb.4rm.eb.mil.br/home"
PASTA_SCRIPT = Path(__file__).parent
PASTA_PERFIL_FIREFOX = PASTA_SCRIPT / "robo_licitacoeseb_playwright_firefox_perfil_atual"


with sync_playwright() as p:
    opcoes_firefox = {
        "user_data_dir": str(PASTA_PERFIL_FIREFOX),
        "headless": False,
        "viewport": {"width": 1600, "height": 900},
        "accept_downloads": True,
        "ignore_https_errors": True,
        "firefox_user_prefs": {
            "browser.sessionstore.resume_from_crash": False,
            "browser.startup.page": 0,
        },
    }

    context = p.firefox.launch_persistent_context(**opcoes_firefox)

    page = context.new_page()
    page.goto(URL_SITE)

    input("Faca o login no navegador aberto. Depois de confirmar que entrou, pressione ENTER aqui...")

    context.close()
