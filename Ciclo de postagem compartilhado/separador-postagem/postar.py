from pathlib import Path
import os
import re
import json
import unicodedata
import time
import shutil
from datetime import datetime
from pypdf import PdfReader
from playwright.sync_api import sync_playwright


def primeiro_caminho_existente(caminhos):
    for caminho in caminhos:
        caminho = Path(caminho)
        if caminho.exists():
            return caminho

    return None


# =========================
# CONFIGURAÇÕES PRINCIPAIS
# =========================
# cd desktop
# cd separador-postagem
# python postar.py

URL_SITE = "https://licitacoeseb.4rm.eb.mil.br/home"
URL_UNIDADES_GESTORAS = "https://licitacoeseb.4rm.eb.mil.br/community-list"

# Se existir uma pasta "processos_separados" ao lado deste arquivo, usa ela.
# Caso contrario, usa a propria pasta do postar.py, que e a estrutura atual.
PASTA_SCRIPT = Path(__file__).parent
PASTA_PROCESSOS_SEPARADOS = PASTA_SCRIPT / "processos_separados"
PASTA_BASE = PASTA_PROCESSOS_SEPARADOS if PASTA_PROCESSOS_SEPARADOS.exists() else PASTA_SCRIPT
PASTA_TEMP_UPLOAD = PASTA_SCRIPT / "_upload_temp"

PASTA_PERFIL_CHROME = PASTA_SCRIPT / "robo_licitacoeseb_chrome_perfil"
PASTA_PERFIL_FIREFOX = PASTA_SCRIPT / "robo_licitacoeseb_playwright_firefox_perfil_atual"

CAMINHO_CHROME = primeiro_caminho_existente([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
])

ARQUIVO_CONTROLE = PASTA_BASE / "postados_teste.json"
ARQUIVO_CREDENCIAIS = PASTA_SCRIPT / "credenciais_login.json"

LOGIN_EMAIL_FIXO = None
LOGIN_SENHA_FIXA = None

UG_OBRIGATORIA = "160109 - 4ª Cia Com L Mth"
ANO_OBRIGATORIO = "Ano 2026 - 4ª Cia Com L Mth"

SETOR_PADRAO = "Almox"
OM_PADRAO = "4ª Cia Com L Mth"

# Se True, pede confirmação antes de clicar em Depositar.
CONFIRMAR_ANTES_DEPOSITAR = False

# Se quiser testar sem depositar, coloque False.
CLICAR_DEPOSITAR = True

# Quando o site derruba a sessão, o robô fecha o navegador e tenta o mesmo PDF de novo.
MAX_TENTATIVAS_RELOGIN = 5
TAMANHO_MAXIMO_PDF_MB = 10


MAPEAMENTO = {
    "processo_dispensa": {
        "categoria_site": "1.1. Dispensa Eletrônica e Dispensa de Licitação - 4ª Cia Com L Mth",
        "tipo": "dispensa",
    },
    "processo_inexigibilidade": {
        "categoria_site": "1.2. Inexigibilidade de Licitação - 4ª Cia Com L Mth",
        "tipo": "inexigibilidade",
    },
    "processo_participante": {
        "categoria_site": "2.1.1 Participante - 4ª Cia Com L Mth",
        "tipo": "participante",
    },
    "processo_adesao": {
        "categoria_site": "2.1.2 Não Participante - 4ª Cia Com L Mth",
        "tipo": "carona",
    },
    "processo_gerenciador": {
        "categoria_site": "2.1.3 Gerenciador - 4ª Cia Com L Mth",
        "tipo": "gerenciador",
    },
    "processo_pregao": {
        "categoria_site": "2.1.4 Pregão - 4ª Cia Com L Mth",
        "tipo": "pregao",
    },
}

CATEGORIAS_ARVORE = {
    "dispensa": [
        "1.1. Dispensa Eletrônica e Dispensa de Licitação",
        "1.1. Dispensa Eletronica e Dispensa de Licitacao",
    ],
    "inexigibilidade": [
        "1.2. Inexigibilidade de Licitação",
        "1.2. Inexigibilidade de Licitacao",
    ],
    "participante": [
        "2.1.1 Participante",
    ],
    "carona": [
        "2.1.2 Não Participante",
        "2.1.2 Nao Participante",
    ],
    "gerenciador": [
        "2.1.3 Gerenciador",
    ],
    "pregao": [
        "2.1.4 Pregão",
        "2.1.4 Pregao",
    ],
}


# =========================
# FUNÇÕES DE EXTRAÇÃO
# =========================

def ler_texto_pdf(caminho_pdf: Path) -> str:
    texto = []

    try:
        reader = PdfReader(str(caminho_pdf))
        for page in reader.pages:
            conteudo = page.extract_text() or ""
            texto.append(conteudo)
    except Exception as erro:
        print(f"[ERRO] Não foi possível ler o PDF: {caminho_pdf.name}")
        print(erro)

    return "\n".join(texto)


def contar_paginas_pdf(caminho_pdf: Path) -> int:
    try:
        reader = PdfReader(str(caminho_pdf))
        return len(reader.pages)
    except Exception:
        return 0


def extrair_numero_die_x_nome(nome_arquivo: str) -> str:
    padroes = [
        r"DIEX\s*[Nnº°]*\s*[-:]?\s*(\d+)[\/\-](\d{4})",
        r"DIEx\s*[Nnº°]*\s*[-:]?\s*(\d+)[\/\-](\d{4})",
        r"DIE[Xx]\s*(\d+)[\/\-](\d{4})",
        r"(\d+)[\/\-](\d{4})",
    ]

    for padrao in padroes:
        achou = re.search(padrao, nome_arquivo, flags=re.IGNORECASE)
        if achou:
            return f"{achou.group(1)}/{achou.group(2)}"

    achou = re.match(r"^\s*(\d+)\s*-", Path(nome_arquivo).stem)
    if achou:
        return f"{achou.group(1)}/2026"

    return "0/2026"


def extrair_numero_dispensa(texto_pdf: str) -> str:
    padroes = [
        r"Dispensa\s+Eletrônica\s*[Nnº°]*\s*(\d+)[\/\-](\d{4})",
        r"Dispensa\s+de\s+Licitação\s*[Nnº°]*\s*(\d+)[\/\-](\d{4})",
        r"Dispensa\s*[Nnº°]*\s*(\d+)[\/\-](\d{4})",
    ]

    for padrao in padroes:
        achou = re.search(padrao, texto_pdf, flags=re.IGNORECASE)
        if achou:
            return f"{achou.group(1)}/{achou.group(2)}"

    return "00/2026"


def extrair_srp(texto_pdf: str) -> str:
    padroes = [
        r"SRP\s*[Nnº°]*\s*(\d+)[\/\-](\d{4})",
        r"Pregão\s*[Nnº°]*\s*(\d+)[\/\-](\d{4})",
        r"Pregão\s+Eletrônico\s*[Nnº°]*\s*(\d+)[\/\-](\d{4})",
    ]

    for padrao in padroes:
        achou = re.search(padrao, texto_pdf, flags=re.IGNORECASE)
        if achou:
            return f"{achou.group(1)}/{achou.group(2)}"

    return "00/2026"


def extrair_ug(texto_pdf: str) -> str:
    padroes = [
        r"UG[:\s]+(\d{6})",
        r"UASG[:\s]+(\d{6})",
        r"Unidade\s+Gestora[:\s]+(\d{6})",
    ]

    for padrao in padroes:
        achou = re.search(padrao, texto_pdf, flags=re.IGNORECASE)
        if achou:
            return achou.group(1)

    return "000000"


def extrair_nota_empenho(texto_pdf: str, nome_arquivo: str) -> str:
    texto_total = nome_arquivo + "\n" + texto_pdf

    padroes = [
        r"20\d{2}NE\d{6}",
        r"20\d{2}\s*NE\s*\d{6}",
    ]

    for padrao in padroes:
        achou = re.search(padrao, texto_total, flags=re.IGNORECASE)
        if achou:
            return re.sub(r"\s+", "", achou.group(0)).upper()

    return "2026NE000000"


def extrair_descricao_curta(nome_arquivo: str) -> str:
    nome = Path(nome_arquivo).stem
    partes = re.split(r"\s+-\s+| – | — ", nome)

    if len(partes) >= 2:
        return partes[-1].strip()

    return nome.strip()


def montar_metadados(caminho_pdf: Path, tipo: str) -> dict:
    texto_pdf = ler_texto_pdf(caminho_pdf)
    paginas = contar_paginas_pdf(caminho_pdf)

    nome_arquivo = caminho_pdf.name
    descricao_curta = extrair_descricao_curta(nome_arquivo)

    diex = extrair_numero_die_x_nome(nome_arquivo)
    dispensa = extrair_numero_dispensa(texto_pdf)
    srp = extrair_srp(texto_pdf)
    ug = extrair_ug(texto_pdf)
    ne = extrair_nota_empenho(texto_pdf, nome_arquivo)

    hoje = datetime.now()

    if tipo == "dispensa":
        nome_colecao = f"Dispensa eletrônica nº {dispensa} – {SETOR_PADRAO} - {OM_PADRAO}"
        titulo_item = f"Vol I - Fl. 1 a {paginas} - {ne}"

    elif tipo == "participante":
        nome_colecao = f"Diex nº {diex} – {SETOR_PADRAO} - {OM_PADRAO}"
        titulo_item = f"Vol I - Fl. 1 a {paginas} - SRP {srp} UG: {ug} - {ne}"

    elif tipo == "carona":
        nome_colecao = f"Diex nº {diex} – {SETOR_PADRAO} - {OM_PADRAO}"
        titulo_item = f"Vol I - Fl. 1 a {paginas} - SRP {srp} UG: {ug} - {ne}"

    elif tipo == "gerenciador":
        nome_colecao = f"Diex nº {diex} – {SETOR_PADRAO} - {OM_PADRAO}"
        titulo_item = f"Vol I - Fl. 1 a {paginas} - SRP {srp} - {ne}"

    
    elif tipo == "pregao":
        nome_colecao = f"Pregão {srp} - {OM_PADRAO}"
        titulo_item = f"Vol I - Fl. 1 a {paginas} - SRP {srp} - {ne}"
    elif tipo == "inexigibilidade":
        nome_colecao = f"Inexigibilidade nº {diex} – {SETOR_PADRAO} - {OM_PADRAO}"
        titulo_item = f"Vol I - Fl. 1 a {paginas} - {ne}"

    else:
        nome_colecao = f"Diex nº {diex} – {SETOR_PADRAO} - {OM_PADRAO}"
        titulo_item = f"Vol I - Fl. 1 a {paginas} - {ne}"

    return {
        "arquivo": caminho_pdf,
        "tipo": tipo,
        "paginas": paginas,
        "descricao_curta": descricao_curta,
        "diex": diex,
        "dispensa": dispensa,
        "srp": srp,
        "ug": ug,
        "ne": ne,
        "nome_colecao": nome_colecao,
        "titulo_item": titulo_item,
        "ano": f"{hoje.year:04d}",
        "mes": f"{hoje.month:02d}",
        "dia": f"{hoje.day:02d}",
    }


# =========================
# CONTROLE DE POSTADOS
# =========================

def carregar_controle() -> dict:
    if ARQUIVO_CONTROLE.exists():
        try:
            return json.loads(ARQUIVO_CONTROLE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def salvar_controle(controle: dict):
    ARQUIVO_CONTROLE.write_text(
        json.dumps(controle, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )


def ja_postado(caminho_pdf: Path) -> bool:
    if "POSTADO" in caminho_pdf.stem.upper():
        return True
    if "PULADO" in caminho_pdf.stem.upper():
        return True

    controle = carregar_controle()
    arquivos_pulados = {
        item.get("arquivo") if isinstance(item, dict) else str(item)
        for item in controle.get("pulados", [])
    }

    return (
        str(caminho_pdf) in controle.get("postados", [])
        or str(caminho_pdf) in arquivos_pulados
    )


def registrar_postado(caminho_pdf: Path):
    controle = carregar_controle()
    controle.setdefault("postados", [])

    if str(caminho_pdf) not in controle["postados"]:
        controle["postados"].append(str(caminho_pdf))

    salvar_controle(controle)


def registrar_pulado(caminho_pdf: Path, motivo: str):
    controle = carregar_controle()
    controle.setdefault("pulados", [])

    registro = {
        "arquivo": str(caminho_pdf),
        "motivo": motivo,
    }

    arquivos_pulados = {
        item.get("arquivo") if isinstance(item, dict) else str(item)
        for item in controle["pulados"]
    }

    if str(caminho_pdf) not in arquivos_pulados:
        controle["pulados"].append(registro)

    salvar_controle(controle)


def caminho_longo_windows(caminho: Path):
    if os.name != "nt":
        return caminho

    texto = str(caminho.resolve())
    if texto.startswith("\\\\?\\"):
        return texto
    return "\\\\?\\" + texto


def renomear_arquivo_seguro(origem: Path, destino: Path):
    try:
        origem.rename(destino)
        return
    except FileNotFoundError:
        if os.name != "nt":
            raise

    os.rename(caminho_longo_windows(origem), caminho_longo_windows(destino))


def simplificar_nome_pdf(nome: str, limite=170) -> str:
    substituicoes = [
        (r"g[eê]neros?\s+aliment[ií]cios?", "gen almt"),
        (r"material\s+permanente", "mat perm"),
        (r"material\s+de\s+consumo", "mat cons"),
        (r"dispensa\s+de\s+licita[cç][aã]o", "disp lic"),
        (r"prorroga[cç][aã]o\s+contratual", "prorr contrat"),
        (r"processo\s+de\s+carona", "carona"),
        (r"por\s+processo\s+de\s+carona", "por carona"),
        (r"requisi[cç][aã]o", "req"),
        (r"aquisi[cç][aã]o", "aqs"),
        (r"servi[cç]o", "sv"),
        (r"equipamentos?", "equip"),
        (r"fotogr[aá]fica", "foto"),
        (r"aliment[ií]cios?", "almt"),
        (r"com[eé]rcio", "com"),
        (r"companhia", "cia"),
        (r"contrata[cç][aã]o", "contrat"),
        (r"administrativo", "adm"),
        (r"fiscaliza[cç][aã]o", "fisc"),
        (r"manuten[cç][aã]o", "manut"),
        (r"lavanderia", "lavand"),
    ]

    nome_simplificado = unicodedata.normalize("NFD", nome)
    nome_simplificado = "".join(
        caractere for caractere in nome_simplificado
        if unicodedata.category(caractere) != "Mn"
    )
    for padrao, abreviado in substituicoes:
        nome_simplificado = re.sub(padrao, abreviado, nome_simplificado, flags=re.IGNORECASE)

    nome_simplificado = re.sub(r"\s+", " ", nome_simplificado)
    nome_simplificado = re.sub(r"\s+-\s+", " - ", nome_simplificado)
    nome_simplificado = re.sub(r"\s+", " ", nome_simplificado).strip(" -")

    if len(nome_simplificado) > limite:
        nome_simplificado = nome_simplificado[:limite].rstrip(" -")

    return nome_simplificado or nome[:limite].rstrip(" -")


def renomear_pdf_postado(caminho_pdf: Path) -> Path:
    if "POSTADO" in caminho_pdf.stem.upper():
        return caminho_pdf

    if not caminho_pdf.exists():
        print(f"[AVISO] Arquivo nao existe para renomear como POSTADO: {caminho_pdf}")
        return caminho_pdf

    nome_base = simplificar_nome_pdf(caminho_pdf.stem)
    novo_nome = f"{nome_base} - POSTADO{caminho_pdf.suffix}"
    novo_caminho = caminho_pdf.with_name(novo_nome)

    contador = 2
    while novo_caminho.exists():
        novo_nome = f"{nome_base} - POSTADO {contador}{caminho_pdf.suffix}"
        novo_caminho = caminho_pdf.with_name(novo_nome)
        contador += 1

    renomear_arquivo_seguro(caminho_pdf, novo_caminho)
    print(f"[OK] Arquivo renomeado para: {novo_caminho.name}")
    return novo_caminho


def renomear_pdf_pulado(caminho_pdf: Path) -> Path:
    if "PULADO" in caminho_pdf.stem.upper():
        return caminho_pdf

    if not caminho_pdf.exists():
        print(f"[AVISO] Arquivo nao existe para renomear como PULADO: {caminho_pdf}")
        return caminho_pdf

    nome_base = simplificar_nome_pdf(caminho_pdf.stem)
    novo_nome = f"{nome_base} - PULADO{caminho_pdf.suffix}"
    novo_caminho = caminho_pdf.with_name(novo_nome)

    contador = 2
    while novo_caminho.exists():
        novo_nome = f"{nome_base} - PULADO {contador}{caminho_pdf.suffix}"
        novo_caminho = caminho_pdf.with_name(novo_nome)
        contador += 1

    renomear_arquivo_seguro(caminho_pdf, novo_caminho)
    print(f"[PULADO] Arquivo renomeado para: {novo_caminho.name}")
    return novo_caminho


def marcar_pdf_pulado(caminho_pdf: Path, motivo: str) -> Path:
    registrar_pulado(caminho_pdf, motivo)
    novo_pdf = renomear_pdf_pulado(caminho_pdf)
    registrar_pulado(novo_pdf, motivo)
    return novo_pdf


def preparar_pdf_para_postagem(caminho_pdf: Path) -> Path:
    if not caminho_pdf.exists():
        raise FileNotFoundError(f"PDF nao encontrado: {caminho_pdf}")

    if len(str(caminho_pdf)) < 240:
        return caminho_pdf

    PASTA_TEMP_UPLOAD.mkdir(parents=True, exist_ok=True)
    destino = PASTA_TEMP_UPLOAD / caminho_pdf.name

    try:
        precisa_copiar = (
            not destino.exists()
            or destino.stat().st_size != caminho_pdf.stat().st_size
            or int(destino.stat().st_mtime) != int(caminho_pdf.stat().st_mtime)
        )

        if precisa_copiar:
            origem = caminho_pdf
            if os.name == "nt":
                origem = "\\\\?\\" + str(caminho_pdf.resolve())
            shutil.copy2(origem, destino)

        print(f"[INFO] Usando copia temporaria com caminho curto para upload: {destino.name}")
        return destino
    except Exception as erro:
        raise FileNotFoundError(f"Nao consegui preparar copia temporaria do PDF: {erro}")


def pdf_maior_que_limite(caminho_pdf: Path, limite_mb=TAMANHO_MAXIMO_PDF_MB) -> bool:
    try:
        tamanho_mb = caminho_pdf.stat().st_size / (1024 * 1024)
        return tamanho_mb >= limite_mb
    except Exception:
        return False


def descrever_tamanho_pdf(caminho_pdf: Path) -> str:
    try:
        tamanho_mb = caminho_pdf.stat().st_size / (1024 * 1024)
        return f"{tamanho_mb:.2f} MB"
    except Exception:
        return "tamanho desconhecido"


def pegar_primeiro_pdf_nao_postado():
    for pasta_local, dados in MAPEAMENTO.items():
        caminho_pasta = PASTA_BASE / pasta_local

        if not caminho_pasta.exists():
            print(f"[AVISO] Pasta não encontrada: {caminho_pasta}")
            continue

        pdfs = sorted(caminho_pasta.glob("*.pdf"))

        for pdf in pdfs:
            if not ja_postado(pdf):
                return {
                    "pdf": pdf,
                    "pasta_local": pasta_local,
                    "categoria_site": dados["categoria_site"],
                    "tipo": dados["tipo"],
                }

    return None


def listar_pdfs_nao_postados():
    pendentes = []
    total_pdfs = 0
    total_postados = 0

    for pasta_local, dados in MAPEAMENTO.items():
        caminho_pasta = PASTA_BASE / pasta_local

        if not caminho_pasta.exists():
            print(f"[AVISO] Pasta não encontrada: {caminho_pasta}")
            continue

        pdfs = sorted(caminho_pasta.glob("*.pdf"))
        total_pdfs += len(pdfs)

        for pdf in pdfs:
            if ja_postado(pdf):
                total_postados += 1
                continue

            pendentes.append({
                "pdf": pdf,
                "pasta_local": pasta_local,
                "categoria_site": dados["categoria_site"],
                "tipo": dados["tipo"],
            })

    print("\n[CONFERÊNCIA]")
    print(f"PDFs encontrados nas pastas: {total_pdfs}")
    print(f"PDFs já registrados como postados: {total_postados}")
    print(f"PDFs pendentes para postagem: {len(pendentes)}")

    return pendentes


# =========================
# FUNÇÕES PLAYWRIGHT
# =========================

def normalizar(texto):
    if not texto:
        return ""

    substituicoes = {
        "Âª": "a",
        "ª": "a",
        "Âº": "o",
        "º": "o",
        "Ã§": "c",
        "ç": "c",
        "Ã£": "a",
        "ã": "a",
        "Ã¡": "a",
        "á": "a",
        "Ã©": "e",
        "é": "e",
        "Ã­": "i",
        "í": "i",
        "Ã³": "o",
        "ó": "o",
        "Ãµ": "o",
        "õ": "o",
    }

    for origem, destino in substituicoes.items():
        texto = texto.replace(origem, destino)

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def clicar_texto(page, texto, timeout=15000):
    try:
        page.get_by_text(texto, exact=True).first.click(timeout=timeout)
        return True
    except Exception:
        try:
            page.get_by_text(texto, exact=False).first.click(timeout=timeout)
            return True
        except Exception:
            print(f"[ERRO] Não consegui clicar no texto: {texto}")
            return False


def clicar_link_ou_texto(page, textos, timeout=15000):
    if isinstance(textos, str):
        textos = [textos]

    for texto in textos:
        padrao = re.compile(re.escape(texto), re.I)

        try:
            links = page.get_by_role("link", name=padrao)
            for i in range(links.count()):
                link = links.nth(i)
                if link.is_visible(timeout=800):
                    link.scroll_into_view_if_needed(timeout=3000)
                    link.click(timeout=timeout)
                    return True
        except Exception:
            pass

        try:
            elementos = page.locator("a:visible").filter(has_text=padrao)
            for i in range(elementos.count()):
                elemento = elementos.nth(i)
                elemento.scroll_into_view_if_needed(timeout=3000)
                elemento.click(timeout=timeout)
                return True
        except Exception:
            pass

        try:
            elementos = page.get_by_text(padrao, exact=False)
            for i in range(elementos.count()):
                elemento = elementos.nth(i)
                if elemento.is_visible(timeout=800):
                    elemento.scroll_into_view_if_needed(timeout=3000)
                    elemento.click(timeout=timeout)
                    return True
        except Exception:
            pass

        try:
            clicou = page.evaluate(
                """(alvo) => {
                    const normalizar = (texto) => (texto || "")
                        .normalize("NFD")
                        .replace(/[\\u0300-\\u036f]/g, "")
                        .replace(/ª/g, "a")
                        .replace(/º/g, "o")
                        .toLowerCase();

                    const alvoNormalizado = normalizar(alvo);
                    const elementos = Array.from(document.querySelectorAll("a, button, [role='link'], [role='button']"));

                    for (const elemento of elementos) {
                        const estilo = window.getComputedStyle(elemento);
                        const caixa = elemento.getBoundingClientRect();

                        if (
                            estilo.visibility === "hidden" ||
                            estilo.display === "none" ||
                            caixa.width < 5 ||
                            caixa.height < 5
                        ) {
                            continue;
                        }

                        const texto = normalizar(elemento.innerText || elemento.textContent || "");

                        if (texto.includes(alvoNormalizado)) {
                            elemento.scrollIntoView({ block: "center", inline: "center" });
                            elemento.click();
                            return true;
                        }
                    }

                    return false;
                }""",
                texto,
            )

            if clicou:
                return True
        except Exception:
            pass

    print(f"[ERRO] Não consegui clicar em nenhuma opção: {', '.join(textos)}")
    return False


def pagina_tem_texto(page, textos):
    if isinstance(textos, str):
        textos = [textos]

    for texto in textos:
        try:
            if page.get_by_text(re.compile(re.escape(texto), re.I), exact=False).count() > 0:
                return True
        except Exception:
            pass

    return False


def clicar_e_validar(page, textos_clique, textos_destino, descricao, timeout=15000, tentativas=2):
    url_antes = page.url

    for tentativa in range(1, tentativas + 1):
        if not clicar_link_ou_texto(page, textos_clique, timeout=timeout):
            continue

        aguardar_pagina_estavel(page, timeout_rede=20000, ciclos=6)
        page.wait_for_timeout(1000)

        if page.url != url_antes or pagina_tem_texto(page, textos_destino):
            return True

        print(f"[AVISO] Clique em {descricao} não mudou de página. Tentando novamente... {tentativa}/{tentativas}")

    return False


class SessaoExpirada(Exception):
    pass


class UploadTravado(Exception):
    pass


def sessao_caiu(page):
    textos_erro = [
        "Authentication is required",
        "Server Error",
        "Unauthorized",
        "Não autorizado",
        "Nao autorizado",
        "Sessão expirada",
        "Sessao expirada",
        "Faça login",
        "Faca login",
    ]

    for texto in textos_erro:
        try:
            if page.get_by_text(re.compile(texto, re.I), exact=False).count() > 0:
                return True
        except Exception:
            pass

    try:
        if login_necessario(page) and not usuario_logado(page):
            return True
    except SessaoExpirada:
        raise
    except Exception:
        pass

    try:
        if modal_novo_item_sem_colecao(page):
            return True
    except Exception:
        pass

    return False


def verificar_sessao(page, contexto=""):
    if sessao_caiu(page):
        detalhe = f" durante {contexto}" if contexto else ""
        raise SessaoExpirada(f"Sessão/login caiu{detalhe}.")


def clicar_botao_possivel(page, nomes):
    for nome in nomes:
        try:
            page.get_by_role("button", name=re.compile(nome, re.I)).first.click(timeout=5000)
            return True
        except Exception:
            pass

        try:
            page.get_by_text(nome, exact=False).first.click(timeout=5000)
            return True
        except Exception:
            pass

    return False


def clicar_botao_exato_visivel(page, nomes, timeout=8000):
    aguardar_pagina_estavel(page, timeout_rede=10000)

    for nome in nomes:
        padrao = re.compile(rf"^\s*{re.escape(nome)}\s*$", re.I)

        try:
            botoes = page.get_by_role("button", name=padrao)
            qtd = botoes.count()

            for i in range(qtd):
                botao = botoes.nth(i)

                if not botao.is_visible(timeout=1000):
                    continue

                if botao.is_disabled(timeout=1000):
                    continue

                botao.scroll_into_view_if_needed(timeout=3000)
                botao.click(timeout=timeout)
                print(f"[OK] Botao '{nome}' clicado.")
                return True
        except Exception:
            pass

        try:
            botoes = page.locator("button:visible").filter(has_text=padrao)
            qtd = botoes.count()

            for i in range(qtd):
                botao = botoes.nth(i)

                if botao.is_disabled(timeout=1000):
                    continue

                botao.scroll_into_view_if_needed(timeout=3000)
                botao.click(timeout=timeout)
                print(f"[OK] Botao '{nome}' clicado.")
                return True
        except Exception:
            pass

    try:
        clicou = page.evaluate(
            """(nomes) => {
                const alvos = nomes.map((nome) => nome.trim().toLowerCase());
                const candidatos = Array.from(document.querySelectorAll("button, input[type='button'], input[type='submit']"));

                for (const elemento of candidatos) {
                    const texto = (
                        elemento.innerText ||
                        elemento.textContent ||
                        elemento.value ||
                        elemento.getAttribute("aria-label") ||
                        ""
                    ).trim().toLowerCase();

                    const style = window.getComputedStyle(elemento);
                    const box = elemento.getBoundingClientRect();

                    if (
                        style.display === "none" ||
                        style.visibility === "hidden" ||
                        box.width < 10 ||
                        box.height < 10 ||
                        elemento.disabled
                    ) {
                        continue;
                    }

                    if (alvos.some((alvo) => texto === alvo || texto.includes(alvo))) {
                        elemento.scrollIntoView({ block: "center", inline: "center" });
                        elemento.click();
                        return true;
                    }
                }

                return false;
            }""",
            nomes,
        )

        if clicou:
            print(f"[OK] Botao '{nomes[0]}' clicado.")
            return True
    except Exception:
        pass

    return False


def aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=30):
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout_rede)
    except Exception:
        pass

    try:
        page.wait_for_load_state("networkidle", timeout=timeout_rede)
    except Exception:
        pass

    seletores_carregando = [
        ".spinner-border",
        ".spinner",
        ".fa-spinner",
        ".loading",
        ".loader",
        "ds-loading",
        "[role='progressbar']",
        "[aria-busy='true']",
    ]

    ciclos_livres = 0

    for _ in range(ciclos):
        carregando = False

        for seletor in seletores_carregando:
            try:
                itens = page.locator(seletor)
                qtd = min(itens.count(), 5)

                for i in range(qtd):
                    if itens.nth(i).is_visible(timeout=300):
                        carregando = True
                        break

                if carregando:
                    break
            except Exception:
                pass

        if not carregando:
            ciclos_livres += 1
            if ciclos_livres >= 2:
                return True
        else:
            ciclos_livres = 0

        page.wait_for_timeout(1000)

    return False


def navegar_com_tentativas(page, url, descricao="página", tentativas=3, timeout=90000):
    for tentativa in range(1, tentativas + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        except Exception as erro:
            print(f"[AVISO] {descricao} demorou para carregar na tentativa {tentativa}/{tentativas}: {erro}")
            try:
                page.evaluate("window.stop()")
            except Exception:
                pass

        aguardar_pagina_estavel(page, timeout_rede=20000, ciclos=8)

        try:
            if url.split("/")[-1] in (page.url or ""):
                return True
        except Exception:
            pass

        if tentativa < tentativas:
            try:
                page.reload(wait_until="domcontentloaded", timeout=timeout)
            except Exception:
                try:
                    page.goto(url, wait_until="commit", timeout=timeout)
                except Exception:
                    pass
            page.wait_for_timeout(3000)

    return False


def ainda_na_tela_criar_colecao(page):
    textos_tela = [
        "Criar uma Coleção",
        "Criar uma colecao",
        "Editar Coleção",
        "Editar colecao",
    ]

    for texto in textos_tela:
        try:
            if page.get_by_text(texto, exact=False).count() > 0:
                return True
        except Exception:
            pass

    try:
        botoes_salvar = page.get_by_role("button", name=re.compile(r"^\s*(Salvar|Criar)\s*$", re.I))
        for i in range(botoes_salvar.count()):
            if botoes_salvar.nth(i).is_visible(timeout=500):
                return True
    except Exception:
        pass

    return False


def preencher_tipo_colecao_se_existir(page):
    try:
        selects = page.locator("select:visible")

        for i in range(min(selects.count(), 5)):
            select = selects.nth(i)
            caixa = select.bounding_box()

            if not caixa or caixa["width"] < 80 or caixa["height"] < 18:
                continue

            valor_atual = ""
            try:
                valor_atual = select.input_value(timeout=1000)
            except Exception:
                pass

            if valor_atual:
                continue

            opcoes = select.locator("option")

            for j in range(min(opcoes.count(), 10)):
                opcao = opcoes.nth(j)
                valor = opcao.get_attribute("value") or ""
                texto = (opcao.inner_text(timeout=1000) or "").strip()

                if not valor and not texto:
                    continue

                if not valor and texto.lower() in ["selecione", "select", "-"]:
                    continue

                if valor:
                    select.select_option(value=valor, timeout=3000)
                else:
                    select.select_option(label=texto, timeout=3000)

                print("[OK] Tipo da coleção selecionado.")
                return True
    except Exception:
        pass

    try:
        selecionou = page.evaluate(
            """() => {
                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 80 &&
                        box.height >= 18;
                };

                const selects = Array.from(document.querySelectorAll("select")).filter(visivel);

                for (const select of selects) {
                    if (select.value) {
                        continue;
                    }

                    const opcao = Array.from(select.options).find((opt) => {
                        const texto = (opt.textContent || "").trim().toLowerCase();
                        return opt.value && !["selecione", "select", "-"].includes(texto);
                    });

                    if (!opcao) {
                        continue;
                    }

                    select.value = opcao.value;
                    select.dispatchEvent(new Event("input", { bubbles: true }));
                    select.dispatchEvent(new Event("change", { bubbles: true }));
                    select.dispatchEvent(new Event("blur", { bubbles: true }));
                    return true;
                }

                return false;
            }"""
        )

        if selecionou:
            print("[OK] Tipo da coleção selecionado.")
            return True
    except Exception:
        pass

    return False


def clicar_salvar_por_posicao(page):
    try:
        page.keyboard.press("End")
        page.wait_for_timeout(800)
        viewport = page.viewport_size or {"width": 1600, "height": 900}
        tentativas = [
            (viewport["width"] - 95, viewport["height"] - 55),
            (viewport["width"] - 120, viewport["height"] - 70),
            (viewport["width"] - 150, viewport["height"] - 55),
        ]

        for x, y in tentativas:
            page.mouse.click(x, y)
            page.wait_for_timeout(2500)

            if not ainda_na_tela_criar_colecao(page):
                return True

        return True
    except Exception:
        return False


def clicar_salvar_colecao_robusto(page):
    preencher_tipo_colecao_se_existir(page)

    if clicar_botao_exato_visivel(page, ["Salvar", "Criar", "Save", "Create"], timeout=10000):
        return True

    try:
        clicou = page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "").trim().toLowerCase();
                const candidatos = Array.from(document.querySelectorAll("button, input[type='submit'], input[type='button'], a"));

                for (const el of candidatos) {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    const texto = normalizar(el.innerText || el.textContent || el.value || el.getAttribute("aria-label") || "");

                    if (
                        style.display === "none" ||
                        style.visibility === "hidden" ||
                        box.width < 20 ||
                        box.height < 15
                    ) {
                        continue;
                    }

                    if (!texto.includes("salvar") && !texto.includes("criar") && !texto.includes("save") && !texto.includes("create")) {
                        continue;
                    }

                    if (el.disabled) {
                        el.disabled = false;
                        el.removeAttribute("disabled");
                    }

                    el.scrollIntoView({ block: "center", inline: "center" });
                    el.click();
                    return true;
                }

                const forms = Array.from(document.querySelectorAll("form"));
                if (forms.length > 0) {
                    forms[0].dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
                    return true;
                }

                return false;
            }"""
        )

        if clicou:
            print("[OK] Clique no botão de salvar/criar enviado.")
            return True
    except Exception:
        pass

    try:
        clicou = page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "").trim().toLowerCase();
                const candidatos = Array.from(document.querySelectorAll("button, input[type='submit'], input[type='button'], a"))
                    .map((el) => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        const texto = normalizar(el.innerText || el.textContent || el.value || el.getAttribute("aria-label") || "");
                        return { el, style, box, texto };
                    })
                    .filter(({ el, style, box, texto }) => {
                        if (
                            style.display === "none" ||
                            style.visibility === "hidden" ||
                            box.width < 20 ||
                            box.height < 15
                        ) {
                            return false;
                        }

                        if (texto.includes("voltar") || texto.includes("cancelar") || texto.includes("back") || texto.includes("cancel")) {
                            return false;
                        }

                        const classe = normalizar(el.getAttribute("class") || "");
                        return texto.includes("salvar") ||
                            texto.includes("criar") ||
                            texto.includes("save") ||
                            texto.includes("create") ||
                            classe.includes("primary") ||
                            classe.includes("success");
                    })
                    .sort((a, b) => {
                        if (a.box.top !== b.box.top) {
                            return b.box.top - a.box.top;
                        }
                        return b.box.left - a.box.left;
                    });

                if (candidatos.length === 0) {
                    return false;
                }

                const alvo = candidatos[0].el;
                if (alvo.disabled) {
                    alvo.disabled = false;
                    alvo.removeAttribute("disabled");
                }

                alvo.scrollIntoView({ block: "center", inline: "center" });
                alvo.click();
                return true;
            }"""
        )

        if clicou:
            print("[OK] Clique no botão de salvar/criar enviado pelo botão principal.")
            return True
    except Exception:
        pass

    try:
        clicou = page.evaluate(
            """() => {
                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 20 &&
                        box.height >= 15;
                };

                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .trim();

                const candidatos = Array.from(document.querySelectorAll("button, input[type='submit'], input[type='button'], a"))
                    .filter(visivel)
                    .map((el) => {
                        const box = el.getBoundingClientRect();
                        const texto = normalizar(el.innerText || el.textContent || el.value || el.getAttribute("aria-label") || "");
                        const classe = normalizar(el.getAttribute("class") || "");
                        return { el, box, texto, classe };
                    })
                    .filter(({ texto, classe }) => {
                        if (texto.includes("voltar") || texto.includes("cancelar") || texto.includes("back") || texto.includes("cancel")) {
                            return false;
                        }
                        return texto.includes("salvar") ||
                            texto.includes("criar") ||
                            texto.includes("save") ||
                            texto.includes("create") ||
                            classe.includes("btn-primary") ||
                            classe.includes("btn-success");
                    })
                    .sort((a, b) => {
                        const ay = a.box.top + a.box.height / 2;
                        const by = b.box.top + b.box.height / 2;
                        if (Math.abs(ay - by) > 10) {
                            return by - ay;
                        }
                        return (b.box.left + b.box.width / 2) - (a.box.left + a.box.width / 2);
                    });

                if (candidatos.length === 0) {
                    return false;
                }

                const alvo = candidatos[0].el;
                alvo.disabled = false;
                alvo.removeAttribute("disabled");
                alvo.removeAttribute("aria-disabled");
                alvo.scrollIntoView({ block: "center", inline: "center" });
                alvo.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, view: window }));
                alvo.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, view: window }));
                alvo.click();
                return true;
            }"""
        )

        if clicou:
            print("[OK] Clique no botão Salvar/Criar enviado pelo botão visual da tela.")
            return True
    except Exception:
        pass

    return clicar_salvar_por_posicao(page)


def salvar_colecao_e_aguardar(page):
    total_tentativas = 4

    for tentativa in range(1, total_tentativas + 1):
        print(f"[INFO] Salvando colecao... tentativa {tentativa}/{total_tentativas}")
        aguardar_pagina_estavel(page, timeout_rede=20000)
        preencher_tipo_colecao_se_existir(page)

        if not ainda_na_tela_criar_colecao(page):
            print("[OK] Colecao salva.")
            return True

        if not clicar_salvar_colecao_robusto(page):
            page.keyboard.press("End")
            aguardar_pagina_estavel(page, timeout_rede=10000, ciclos=5)

            if not clicar_salvar_colecao_robusto(page):
                if clicar_salvar_por_posicao(page):
                    print("[OK] Clique no botao de salvar/criar enviado por posicao.")
                else:
                    print("[AVISO] Botao de salvar/criar ainda nao esta disponivel.")
                    page.wait_for_timeout(5000)
                    continue

        print("[INFO] Aguardando o site concluir o salvamento...")
        aguardar_pagina_estavel(page, timeout_rede=45000, ciclos=25)

        if not ainda_na_tela_criar_colecao(page):
            print("[OK] Colecao salva.")
            return True

        if tentativa < total_tentativas:
            print("[AVISO] A tela de colecao ainda esta aberta; vou tentar salvar mais uma vez.")
            page.wait_for_timeout(5000)

    return False


def tela_criacao_item_aberta(page):
    sinais = [
        "Editar Submissão",
        "Submissão",
        "Title",
        "Date of Issue",
    ]

    for sinal in sinais:
        try:
            if page.get_by_text(re.compile(sinal, re.I), exact=False).count() > 0:
                return True
        except Exception:
            pass

    try:
        if page.locator("input[type='file']").count() > 0:
            return True
    except Exception:
        pass

    return False


def modal_novo_item_aberto(page):
    try:
        if page.get_by_text(re.compile("Novo item|Criar um novo item em", re.I), exact=False).count() > 0:
            return True
    except Exception:
        pass

    return False


def modal_editar_item_aberto(page):
    try:
        if page.get_by_text(re.compile(r"Editar\s+item", re.I), exact=False).count() > 0:
            return True
    except Exception:
        pass

    return False


def fechar_modal_se_aberto(page):
    try:
        if not modal_visivel(page):
            return
    except Exception:
        return

    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(600)
    except Exception:
        pass

    try:
        if modal_visivel(page):
            page.locator(".modal-content:visible button, .modal-dialog:visible button").filter(
                has_text=re.compile(r"×|Fechar|Cancelar|Close", re.I)
            ).first.click(timeout=2000, force=True)
            page.wait_for_timeout(600)
    except Exception:
        pass


def modal_novo_item_sem_colecao(page):
    try:
        if page.get_by_text(re.compile("Criar um novo item em|Novo item", re.I), exact=False).count() == 0:
            return False

        textos_vazio = [
            r"Nenhum\(a\)\s+collection\s+encontrado\(a\)",
            r"Nenhuma\s+collection\s+encontrada",
            r"Nenhum\s+collection\s+encontrado",
            r"Nenhum\(a\).*encontrado\(a\)",
        ]

        for texto in textos_vazio:
            if page.get_by_text(re.compile(texto, re.I), exact=False).count() > 0:
                return True
    except Exception:
        pass

    return False


def modal_visivel(page):
    try:
        return page.locator(".modal-content:visible, .modal-dialog:visible").count() > 0
    except Exception:
        return False


def tela_criacao_colecao_aberta(page):
    if modal_visivel(page):
        return False

    encontrou_campo = False

    try:
        campos = page.locator("input:visible, textarea:visible")
        for i in range(min(campos.count(), 20)):
            campo = campos.nth(i)
            caixa = campo.bounding_box()
            tipo = ""
            try:
                tipo = (campo.get_attribute("type") or "").lower()
            except Exception:
                pass

            if tipo in ["hidden", "file", "checkbox", "radio", "submit", "button"]:
                continue

            if caixa and caixa["width"] >= 120 and caixa["height"] >= 18:
                encontrou_campo = True
                break
    except Exception:
        pass

    if not encontrou_campo:
        return False

    return encontrou_campo


def objetivo_modal_concluido(page, tipo_modal="geral"):
    if tipo_modal == "item":
        return tela_criacao_item_aberta(page) and not modal_novo_item_aberto(page)

    if tipo_modal == "colecao":
        return tela_criacao_colecao_aberta(page)

    return tela_criacao_item_aberta(page) or objetivo_modal_concluido(page, "colecao")


def clicar_opcao_e_confirmar_saida_modal(page, opcao, tipo_modal="geral"):
    tentativas = [
        ("click", lambda: opcao.click(timeout=5000)),
        ("duplo clique", lambda: opcao.dblclick(timeout=5000)),
        ("click forçado", lambda: opcao.click(timeout=5000, force=True)),
        ("click via página", lambda: opcao.evaluate("elemento => elemento.click()")),
    ]

    for descricao, acao in tentativas:
        try:
            opcao.scroll_into_view_if_needed(timeout=3000)
            acao()
            page.wait_for_timeout(2500)

            if objetivo_modal_concluido(page, tipo_modal):
                print(f"[OK] Opção do modal selecionada com {descricao}.")
                return True
        except Exception:
            pass

    try:
        page.keyboard.press("Enter")
        page.wait_for_timeout(2500)

        if objetivo_modal_concluido(page, tipo_modal):
            print("[OK] Opção do modal selecionada com Enter.")
            return True
    except Exception:
        pass

    return False


def clicar_botao_confirmacao_modal(page, tipo_modal="geral"):
    nomes = [
        "Selecionar",
        "Confirmar",
        "Continuar",
        "Criar",
        "Adicionar",
        "Select",
        "Confirm",
        "Continue",
        "Create",
        "Add",
    ]

    for nome in nomes:
        try:
            botoes = page.locator(".modal-content button:visible, .modal-dialog button:visible").filter(
                has_text=re.compile(rf"^\s*{re.escape(nome)}\s*$", re.I)
            )

            for i in range(min(botoes.count(), 4)):
                botao = botoes.nth(i)
                botao.click(timeout=4000)
                page.wait_for_timeout(2500)

                if objetivo_modal_concluido(page, tipo_modal):
                    print(f"[OK] Botão '{nome}' do modal confirmado.")
                    return True
        except Exception:
            pass

    return False


def clicar_primeira_opcao_lista_modal(page, tipo_modal="geral"):
    tempo_limite = 5 if tipo_modal == "item" else 10
    limite = datetime.now().timestamp() + tempo_limite

    seletores = [
        ".modal-content .list-group-item",
        ".modal-dialog .list-group-item",
        ".modal-content [role='option']",
        ".modal-dialog [role='option']",
        ".modal-content .active",
        ".modal-dialog .active",
        ".modal-content a",
        ".modal-dialog a",
        ".modal-content button",
        ".modal-dialog button",
        ".modal-content li",
        ".modal-dialog li",
        ".modal-content .media",
        ".modal-dialog .media",
    ]

    while datetime.now().timestamp() < limite:
        if objetivo_modal_concluido(page, tipo_modal):
            return True

        if modal_novo_item_sem_colecao(page):
            raise SessaoExpirada("Sessão/login caiu: modal de item abriu sem coleções.")

        try:
            page.locator(".modal-content, .modal-dialog").first.wait_for(state="visible", timeout=1000)
        except Exception:
            pass

        encontrou_opcao = False

        for seletor in seletores:
            try:
                opcoes = page.locator(seletor)
                qtd = min(opcoes.count(), 12)

                for i in range(qtd):
                    opcao = opcoes.nth(i)

                    if not opcao.is_visible(timeout=1000):
                        continue

                    caixa = opcao.bounding_box()
                    if not caixa:
                        continue

                    texto_opcao = ""
                    try:
                        texto_opcao = (opcao.inner_text(timeout=1000) or "").strip()
                    except Exception:
                        pass

                    texto_normalizado = normalizar(texto_opcao)

                    if caixa["width"] < 80 or caixa["height"] < 20:
                        continue

                    if any(p in texto_normalizado for p in ["cancelar", "fechar", "close", "novo item"]):
                        continue

                    encontrou_opcao = True

                    if clicar_opcao_e_confirmar_saida_modal(page, opcao, tipo_modal):
                        return True

                    if clicar_botao_confirmacao_modal(page, tipo_modal):
                        return True
            except Exception:
                pass

        if not encontrou_opcao:
            if modal_novo_item_sem_colecao(page):
                raise SessaoExpirada("Sessão/login caiu: modal de item não listou coleções.")

            print("[INFO] Aguardando lista do modal carregar...")

        try:
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(1500)
        except Exception:
            pass

    # Fallback por coordenada relativa ao modal, evitando depender de uma posição fixa da tela.
    try:
        modal = page.locator(".modal-content:visible, .modal-dialog:visible").first
        caixa = modal.bounding_box()

        if caixa:
            page.mouse.dblclick(caixa["x"] + caixa["width"] / 2, caixa["y"] + min(180, caixa["height"] / 2))
        else:
            page.mouse.dblclick(780, 335)

        page.wait_for_timeout(3000)

        if objetivo_modal_concluido(page, tipo_modal):
            return True
    except Exception:
        pass

    return False


def clicar_primeira_opcao_modal(page, tipo_modal="geral"):
    """
    Modal do DSpace:
    quando abre Novo > Coleção/Item, a primeira opção já vem selecionada.
    Este método tenta ENTER, duplo clique na opção selecionada e clique por coordenada.
    """
    page.wait_for_timeout(1500)

    if objetivo_modal_concluido(page, tipo_modal):
        return True

    if modal_novo_item_sem_colecao(page):
        raise SessaoExpirada("Sessão/login caiu: modal de item abriu sem listar coleções.")

    if modal_novo_item_aberto(page):
        print("[INFO] Modal de item aberto. Selecionando obrigatoriamente a primeira opção da lista...")
        if clicar_primeira_opcao_lista_modal(page, tipo_modal=tipo_modal):
            return True

    # 1) Se a primeira opção já está destacada, ENTER costuma selecionar.
    try:
        page.keyboard.press("Enter")
        page.wait_for_timeout(2500)

        # Se saiu do modal e abriu uma tela de criação, deu certo.
        if objetivo_modal_concluido(page, tipo_modal):
            return True

        if modal_novo_item_sem_colecao(page):
            raise SessaoExpirada("Sessão/login caiu: modal de item continuou sem coleções.")
    except SessaoExpirada:
        raise
    except Exception:
        pass

    # 2) Tenta clicar/dar duplo clique em elementos visíveis dentro do modal.
    seletores = [
        ".modal-content .active",
        ".modal-dialog .active",
        ".modal-content .list-group-item",
        ".modal-dialog .list-group-item",
        ".modal-content li",
        ".modal-dialog li",
        ".modal-content .media",
        ".modal-dialog .media",
        ".modal-content div",
    ]

    for seletor in seletores:
        try:
            opcoes = page.locator(seletor)
            qtd = opcoes.count()

            for i in range(min(qtd, 5)):
                opcao = opcoes.nth(i)

                if not opcao.is_visible(timeout=1000):
                    continue

                caixa = opcao.bounding_box()
                if not caixa:
                    continue

                # Evita clicar no input de pesquisa do modal.
                if caixa["y"] < 150:
                    continue

                opcao.dblclick(timeout=5000)
                page.wait_for_timeout(3000)

                if objetivo_modal_concluido(page, tipo_modal):
                    return True

                opcao.click(timeout=5000)
                page.wait_for_timeout(3000)

                if objetivo_modal_concluido(page, tipo_modal):
                    return True

        except Exception:
            pass

    # 3) Clique por coordenada na primeira opção visível do modal.
    # Usando coordenadas próximas ao print enviado.
    coordenadas = [
        (255, 210),
        (260, 225),
        (300, 210),
        (300, 230),
    ]

    for x, y in coordenadas:
        try:
            page.mouse.dblclick(x, y)
            page.wait_for_timeout(3000)

            if objetivo_modal_concluido(page, tipo_modal):
                return True
        except Exception:
            pass

    return False


def garantir_tela_criacao_colecao(page):
    if tela_criacao_colecao_aberta(page):
        return True

    for tentativa in range(1, 4):
        print(f"[AVISO] Tela de criação da coleção ainda não abriu. Tentando selecionar novamente... {tentativa}/3")

        try:
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
        except Exception:
            pass

        if tela_criacao_colecao_aberta(page):
            return True

        if modal_visivel(page):
            clicar_primeira_opcao_lista_modal(page, tipo_modal="colecao")
            page.wait_for_timeout(2500)

        if tela_criacao_colecao_aberta(page):
            return True

    return False


def preencher_primeiro_input_visivel(page, valor, descricao="campo"):
    seletores = [
        "input:visible",
        "input.form-control:visible",
        "input:not([type='hidden'])",
    ]

    for seletor in seletores:
        try:
            campos = page.locator(seletor)
            qtd = campos.count()

            for i in range(min(qtd, 10)):
                campo = campos.nth(i)

                if not campo.is_visible(timeout=1000):
                    continue

                caixa = campo.bounding_box()
                if not caixa:
                    continue

                # Evita inputs muito pequenos ou ocultos.
                if caixa["width"] < 100 or caixa["height"] < 15:
                    continue

                campo.click(timeout=3000)
                campo.fill(valor, timeout=8000)
                print(f"[OK] {descricao} preenchido.")
                return True
        except Exception:
            pass

    return False


def preencher_nome_colecao(page, valor):
    for tentativa in range(1, 6):
        aguardar_pagina_estavel(page, timeout_rede=10000, ciclos=3)

        try:
            page.locator("input:visible, textarea:visible").first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        seletores = [
            "input[id*='name' i]:visible",
            "input[name*='name' i]:visible",
            "input[formcontrolname*='name' i]:visible",
            "input[aria-label*='Nome' i]:visible",
            "input[placeholder*='Nome' i]:visible",
        ]

        for seletor in seletores:
            try:
                campos = page.locator(seletor)

                for i in range(min(campos.count(), 5)):
                    campo = campos.nth(i)
                    caixa = campo.bounding_box()

                    if not caixa or caixa["width"] < 120 or caixa["height"] < 20:
                        continue

                    campo.scroll_into_view_if_needed(timeout=3000)
                    campo.click(timeout=5000, force=True)
                    campo.fill(valor, timeout=8000)
                    print("[OK] Nome da coleção preenchido.")
                    return True
            except Exception:
                pass

        try:
            labels = page.locator("label:visible").filter(has_text=re.compile("Nome", re.I))

            for i in range(min(labels.count(), 5)):
                label = labels.nth(i)
                label_box = label.bounding_box()

                if not label_box:
                    continue

                inputs = page.locator("input:visible")

                for j in range(min(inputs.count(), 20)):
                    campo = inputs.nth(j)
                    caixa = campo.bounding_box()

                    if not caixa or caixa["width"] < 120 or caixa["height"] < 20:
                        continue

                    if caixa["y"] >= label_box["y"] and caixa["y"] <= label_box["y"] + 90:
                        campo.scroll_into_view_if_needed(timeout=3000)
                        campo.click(timeout=5000, force=True)
                        campo.fill(valor, timeout=8000)
                        print("[OK] Nome da coleção preenchido.")
                        return True
        except Exception:
            pass

        if preencher_primeiro_input_visivel(page, valor, "Nome da coleção"):
            return True

        try:
            preenchido = page.evaluate(
                """(valor) => {
                    const visivel = (el) => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        return style.display !== "none" &&
                            style.visibility !== "hidden" &&
                            box.width >= 120 &&
                            box.height >= 18;
                    };

                    const aplicarValor = (el) => {
                        el.scrollIntoView({ block: "center", inline: "center" });
                        el.focus();
                        const proto = el instanceof HTMLTextAreaElement
                            ? HTMLTextAreaElement.prototype
                            : HTMLInputElement.prototype;
                        const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
                        setter.call(el, valor);
                        el.dispatchEvent(new Event("input", { bubbles: true }));
                        el.dispatchEvent(new Event("change", { bubbles: true }));
                        el.dispatchEvent(new Event("blur", { bubbles: true }));
                        return true;
                    };

                    const labels = Array.from(document.querySelectorAll("label"));
                    for (const label of labels) {
                        const texto = (label.innerText || label.textContent || "").toLowerCase();
                        if (!texto.includes("nome")) {
                            continue;
                        }

                        const forId = label.getAttribute("for");
                        if (forId) {
                            const campo = document.getElementById(forId);
                            if (campo && visivel(campo)) {
                                return aplicarValor(campo);
                            }
                        }

                        const labelBox = label.getBoundingClientRect();
                        const campos = Array.from(document.querySelectorAll("input, textarea"))
                            .filter((el) => {
                                const tipo = (el.getAttribute("type") || "").toLowerCase();
                                if (["hidden", "file", "checkbox", "radio", "submit", "button"].includes(tipo)) {
                                    return false;
                                }
                                if (!visivel(el)) {
                                    return false;
                                }
                                const box = el.getBoundingClientRect();
                                return box.top >= labelBox.top && box.top <= labelBox.bottom + 120;
                            })
                            .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);

                        if (campos.length > 0) {
                            return aplicarValor(campos[0]);
                        }
                    }

                    const campos = Array.from(document.querySelectorAll("input, textarea"))
                        .filter((el) => {
                            const tipo = (el.getAttribute("type") || "").toLowerCase();
                            if (["hidden", "file", "checkbox", "radio", "submit", "button"].includes(tipo)) {
                                return false;
                            }
                            return visivel(el);
                        })
                        .sort((a, b) => {
                            const ab = a.getBoundingClientRect();
                            const bb = b.getBoundingClientRect();
                            return ab.top === bb.top ? ab.left - bb.left : ab.top - bb.top;
                        });

                    if (campos.length > 0) {
                        return aplicarValor(campos[0]);
                    }

                    return false;
                }""",
                valor,
            )

            if preenchido:
                print("[OK] Nome da coleção preenchido.")
                return True
        except Exception:
            pass

        print(f"[AVISO] Campo Nome da coleção ainda não disponível. Tentando novamente... {tentativa}/5")
        page.wait_for_timeout(2000)

    return False


def campo_com_valor(page, valor):
    try:
        campos = page.locator("input:visible, textarea:visible")

        for i in range(min(campos.count(), 80)):
            try:
                if campos.nth(i).input_value(timeout=500).strip() == valor.strip():
                    return True
            except Exception:
                pass
    except Exception:
        pass

    try:
        return page.get_by_display_value(valor).count() > 0
    except Exception:
        return False


def preencher_descricao_curta_colecao(page, valor):
    for tentativa in range(1, 4):
        try:
            labels = page.locator("label:visible").filter(has_text=re.compile("Descrição curta|Descricao curta", re.I))

            for i in range(min(labels.count(), 5)):
                label = labels.nth(i)
                label_box = label.bounding_box()

                if not label_box:
                    continue

                textareas = page.locator("textarea:visible")

                for j in range(min(textareas.count(), 20)):
                    campo = textareas.nth(j)
                    caixa = campo.bounding_box()

                    if not caixa or caixa["width"] < 120 or caixa["height"] < 30:
                        continue

                    if caixa["y"] >= label_box["y"] and caixa["y"] <= label_box["y"] + 120:
                        campo.scroll_into_view_if_needed(timeout=3000)
                        campo.fill(valor, timeout=5000)
                        print("[OK] Descrição curta preenchida.")
                        return True
        except Exception:
            pass

        try:
            textareas = page.locator("textarea:visible")
            if textareas.count() >= 2:
                textareas.nth(1).fill(valor, timeout=5000)
                print("[OK] Descrição curta preenchida.")
                return True
            if textareas.count() == 1:
                textareas.nth(0).fill(valor, timeout=5000)
                print("[OK] Descrição curta preenchida.")
                return True
        except Exception:
            pass

        print(f"[AVISO] Descrição curta ainda não disponível. Tentando novamente... {tentativa}/3")
        page.wait_for_timeout(1500)

    return False


def login_necessario(page):
    sinais_login = [
        "Entrar",
        "Login",
        "E-mail",
        "Email",
        "Senha",
        "Usuário",
        "Usuario",
        "Acessar",
    ]

    for sinal in sinais_login:
        try:
            if page.get_by_text(re.compile(sinal, re.I), exact=False).count() > 0:
                return True
        except Exception:
            pass

    try:
        if page.locator("input[type='password']").count() > 0:
            return True
    except Exception:
        pass

    return False


def usuario_logado(page):
    sinais_barra_lateral = [
        "Administração",
        "Controle de Acesso",
        "Novo",
    ]

    for sinal in sinais_barra_lateral:
        try:
            elementos = page.get_by_text(re.compile(sinal, re.I), exact=False)

            for i in range(elementos.count()):
                elemento = elementos.nth(i)

                if not elemento.is_visible(timeout=500):
                    continue

                caixa = elemento.bounding_box()
                if caixa and caixa["x"] < 330:
                    return True
        except Exception:
            pass

    return False


def clicar_botao_login_salvo(page):
    try:
        senha = page.locator("input[type='password']:visible").first
        caixa_senha = senha.bounding_box()

        if caixa_senha:
            botoes = page.locator("button:visible").filter(has_text=re.compile("Entrar", re.I))

            for i in range(botoes.count()):
                botao = botoes.nth(i)
                caixa = botao.bounding_box()

                if not caixa:
                    continue

                if caixa["y"] > caixa_senha["y"] and abs(caixa["x"] - caixa_senha["x"]) < 120:
                    botao.click(timeout=5000)
                    print("[OK] Botão Entrar do formulário clicado.")
                    return True
    except Exception:
        pass

    try:
        botoes_entrar = page.locator("button:visible").filter(has_text=re.compile("Entrar", re.I))
        for i in range(botoes_entrar.count()):
            botao = botoes_entrar.nth(i)
            caixa = botao.bounding_box()

            if not caixa:
                continue

            if caixa["width"] >= 100 and caixa["height"] >= 30:
                botao.click(timeout=5000)
                print("[OK] Botão Entrar clicado.")
                return True
    except Exception:
        pass

    nomes = [
        "Entrar",
        "Acessar",
        "Login",
        "Log in",
        "Sign in",
    ]

    for nome in nomes:
        padrao = re.compile(nome, re.I)

        try:
            botoes = page.get_by_role("button", name=padrao)
            for i in range(botoes.count()):
                botao = botoes.nth(i)
                if botao.is_visible(timeout=500):
                    botao.click(timeout=5000)
                    print(f"[OK] Botão {nome} clicado.")
                    return True
        except Exception:
            pass

        try:
            links = page.get_by_role("link", name=padrao)
            for i in range(links.count()):
                link = links.nth(i)
                if link.is_visible(timeout=500):
                    link.click(timeout=5000)
                    return True
        except Exception:
            pass

        try:
            textos = page.get_by_text(padrao, exact=False)
            for i in range(textos.count()):
                texto = textos.nth(i)
                if texto.is_visible(timeout=500):
                    texto.click(timeout=5000)
                    return True
        except Exception:
            pass

    return False


def carregar_credenciais_login():
    email = None
    senha = None

    if LOGIN_EMAIL_FIXO and LOGIN_SENHA_FIXA:
        return LOGIN_EMAIL_FIXO, LOGIN_SENHA_FIXA

    try:
        import os

        email = os.environ.get("LICITACOES_EMAIL")
        senha = os.environ.get("LICITACOES_SENHA")
    except Exception:
        pass

    if email and senha:
        return email, senha

    if not ARQUIVO_CREDENCIAIS.exists():
        return None, None

    try:
        dados = json.loads(ARQUIVO_CREDENCIAIS.read_text(encoding="utf-8"))
        email = (dados.get("email") or "").strip()
        senha = dados.get("senha") or ""

        if email and senha:
            return email, senha
    except Exception as erro:
        print(f"[AVISO] Não consegui ler {ARQUIVO_CREDENCIAIS.name}: {erro}")

    return None, None


def painel_login_aberto_sem_campos(page):
    try:
        painel_aberto = page.get_by_text(re.compile("Novo Usuário|Novo Usuario|Esqueceu a senha", re.I), exact=False).count() > 0
        tem_senha = page.locator("input[type='password']:visible").count() > 0
        campos_visiveis = page.locator("input:visible").count()
        return painel_aberto and not tem_senha and campos_visiveis == 0
    except Exception:
        return False


def aguardar_campos_login(page, timeout_segundos=20):
    for segundo in range(timeout_segundos):
        aguardar_pagina_estavel(page, timeout_rede=5000, ciclos=2)

        try:
            if page.locator("input[type='password']:visible").count() > 0:
                return True
        except Exception:
            pass

        try:
            campos = page.locator("input:visible")
            if campos.count() >= 2:
                return True
        except Exception:
            pass

        if painel_login_aberto_sem_campos(page):
            if segundo in [3, 8, 14]:
                print("[INFO] Painel de login abriu, mas os campos ainda não carregaram. Aguardando...")

        page.wait_for_timeout(1000)

    return False


def abrir_painel_login(page):
    try:
        links_entrar = page.get_by_text(re.compile(r"^\s*Entrar\s*$", re.I), exact=False)

        for i in range(links_entrar.count()):
            link = links_entrar.nth(i)

            if not link.is_visible(timeout=500):
                continue

            caixa = link.bounding_box()

            if not caixa:
                continue

            if caixa["y"] < 160:
                link.click(timeout=5000)
                page.wait_for_timeout(1000)
                return True
    except Exception:
        pass

    return False


def reiniciar_home_para_login(page):
    print("[INFO] Recarregando a página inicial para refazer o login...")
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    navegar_com_tentativas(page, URL_SITE, "página inicial", tentativas=3, timeout=120000)
    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)


def preencher_login_com_credenciais(page, email, senha):
    abrir_painel_login(page)

    if not aguardar_campos_login(page, timeout_segundos=20):
        print("[AVISO] O painel de login abriu sem carregar e-mail/senha.")
        return False

    try:
        campo_email = page.get_by_placeholder(re.compile("Endereço de email|Endereco de email|email|e-mail", re.I)).first

        campo_email.click(timeout=5000)
        campo_email.fill(email, timeout=5000)
    except Exception:
        try:
            campos = page.locator("input:visible")
            candidatos = []

            for i in range(min(campos.count(), 20)):
                campo = campos.nth(i)
                caixa = campo.bounding_box()

                if not caixa or caixa["width"] < 120 or caixa["height"] < 25:
                    continue

                placeholder = ""
                tipo = ""

                try:
                    placeholder = campo.get_attribute("placeholder") or ""
                    tipo = campo.get_attribute("type") or ""
                except Exception:
                    pass

                texto = f"{placeholder} {tipo}".lower()

                if "pesquisar" in texto or "search" in texto:
                    continue

                candidatos.append(campo)

            if not candidatos:
                print("[AVISO] Não encontrei campo de e-mail visível.")
                return False

            candidatos[0].click(timeout=5000)
            candidatos[0].fill(email, timeout=5000)
        except Exception as erro:
            print(f"[AVISO] Não consegui preencher o e-mail: {erro}")
            return False

    try:
        campo_senha = page.locator("input[type='password']:visible").first
        campo_senha.click(timeout=5000)
        campo_senha.fill(senha, timeout=5000)
    except Exception as erro:
        print(f"[AVISO] Não consegui preencher a senha: {erro}")
        return False

    print("[OK] E-mail e senha preenchidos.")
    return True


def tentar_login_com_credenciais_salvas(page):
    print("[INFO] Login não confirmado. Tentando usar o login salvo do navegador...")

    email, senha = carregar_credenciais_login()

    if email and senha:
        for rodada in range(1, 4):
            print(f"[INFO] Credenciais locais encontradas. Preenchendo login... tentativa {rodada}/3")

            if preencher_login_com_credenciais(page, email, senha):
                if clicar_botao_login_salvo(page):
                    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

                    if usuario_logado(page):
                        print("[OK] Login confirmado.")
                        return True

                try:
                    page.keyboard.press("Enter")
                    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

                    if usuario_logado(page):
                        print("[OK] Login confirmado.")
                        return True
                except Exception:
                    pass

            if usuario_logado(page):
                print("[OK] Login confirmado.")
                return True

            reiniciar_home_para_login(page)

    for tentativa in range(1, 4):
        print(f"[INFO] Tentativa de login automático {tentativa}/3...")

        try:
            campos_texto = page.locator("input:visible")
            if campos_texto.count() > 0:
                campos_texto.first.click(timeout=3000)
                page.wait_for_timeout(500)
        except Exception:
            pass

        try:
            senha = page.locator("input[type='password']").first
            if senha.is_visible(timeout=1500):
                senha.click(timeout=3000)
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")
        except Exception:
            pass

        if not clicar_botao_login_salvo(page):
            try:
                page.keyboard.press("Enter")
            except Exception:
                pass

        aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

        if usuario_logado(page):
            print("[OK] Login confirmado.")
            return True

    return False


def preencher_campo_data(campo, valor):
    try:
        try:
            campo.scroll_into_view_if_needed(timeout=1500)
        except Exception:
            pass

        campo.click(timeout=2000, force=True)
        campo.press("Control+A")
        campo.press("Backspace")
        campo.type(valor, delay=30)
    except Exception:
        pass

    try:
        campo.evaluate(
            """(el, value) => {
                const proto = el instanceof HTMLTextAreaElement
                    ? HTMLTextAreaElement.prototype
                    : HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                setter.call(el, value);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            }""",
            valor,
        )
    except Exception:
        return False

    try:
        return campo.input_value(timeout=1000).strip() == valor
    except Exception:
        return True


def preencher_data_por_js_direto(page, metadados):
    ano = metadados["ano"]
    mes = metadados["mes"]
    dia = metadados["dia"]

    try:
        return page.evaluate(
            """([ano, mes, dia]) => {
                const valores = [ano, mes, dia];

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 10 &&
                        box.height >= 10;
                };

                const textoEl = (el) => [
                    el.getAttribute("placeholder") || "",
                    el.getAttribute("aria-label") || "",
                    el.getAttribute("name") || "",
                    el.getAttribute("id") || "",
                    el.getAttribute("formcontrolname") || "",
                    el.getAttribute("data-test") || "",
                    el.getAttribute("data-testid") || "",
                ].join(" ").toLowerCase();

                const aplicar = (el, valor) => {
                    el.focus();
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
                    setter.call(el, valor);
                    el.dispatchEvent(new Event("input", { bubbles: true }));
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                    el.dispatchEvent(new Event("keyup", { bubbles: true }));
                    el.dispatchEvent(new Event("blur", { bubbles: true }));
                    return String(el.value).trim() === String(valor);
                };

                const campos = Array.from(document.querySelectorAll("input"))
                    .filter((el) => {
                        const tipo = (el.getAttribute("type") || "").toLowerCase();
                        if (["hidden", "file", "checkbox", "radio", "submit", "button"].includes(tipo)) {
                            return false;
                        }
                        return visivel(el);
                    });

                const porAtributo = [
                    campos.find((el) => /year|ano/.test(textoEl(el))),
                    campos.find((el) => /month|mes|mês/.test(textoEl(el))),
                    campos.find((el) => /day|dia/.test(textoEl(el))),
                ];

                if (porAtributo.every(Boolean)) {
                    return porAtributo.every((el, idx) => aplicar(el, valores[idx]));
                }

                const candidatosTexto = Array.from(document.querySelectorAll("label, span, div, small, p"))
                    .filter((el) => /date of issue|data/i.test(el.innerText || el.textContent || ""))
                    .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);

                for (const label of candidatosTexto) {
                    const labelBox = label.getBoundingClientRect();
                    const proximos = campos
                        .map((el) => ({ el, box: el.getBoundingClientRect() }))
                        .filter(({ box }) => {
                            const abaixo = box.top >= labelBox.top - 30 && box.top <= labelBox.bottom + 220;
                            const larguraData = box.width <= 180;
                            return abaixo && larguraData;
                        })
                        .sort((a, b) => a.box.top === b.box.top ? a.box.left - b.box.left : a.box.top - b.box.top)
                        .slice(0, 3)
                        .map(({ el }) => el);

                    if (proximos.length >= 3 && proximos.every((el, idx) => aplicar(el, valores[idx]))) {
                        return true;
                    }
                }

                const gruposPequenos = campos
                    .map((el) => ({ el, box: el.getBoundingClientRect(), texto: textoEl(el), valor: (el.value || "").trim() }))
                    .filter(({ box, texto, valor }) => {
                        if (box.width > 180) {
                            return false;
                        }
                        if (/title|author|publisher|search|pesquisar/.test(texto)) {
                            return false;
                        }
                        return !valor || /^\\d{1,4}$/.test(valor);
                    })
                    .sort((a, b) => a.box.top === b.box.top ? a.box.left - b.box.left : a.box.top - b.box.top);

                for (let i = 0; i <= gruposPequenos.length - 3; i++) {
                    const trio = gruposPequenos.slice(i, i + 3);
                    const mesmaArea = Math.abs(trio[2].box.top - trio[0].box.top) <= 80;
                    if (!mesmaArea) {
                        continue;
                    }

                    if (trio.every(({ el }, idx) => aplicar(el, valores[idx]))) {
                        return true;
                    }
                }

                return false;
            }""",
            [ano, mes, dia],
        )
    except Exception:
        return False


def preencher_data_publicacao(page, metadados):
    ano = metadados["ano"]
    mes = metadados["mes"]
    dia = metadados["dia"]

    if preencher_data_por_js_direto(page, metadados):
        metadados["data_preenchida_ok"] = True
        print(f"[OK] Data preenchida: {dia}/{mes}/{ano}.")
        return True

    valores = [ano, mes, dia]
    chaves = ["year", "month", "day"]

    preenchidos_por_placeholder = 0

    for placeholder, valor in zip(chaves, valores):
        seletores = [
            f"input[placeholder*='{placeholder}' i]:visible",
            f"input[aria-label*='{placeholder}' i]:visible",
            f"input[name*='{placeholder}' i]:visible",
            f"input[id*='{placeholder}' i]:visible",
            f"input[formcontrolname*='{placeholder}' i]:visible",
        ]

        for seletor in seletores:
            try:
                campos = page.locator(seletor)

                for i in range(min(campos.count(), 5)):
                    campo = campos.nth(i)
                    caixa = campo.bounding_box()

                    if not caixa or caixa["width"] < 20 or caixa["height"] < 18:
                        continue

                    if preencher_campo_data(campo, valor):
                        preenchidos_por_placeholder += 1
                        raise StopIteration
            except Exception:
                if preenchidos_por_placeholder > chaves.index(placeholder):
                    break

    if preenchidos_por_placeholder == 3:
        metadados["data_preenchida_ok"] = True
        print(f"[OK] Data preenchida: {dia}/{mes}/{ano}.")
        return True

    try:
        labels = page.get_by_text(re.compile("Date of Issue|Data", re.I), exact=False)
        area_y = None

        for i in range(min(labels.count(), 10)):
            label = labels.nth(i)

            if not label.is_visible(timeout=500):
                continue

            caixa_label = label.bounding_box()

            if caixa_label:
                area_y = caixa_label["y"]
                break

        campos = page.locator("input:visible")
        candidatos = []

        for i in range(min(campos.count(), 80)):
            campo = campos.nth(i)

            if not campo.is_visible(timeout=500):
                continue

            caixa = campo.bounding_box()
            if not caixa or caixa["width"] < 20 or caixa["height"] < 18:
                continue

            try:
                tipo = (campo.get_attribute("type") or "").lower()
                placeholder = (campo.get_attribute("placeholder") or "").lower()
                valor_atual = campo.input_value(timeout=500).strip()
            except Exception:
                tipo = ""
                placeholder = ""
                valor_atual = ""

            if tipo in ["hidden", "file", "checkbox", "radio", "submit", "button"]:
                continue

            texto_auxiliar = f"{tipo} {placeholder}"
            parece_data = any(chave in texto_auxiliar for chave in ["year", "month", "day", "ano", "mes", "mês", "dia"])

            if area_y is not None and not (area_y - 20 <= caixa["y"] <= area_y + 170) and not parece_data:
                continue

            if valor_atual and valor_atual not in valores:
                continue

            candidatos.append((caixa["y"], caixa["x"], campo))

        candidatos = sorted(candidatos, key=lambda item: (item[0], item[1]))

        if len(candidatos) >= 3:
            preenchidos = 0
            for (_, _, campo), valor in zip(candidatos[:3], valores):
                if preencher_campo_data(campo, valor):
                    preenchidos += 1

            if preenchidos >= 3:
                metadados["data_preenchida_ok"] = True
                print(f"[OK] Data preenchida: {dia}/{mes}/{ano}.")
                return True
    except Exception as erro:
        print(f"[AVISO] Falha no preenchimento alternativo da data: {erro}")

    try:
        preenchido_js = page.evaluate(
            """([ano, mes, dia]) => {
                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 20 &&
                        box.height >= 15;
                };

                const aplicar = (el, valor) => {
                    el.scrollIntoView({ block: "center", inline: "nearest" });
                    el.focus();
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
                    setter.call(el, valor);
                    el.dispatchEvent(new Event("input", { bubbles: true }));
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                    el.dispatchEvent(new Event("blur", { bubbles: true }));
                    return el.value === valor;
                };

                const campos = Array.from(document.querySelectorAll("input"))
                    .filter((el) => {
                        const tipo = (el.getAttribute("type") || "").toLowerCase();
                        if (["hidden", "file", "checkbox", "radio", "submit", "button"].includes(tipo)) {
                            return false;
                        }
                        return visivel(el);
                    });

                const procurar = (termos) => campos.find((el) => {
                    const texto = [
                        el.getAttribute("placeholder") || "",
                        el.getAttribute("aria-label") || "",
                        el.getAttribute("name") || "",
                        el.getAttribute("id") || "",
                        el.getAttribute("formcontrolname") || "",
                    ].join(" ").toLowerCase();
                    return termos.some((termo) => texto.includes(termo));
                });

                const campoAno = procurar(["year", "ano"]);
                const campoMes = procurar(["month", "mes", "mês"]);
                const campoDia = procurar(["day", "dia"]);

                if (campoAno && campoMes && campoDia) {
                    return aplicar(campoAno, ano) && aplicar(campoMes, mes) && aplicar(campoDia, dia);
                }

                const label = Array.from(document.querySelectorAll("label, span, div"))
                    .find((el) => /date of issue|data/i.test(el.innerText || el.textContent || ""));

                if (!label) {
                    return false;
                }

                const labelBox = label.getBoundingClientRect();
                const proximos = campos
                    .map((el) => ({ el, box: el.getBoundingClientRect() }))
                    .filter(({ box }) => box.top >= labelBox.top - 30 && box.top <= labelBox.bottom + 180)
                    .sort((a, b) => a.box.top === b.box.top ? a.box.left - b.box.left : a.box.top - b.box.top)
                    .slice(0, 3);

                if (proximos.length < 3) {
                    return false;
                }

                return aplicar(proximos[0].el, ano) &&
                    aplicar(proximos[1].el, mes) &&
                    aplicar(proximos[2].el, dia);
            }""",
            [ano, mes, dia],
        )

        if preenchido_js:
            metadados["data_preenchida_ok"] = True
            print(f"[OK] Data preenchida: {dia}/{mes}/{ano}.")
            return True
    except Exception as erro:
        print(f"[AVISO] Falha no preenchimento direto da data: {erro}")

    return False


def aguardar_deposito_concluido(page):
    print("[INFO] Aguardando o depósito concluir...")

    try:
        page.wait_for_load_state("networkidle", timeout=90000)
    except Exception:
        pass

    aguardar_pagina_estavel(page, timeout_rede=60000, ciclos=20)

    sinais_sucesso = [
        "Item depositado",
        "Submissão concluída",
        "Submission complete",
        "Item submitted",
        "handle",
        "URI Permanente",
    ]

    for _ in range(30):
        for sinal in sinais_sucesso:
            try:
                if page.get_by_text(re.compile(sinal, re.I), exact=False).count() > 0:
                    print("[OK] Depósito concluído.")
                    return True
            except Exception:
                pass

        try:
            botoes_depositar = page.get_by_role("button", name=re.compile("Depositar", re.I))
            if botoes_depositar.count() == 0:
                print("[OK] Depósito concluído.")
                return True
        except Exception:
            pass

        page.wait_for_timeout(1000)

    print("[AVISO] Não consegui confirmar visualmente o depósito, mas o carregamento terminou.")
    return True


def upload_em_andamento(page):
    seletores = [
        ".progress",
        ".progress-bar",
        ".spinner-border",
        ".spinner",
        ".fa-spinner",
        ".loading",
        ".loader",
        ".uploading",
        ".upload-progress",
        ".file-upload-progress",
        ".dz-processing",
        ".dz-upload",
        "[role='progressbar']",
        "[aria-busy='true']",
    ]

    for seletor in seletores:
        try:
            itens = page.locator(seletor)
            qtd = min(itens.count(), 10)

            for i in range(qtd):
                item = itens.nth(i)
                if item.is_visible(timeout=300):
                    return True
        except Exception:
            pass

    textos = [
        "Enviando",
        "Uploading",
        "Carregando",
        "Processando",
        "Aguarde",
        "Anexando",
        "Transferindo",
        "Salvando",
        "Validando",
        "Bitstream",
        "Processing",
        "Saving",
        "Please wait",
    ]

    for texto in textos:
        try:
            itens = page.get_by_text(re.compile(texto, re.I), exact=False)
            qtd = min(itens.count(), 10)

            for i in range(qtd):
                if itens.nth(i).is_visible(timeout=300):
                    return True
        except Exception:
            pass

    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase();

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 10 &&
                        box.height >= 10;
                };

                const padraoTexto = /(enviando|uploading|carregando|processando|aguarde|anexando|transferindo|salvando|validando|bitstream|processing|saving|please wait|\\b\\d{1,3}\\s*%\\b)/i;
                const padraoClasse = /(progress|spinner|loading|loader|uploading|upload-progress|file-upload|processing|busy)/i;

                for (const el of document.querySelectorAll("div, span, p, small, strong, em, button, li")) {
                    if (!visivel(el)) {
                        continue;
                    }

                    const texto = normalizar(el.innerText || el.textContent || "");
                    const classe = normalizar(el.className || "");

                    if (padraoClasse.test(classe) || padraoTexto.test(texto)) {
                        return true;
                    }
                }

                return false;
            }"""
        )
    except Exception:
        pass

    return False


def upload_falhou(page):
    textos_falha = [
        r"falha",
        r"falhou",
        r"falha\s+no\s+upload",
        r"falha\s+ao\s+enviar",
        r"erro\s+no\s+upload",
        r"erro\s+ao\s+enviar",
        r"erro\s+ao\s+carregar",
        r"não\s+foi\s+possível\s+carregar",
        r"não\s+foi\s+possível\s+enviar",
        r"nao\s+foi\s+possivel\s+carregar",
        r"nao\s+foi\s+possivel\s+enviar",
        r"server\s+error",
        r"upload\s+failed",
        r"failed\s+to\s+upload",
        r"error\s+upload",
    ]

    for texto in textos_falha:
        try:
            if page.get_by_text(re.compile(texto, re.I), exact=False).count() > 0:
                return True
        except Exception:
            pass

    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase();

                const seletores = [
                    ".toast",
                    ".toast-container",
                    ".alert",
                    ".alert-danger",
                    ".notification",
                    ".notifications",
                    "[role='alert']",
                    "[aria-live]"
                ];

                const padrao = /(falha|falhou|falha no upload|falha ao enviar|erro no upload|erro ao enviar|erro ao carregar|nao foi possivel carregar|nao foi possivel enviar|server error|upload failed|failed to upload|error upload)/i;

                for (const seletor of seletores) {
                    for (const el of document.querySelectorAll(seletor)) {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        if (style.display === "none" || style.visibility === "hidden" || box.width < 10 || box.height < 10) {
                            continue;
                        }

                        if (padrao.test(normalizar(el.innerText || el.textContent || ""))) {
                            return true;
                        }
                    }
                }

                return false;
            }"""
        )
    except Exception:
        return False


def upload_sucesso_notificado(page):
    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase();

                const seletores = [
                    ".toast",
                    ".toast-container",
                    ".alert",
                    ".alert-success",
                    ".notification",
                    ".notifications",
                    "[role='alert']",
                    "[aria-live]"
                ];

                const padrao = /(sucesso|concluido|concluida|anexado|carregado|enviado|uploaded|success|complete|completed)/i;

                for (const seletor of seletores) {
                    for (const el of document.querySelectorAll(seletor)) {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        if (style.display === "none" || style.visibility === "hidden" || box.width < 10 || box.height < 10) {
                            continue;
                        }

                        const classe = normalizar(el.className || "");
                        const texto = normalizar(el.innerText || el.textContent || "");
                        const pareceSucesso = classe.includes("success") ||
                            classe.includes("sucesso") ||
                            classe.includes("alert-success") ||
                            classe.includes("toast-success");

                        if (pareceSucesso || padrao.test(texto)) {
                            return true;
                        }
                    }
                }

                return false;
            }"""
        )
    except Exception:
        return False


def limpar_falha_upload(page):
    print("[INFO] Falha de upload detectada. Vou limpar o aviso e tentar novamente...")

    try:
        page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase();

                const padrao = /(falha|falhou|falha no upload|falha ao enviar|erro no upload|erro ao enviar|erro ao carregar|nao foi possivel carregar|nao foi possivel enviar|server error|upload failed|failed to upload|error upload)/i;
                const avisos = Array.from(document.querySelectorAll(".toast, .alert, .notification, [role='alert'], [aria-live]"))
                    .filter((el) => padrao.test(normalizar(el.innerText || el.textContent || "")));

                for (const aviso of avisos) {
                    const fechar = aviso.querySelector("button.close, .close, [aria-label='Close'], [aria-label='Fechar'], .btn-close");
                    if (fechar) {
                        fechar.click();
                    } else {
                        aviso.style.display = "none";
                    }
                }
            }"""
        )
    except Exception:
        pass

    try:
        viewport = page.viewport_size or {"width": 1600, "height": 900}
        lixeiras = page.locator(".fa-trash, .fa-trash-alt, button:visible").filter(has_text=re.compile(r"^\s*$|Excluir|Remover|Delete|Remove", re.I))

        candidatos = []
        for i in range(min(lixeiras.count(), 20)):
            item = lixeiras.nth(i)
            caixa = item.bounding_box()
            if not caixa:
                continue

            if caixa["y"] < 150 or caixa["y"] > viewport["height"] - 90:
                continue

            if caixa["x"] < viewport["width"] - 300:
                continue

            candidatos.append((caixa["y"], item))

        for _, item in sorted(candidatos, key=lambda par: par[0], reverse=True):
            try:
                item.click(timeout=3000, force=True)
                page.wait_for_timeout(800)
            except Exception:
                pass
    except Exception:
        pass

    fechar_menus_suspensos(page)


def upload_concluido(page, caminho_pdf):
    nome_pdf = Path(caminho_pdf).name
    nome_normalizado = normalizar(nome_pdf)

    if upload_falhou(page):
        return False

    try:
        achou_nome = page.evaluate(
            """(nomeNormalizado) => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                return normalizar(document.body.innerText || "").includes(nomeNormalizado);
            }""",
            nome_normalizado,
        )

        if not achou_nome:
            return False
    except Exception:
        try:
            if page.get_by_text(nome_pdf, exact=False).count() == 0:
                return False
        except Exception:
            return False

    try:
        if page.get_by_text(re.compile(r"\(\s*[\d,.]+\s*(KB|MB|GB)\s*\)", re.I), exact=False).count() == 0:
            return False
    except Exception:
        pass

    if upload_em_andamento(page):
        return False

    return True


def area_upload_mostra_pdf_pronto(page, caminho_pdf):
    nome_pdf = Path(caminho_pdf).name
    nome_normalizado = normalizar(nome_pdf)

    if upload_falhou(page):
        return False

    try:
        return page.evaluate(
            """(nomeNormalizado) => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const textoPagina = normalizar(document.body.innerText || "");

                if (textoPagina.includes("nenhum arquivo enviado ainda")) {
                    return false;
                }

                if (!textoPagina.includes(nomeNormalizado)) {
                    const base = nomeNormalizado.replace(/\\.pdf$/i, "");
                    const partes = base
                        .split(/\\s+-\\s+|\\s+/)
                        .filter((parte) => parte.length >= 4);
                    const partesEncontradas = partes.filter((parte) => textoPagina.includes(parte)).length;

                    if (partesEncontradas < Math.min(3, partes.length)) {
                        return false;
                    }
                }

                const temTamanhoArquivo = /\\(\\s*[\\d,.]+\\s*(kb|mb|gb)\\s*\\)/i.test(textoPagina);
                const temSemMiniatura = textoPagina.includes("sem miniatura");
                const temBotaoArquivo = Array.from(document.querySelectorAll("button, a, i, span"))
                    .some((el) => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        if (style.display === "none" || style.visibility === "hidden" || box.width < 8 || box.height < 8) {
                            return false;
                        }

                        const classe = normalizar(el.className || "");
                        const titulo = normalizar(el.getAttribute("title") || el.getAttribute("aria-label") || "");
                        return classe.includes("fa-download") ||
                            classe.includes("fa-edit") ||
                            classe.includes("fa-pencil") ||
                            classe.includes("fa-trash") ||
                            titulo.includes("download") ||
                            titulo.includes("editar") ||
                            titulo.includes("excluir") ||
                            titulo.includes("remover");
                    });

                const temCheckVerde = Array.from(document.querySelectorAll("i, span, svg, div"))
                    .some((el) => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        if (style.display === "none" || style.visibility === "hidden" || box.width < 8 || box.height < 8) {
                            return false;
                        }

                        const classe = normalizar(el.className || "");
                        const cor = normalizar(style.color || "");
                        return classe.includes("fa-check") ||
                            classe.includes("check-circle") ||
                            classe.includes("text-success") ||
                            classe.includes("success") ||
                            cor.includes("rgb(139, 195, 74)") ||
                            cor.includes("rgb(76, 175, 80)") ||
                            cor.includes("green");
                    });

                return temTamanhoArquivo && (temSemMiniatura || temBotaoArquivo || temCheckVerde);
            }""",
            nome_normalizado,
        )
    except Exception:
        return False


def area_upload_sem_arquivo(page):
    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                return normalizar(document.body.innerText || "").includes("nenhum arquivo enviado ainda");
            }"""
        )
    except Exception:
        return False


def upload_visual_em_processamento(page):
    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const texto = normalizar(document.body.innerText || "");

                return texto.includes("a processar") ||
                    texto.includes("processar...") ||
                    texto.includes("a processar...") ||
                    texto.includes("processing") ||
                    texto.includes("tamanho da fila");
            }"""
        )
    except Exception:
        return False


def upload_visual_com_erro_percentual(page):
    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const texto = normalizar(document.body.innerText || "");

                return texto.includes("tamanho da fila") &&
                    texto.includes(".pdf") &&
                    /(^|\\s)0\\s*%(\\s|$)/.test(texto);
            }"""
        )
    except Exception:
        return False


def opcoes_finais_upload_visiveis(page):
    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 20 &&
                        box.height >= 10;
                };

                let temRealizar = false;
                let temEncerrar = false;

                for (const el of document.querySelectorAll("button, a, input[type='button'], input[type='submit']")) {
                    if (!visivel(el)) {
                        continue;
                    }

                    const texto = normalizar(el.innerText || el.textContent || el.value || el.getAttribute("aria-label") || el.getAttribute("title") || "");

                    if (
                        texto.includes("realizar upload") ||
                        texto.includes("realizar o upload") ||
                        texto.includes("fazer upload") ||
                        texto.includes("fazer o upload") ||
                        texto.includes("enviar upload") ||
                        texto === "upload" ||
                        texto.includes("salvar upload") ||
                        texto.includes("confirmar upload")
                    ) {
                        temRealizar = true;
                    }

                    if (
                        texto.includes("encerrar sem fazer") ||
                        texto.includes("sem fazer upload") ||
                        texto.includes("cancelar upload") ||
                        texto.includes("cancelar") ||
                        texto.includes("descartar")
                    ) {
                        temEncerrar = true;
                    }
                }

                return temRealizar && temEncerrar;
            }"""
        )
    except Exception:
        return False


def clicar_realizar_upload_pendente(page):
    expressoes = [
        r"realizar\s+upload",
        r"realizar\s+o\s+upload",
        r"fazer\s+upload",
        r"fazer\s+o\s+upload",
        r"enviar\s+upload",
        r"salvar\s+upload",
        r"confirmar\s+upload",
        r"^\s*upload\s*$",
    ]

    for expressao in expressoes:
        try:
            botoes = page.locator("button:visible, a:visible, input[type='button']:visible, input[type='submit']:visible").filter(has_text=re.compile(expressao, re.I))
            if botoes.count() > 0:
                botoes.first.click(timeout=5000, force=True)
                print("[OK] Botao de realizar upload clicado.")
                return True
        except Exception:
            pass

    try:
        return page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 20 &&
                        box.height >= 10;
                };

                for (const el of document.querySelectorAll("button, a, input[type='button'], input[type='submit']")) {
                    if (!visivel(el)) {
                        continue;
                    }

                    const texto = normalizar(el.innerText || el.textContent || el.value || el.getAttribute("aria-label") || el.getAttribute("title") || "");

                    if (
                        texto.includes("realizar upload") ||
                        texto.includes("realizar o upload") ||
                        texto.includes("fazer upload") ||
                        texto.includes("fazer o upload") ||
                        texto.includes("enviar upload") ||
                        texto === "upload" ||
                        texto.includes("salvar upload") ||
                        texto.includes("confirmar upload")
                    ) {
                        el.scrollIntoView({ block: "center", inline: "center" });
                        el.click();
                        return true;
                    }
                }

                return false;
            }"""
        )
    except Exception:
        return False


def clicar_encerrar_upload_pendente(page):
    expressoes = [
        r"encerrar\s+sem\s+fazer",
        r"sem\s+fazer\s+upload",
        r"cancelar\s+upload",
        r"descartar",
        r"cancelar",
    ]

    for expressao in expressoes:
        try:
            botoes = page.locator("button:visible, a:visible, input[type='button']:visible, input[type='submit']:visible").filter(has_text=re.compile(expressao, re.I))
            if botoes.count() > 0:
                botoes.first.click(timeout=5000, force=True)
                print("[INFO] Opção de encerrar/cancelar upload clicada para tentar anexar novamente.")
                page.wait_for_timeout(1000)
                return True
        except Exception:
            pass

    return False


def algum_pdf_anexado(page):
    if upload_falhou(page):
        return False

    try:
        return page.evaluate(
            """() => {
                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 20 &&
                        box.height >= 10;
                };

                const texto = (document.body.innerText || "").toLowerCase();
                if (texto.includes(".pdf")) {
                    return true;
                }

                return Array.from(document.querySelectorAll("a, span, div, h1, h2, h3, h4, h5, p"))
                    .some((el) => visivel(el) && (el.innerText || el.textContent || "").toLowerCase().includes(".pdf"));
            }"""
        )
    except Exception:
        try:
            return page.get_by_text(re.compile(r"\.pdf", re.I), exact=False).count() > 0
        except Exception:
            return False


def pdf_anexado_na_tela(page, caminho_pdf):
    if upload_falhou(page):
        return False

    nome_pdf = Path(caminho_pdf).name
    nome_normalizado = normalizar(nome_pdf)
    base_normalizado = normalizar(Path(caminho_pdf).stem)

    try:
        return page.evaluate(
            """([nomeNormalizado, baseNormalizado]) => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const texto = normalizar(document.body.innerText || "");
                return texto.includes(nomeNormalizado) ||
                    (baseNormalizado && texto.includes(baseNormalizado) && texto.includes(".pdf"));
            }""",
            [nome_normalizado, base_normalizado],
        )
    except Exception:
        try:
            return page.get_by_text(re.compile(r"\.pdf", re.I), exact=False).count() > 0
        except Exception:
            return False


def aguardar_upload_concluido(page, caminho_pdf, tentativas=None):
    print("[INFO] Aguardando ate 3 minutos pela confirmacao visual do upload...")
    checagens_prontas = 0
    checagens_prontas_necessarias = 2
    ja_clicou_realizar_upload = False
    inicio_espera = time.time()
    limite_espera_segundos = 180
    avisou_processando = False

    while True:
        aguardar_pagina_estavel(page, timeout_rede=5000, ciclos=2)

        if upload_falhou(page):
            print("[AVISO] O site informou falha no upload.")
            return False

        if upload_visual_com_erro_percentual(page):
            print("[AVISO] Upload terminou em 0%. Vou recarregar e tentar novamente.")
            return False

        if area_upload_mostra_pdf_pronto(page, caminho_pdf):
            checagens_prontas += 1
            if checagens_prontas >= checagens_prontas_necessarias:
                print("[OK] Area de upload mostra o PDF pronto para deposito.")
                return True
        else:
            checagens_prontas = 0

        if opcoes_finais_upload_visiveis(page):
            print("[INFO] A barra terminou e apareceram as opcoes finais do upload.")
            if not ja_clicou_realizar_upload:
                if clicar_realizar_upload_pendente(page):
                    ja_clicou_realizar_upload = True
                    page.wait_for_timeout(1500)
                    continue
                print("[AVISO] Nao consegui clicar em realizar upload.")
                return False

        if upload_visual_em_processamento(page) and not avisou_processando:
            print("[INFO] Upload esta em processamento. Vou aguardar ate 3 minutos nesta tentativa.")
            avisou_processando = True

        if time.time() - inicio_espera >= limite_espera_segundos:
            print("[AVISO] Nao apareceu confirmacao visual do PDF pronto em 3 minutos. Vou recarregar e tentar novamente.")
            return False

        page.wait_for_timeout(1500)


def fechar_menus_suspensos(page):
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception:
        pass

    try:
        page.evaluate(
            """() => {
                for (const el of document.querySelectorAll(".dropdown-menu.show, .dropdown.show .dropdown-menu, .show.dropdown-menu")) {
                    el.classList.remove("show");
                    el.style.display = "none";
                }
            }"""
        )
    except Exception:
        pass


def clicar_navegar_upload(page):
    fechar_menus_suspensos(page)

    try:
        clicou = page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 20 &&
                        box.height >= 10;
                };

                const candidatos = Array.from(document.querySelectorAll("a, button, label, span"))
                    .filter(visivel)
                    .map((el) => ({ el, box: el.getBoundingClientRect(), texto: normalizar(el.innerText || el.textContent || "") }))
                    .filter(({ box, texto }) => texto === "navegar" && box.top > 140)
                    .sort((a, b) => a.box.top - b.box.top);

                if (candidatos.length === 0) {
                    return false;
                }

                const alvo = candidatos[0].el;
                alvo.scrollIntoView({ block: "center", inline: "center" });
                alvo.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, view: window }));
                alvo.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, view: window }));
                alvo.click();
                return true;
            }"""
        )

        if clicou:
            return True
    except Exception:
        pass

    try:
        links = page.locator("a:visible, button:visible, label:visible").filter(has_text=re.compile(r"^\s*Navegar\s*$", re.I))
        candidatos = []

        for i in range(min(links.count(), 20)):
            elemento = links.nth(i)
            caixa = elemento.bounding_box()
            if not caixa:
                continue

            if caixa["y"] <= 140:
                continue

            candidatos.append((caixa["y"], elemento))

        if candidatos:
            _, elemento = sorted(candidatos, key=lambda item: item[0])[0]
            elemento.scroll_into_view_if_needed(timeout=3000)
            elemento.click(timeout=5000, force=True)
            return True
    except Exception:
        pass

    return False


def upload_pronto_para_anexar(page):
    try:
        inputs = page.locator("input[type='file']")
        if inputs.count() > 0:
            return True
    except Exception:
        pass

    try:
        pronto = page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 20 &&
                        box.height >= 10;
                };

                const temNavegarUpload = Array.from(document.querySelectorAll("a, button, label, span"))
                    .some((el) => {
                        if (!visivel(el)) {
                            return false;
                        }
                        const box = el.getBoundingClientRect();
                        return box.top > 140 && normalizar(el.innerText || el.textContent || "") === "navegar";
                    });

                const texto = normalizar(document.body.innerText || "");
                return temNavegarUpload ||
                    texto.includes("arraste arquivos") ||
                    texto.includes("arraste um arquivo") ||
                    texto.includes("anexar a este item") ||
                    texto.includes("drag files") ||
                    texto.includes("browse");
            }"""
        )

        if pronto:
            return True
    except Exception:
        pass

    return False


def aguardar_area_upload_pronta(page, timeout_segundos=60):
    print("[INFO] Aguardando a área de upload carregar...")

    for segundo in range(timeout_segundos):
        aguardar_pagina_estavel(page, timeout_rede=5000, ciclos=2)
        verificar_sessao(page, "aguardar área de upload")
        fechar_menus_suspensos(page)

        if upload_pronto_para_anexar(page):
            print("[OK] Área de upload pronta.")
            return True

        if segundo in [10, 20, 35, 50]:
            print("[INFO] A área de upload ainda está carregando. Vou aguardar mais um pouco...")

        page.wait_for_timeout(1000)

    return False


def anexar_pdf(page, caminho_pdf):
    fechar_menus_suspensos(page)

    try:
        inputs = page.locator("input[type='file']")
        for i in range(min(inputs.count(), 5)):
            try:
                inputs.nth(i).set_input_files(caminho_pdf, timeout=10000)
                print("[OK] PDF anexado.")
                return True
            except Exception:
                pass
    except Exception:
        pass

    print("[AVISO] Não encontrei input[type=file]. Tentando pelo botão Navegar da área de upload...")

    with page.expect_file_chooser(timeout=15000) as fc_info:
        if not clicar_navegar_upload(page):
            raise Exception("Não encontrei o botão Navegar da área de upload.")

    file_chooser = fc_info.value
    file_chooser.set_files(caminho_pdf)
    fechar_menus_suspensos(page)
    print("[OK] PDF anexado via Navegar.")
    return True


def garantir_upload_pdf(page, caminho_pdf, total_tentativas=3):
    if upload_falhou(page):
        limpar_falha_upload(page)

    for tentativa in range(1, total_tentativas + 1):
        if upload_falhou(page):
            limpar_falha_upload(page)

        if area_upload_mostra_pdf_pronto(page, caminho_pdf):
            print("[OK] PDF ja aparece pronto na area de upload.")
            return True

        print(f"[INFO] Anexando PDF... tentativa {tentativa}/{total_tentativas}")
        if not aguardar_area_upload_pronta(page, timeout_segundos=60):
            if area_upload_mostra_pdf_pronto(page, caminho_pdf):
                print("[OK] Area de upload mostra o PDF pronto.")
                return True
            raise UploadTravado("A area de upload nao carregou a tempo.")

        fechar_menus_suspensos(page)
        anexar_pdf(page, caminho_pdf)

        if aguardar_upload_concluido(page, caminho_pdf):
            return True

        if upload_falhou(page):
            limpar_falha_upload(page)

        if tentativa < total_tentativas:
            clicar_encerrar_upload_pendente(page)
            print("[AVISO] Upload nao confirmado pela cena visual. Vou recarregar a pagina e anexar novamente.")
            try:
                page.reload(wait_until="domcontentloaded", timeout=90000)
            except Exception:
                try:
                    page.reload(wait_until="commit", timeout=90000)
                except Exception:
                    pass
            aguardar_pagina_estavel(page, timeout_rede=20000, ciclos=8)
            page.wait_for_timeout(1000)

    raise UploadTravado("O upload do PDF nao foi confirmado visualmente apos 3 tentativas.")

def titulo_preenchido(page, titulo):
    try:
        campos = page.locator("input:visible")
        qtd = min(campos.count(), 30)

        for i in range(qtd):
            valor = campos.nth(i).input_value(timeout=1000)
            if valor.strip() == titulo.strip():
                return True
    except Exception:
        pass

    try:
        if page.get_by_display_value(titulo).count() > 0:
            return True
    except Exception:
        pass

    return False


def data_preenchida(page, metadados):
    valores = [metadados["ano"], metadados["mes"], metadados["dia"]]
    encontrados = 0

    try:
        campos = page.locator("input:visible")
        qtd = min(campos.count(), 60)

        for i in range(qtd):
            valor = campos.nth(i).input_value(timeout=1000).strip()
            if valor in valores:
                encontrados += 1
    except Exception:
        pass

    return encontrados >= 3


def validar_conteudo_antes_depositar(page, metadados, caminho_pdf):
    print("[INFO] Validando conteúdo antes de depositar...")

    upload_ja_confirmado = metadados.get("upload_confirmado_ok", False)

    if upload_ja_confirmado and upload_falhou(page):
        raise UploadTravado("O site informou falha no upload antes do depósito.")

    if upload_ja_confirmado and not (pdf_anexado_na_tela(page, caminho_pdf) or algum_pdf_anexado(page)):
        print("[AVISO] Upload tinha sido confirmado, mas o PDF não aparece mais na tela. Vou conferir novamente.")
        upload_ja_confirmado = False

    if not upload_ja_confirmado and not upload_concluido(page, caminho_pdf):
        if pdf_anexado_na_tela(page, caminho_pdf) or algum_pdf_anexado(page):
            print("[INFO] PDF aparece na tela. Vou aguardar estabilizar antes de depositar.")
            if not aguardar_upload_concluido(page, caminho_pdf, tentativas=180):
                raise UploadTravado("O PDF apareceu, mas o upload não estabilizou antes do depósito.")
            metadados["upload_confirmado_ok"] = True
        else:
            garantir_upload_pdf(page, caminho_pdf)
            metadados["upload_confirmado_ok"] = True

    if not metadados.get("upload_confirmado_ok") and not upload_concluido(page, caminho_pdf) and not (pdf_anexado_na_tela(page, caminho_pdf) or algum_pdf_anexado(page)):
        garantir_upload_pdf(page, caminho_pdf)
        metadados["upload_confirmado_ok"] = True

    print("[INFO] Conferindo se o upload terminou de verdade antes de liberar o Depositar...")
    if not aguardar_upload_concluido(page, caminho_pdf, tentativas=180):
        raise UploadTravado("O upload nao ficou estavel antes do deposito.")
    if not area_upload_mostra_pdf_pronto(page, caminho_pdf):
        raise UploadTravado("A area de upload ainda nao mostra o PDF pronto para deposito.")
    metadados["upload_confirmado_ok"] = True
    if not titulo_preenchido(page, metadados["titulo_item"]):
        raise Exception("O título não parece preenchido; depósito cancelado.")

    if not metadados.get("data_preenchida_ok") and not data_preenchida(page, metadados):
        print("[AVISO] Não consegui confirmar a data automaticamente; vou seguir porque ela pode já estar preenchida na tela.")
        metadados["data_preenchida_ok"] = True

    print("[OK] Conteúdo obrigatório validado antes do depósito.")


def clicar_botao_depositar(page):
    print("[INFO] Clicando no botão Depositar...")

    url_antes = page.url
    fechar_menus_suspensos(page)

    try:
        page.mouse.click(20, 20)
        page.wait_for_timeout(300)
    except Exception:
        pass

    for tentativa in range(1, 3):
        page.keyboard.press("End")
        page.wait_for_timeout(1500)

        clicou = False

        try:
            botoes = page.locator("button:visible").filter(has_text=re.compile("Depositar", re.I))
            candidatos = []

            for i in range(botoes.count()):
                botao = botoes.nth(i)

                if botao.is_disabled(timeout=1000):
                    continue

                caixa = botao.bounding_box()
                if not caixa:
                    continue

                candidatos.append((caixa["y"], botao, caixa))

            if candidatos:
                _, botao, caixa = sorted(candidatos, key=lambda item: item[0], reverse=True)[0]
                botao.scroll_into_view_if_needed(timeout=3000)
                caixa = botao.bounding_box() or caixa
                page.mouse.click(caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
                clicou = True
                print(f"[OK] Clique em Depositar enviado. Tentativa {tentativa}/2.")
        except Exception:
            pass

        if not clicou:
            try:
                viewport = page.viewport_size or {"width": 1600, "height": 900}
                page.mouse.click(viewport["width"] - 70, viewport["height"] - 27)
                clicou = True
                print(f"[OK] Clique em Depositar por posição enviado. Tentativa {tentativa}/2.")
            except Exception:
                pass

        if not clicou:
            print(f"[AVISO] Não consegui clicar em Depositar na tentativa {tentativa}/2.")
            page.wait_for_timeout(3000)
            continue

        page.wait_for_timeout(8000)
        aguardar_pagina_estavel(page, timeout_rede=20000, ciclos=5)

        try:
            if page.url != url_antes:
                print("[OK] O site reagiu ao depósito.")
                return True
        except Exception:
            pass

        try:
            ainda_tem_depositar = page.locator("button:visible").filter(has_text=re.compile("Depositar", re.I)).count() > 0
            if not ainda_tem_depositar:
                print("[OK] O botão Depositar saiu da tela.")
                return True
        except Exception:
            return True

        if tentativa == 1:
            print("[AVISO] Nada mudou após o primeiro clique em Depositar. Vou tentar mais uma vez.")

    return False


def abrir_site_com_login_salvo(page):
    print(f"[INFO] Abrindo site: {URL_SITE}")
    navegar_com_tentativas(page, URL_SITE, "página inicial", tentativas=3, timeout=120000)
    aguardar_pagina_estavel(page)

    if usuario_logado(page):
        print("[OK] Login confirmado pelo perfil salvo.")
        aguardar_pos_login(page)
        return

    if tentar_login_com_credenciais_salvas(page):
        aguardar_pos_login(page)
        return

    raise Exception("Não foi possível confirmar o login automático. O robô não continuará deslogado.")


def aguardar_pos_login(page):
    print("[INFO] Aguardando a página estabilizar após o login...")
    aguardar_pagina_estavel(page, timeout_rede=45000, ciclos=12)

    for _ in range(20):
        try:
            if page.get_by_role("link", name=re.compile("Unidades Gestoras", re.I)).count() > 0:
                print("[OK] Página pronta após login.")
                return True
        except Exception:
            pass

        try:
            if page.locator("a:visible").filter(has_text=re.compile("Unidades Gestoras", re.I)).count() > 0:
                print("[OK] Página pronta após login.")
                return True
        except Exception:
            pass

        page.wait_for_timeout(500)

    print("[AVISO] Não confirmei o menu superior, mas a página terminou de carregar. Vou continuar.")
    return False


def aguardar_lista_unidades_carregar(page):
    print("[INFO] Aguardando a lista de Unidades Gestoras carregar...")

    for tentativa in range(1, 41):
        aguardar_pagina_estavel(page, timeout_rede=10000, ciclos=3)
        verificar_sessao(page, "carregar lista de unidades gestoras")

        try:
            if page.get_by_text(re.compile("Lista de Unidades Gestoras", re.I), exact=False).count() > 0:
                if page.get_by_text(re.compile("160109", re.I), exact=False).count() > 0:
                    page.get_by_text(re.compile("160109", re.I), exact=False).first.scroll_into_view_if_needed(timeout=3000)
                    print("[OK] Lista de Unidades Gestoras carregada.")
                    return True
        except Exception:
            pass

        try:
            carregou = page.evaluate(
                """() => {
                    const texto = (document.body.innerText || "").toLowerCase();
                    return texto.includes("lista de unidades gestoras") && texto.includes("160109");
                }"""
            )

            if carregou:
                print("[OK] Lista de Unidades Gestoras carregada.")
                return True
        except Exception:
            pass

        if tentativa in [10, 20, 30]:
            print("[INFO] A lista ainda está carregando. Vou aguardar mais um pouco...")

        page.wait_for_timeout(1000)

    return False


def abrir_lista_unidades_gestoras(page):
    print("[INFO] Acessando Unidades Gestoras...")
    page.keyboard.press("Escape")

    clicou = False
    try:
        link = page.get_by_role("link", name=re.compile("Unidades Gestoras", re.I)).first
        link.wait_for(state="visible", timeout=10000)
        link.click(timeout=10000)
        clicou = True
    except Exception:
        try:
            link = page.locator("a:visible").filter(has_text=re.compile("Unidades Gestoras", re.I)).first
            link.click(timeout=10000)
            clicou = True
        except Exception:
            pass

    if not clicou:
        print("[AVISO] Não consegui clicar no link Unidades Gestoras. Abrindo pelo endereço direto...")
        navegar_com_tentativas(page, URL_UNIDADES_GESTORAS, "página de Unidades Gestoras", tentativas=4, timeout=120000)

    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)
    verificar_sessao(page, "abrir lista de unidades gestoras")

    if not aguardar_lista_unidades_carregar(page):
        print("[AVISO] A lista não carregou após o clique. Recarregando pelo endereço direto...")
        navegar_com_tentativas(page, URL_UNIDADES_GESTORAS, "página de Unidades Gestoras", tentativas=4, timeout=120000)
        aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

        if not aguardar_lista_unidades_carregar(page):
            raise Exception("A página de Unidades Gestoras não carregou a lista com a UG 160109.")


def arvore_tem_texto(page, texto):
    try:
        alvo = normalizar(texto)
        return page.evaluate(
            """(alvo) => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .replace(/ª/g, "a")
                    .replace(/º/g, "o")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                return Array.from(document.querySelectorAll("a, span, div"))
                    .some((el) => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        if (style.display === "none" || style.visibility === "hidden" || box.width < 5 || box.height < 5) {
                            return false;
                        }
                        return normalizar(el.innerText || el.textContent || "").includes(alvo);
                    });
            }""",
            alvo,
        )
    except Exception:
        return False


def clicar_setinha_arvore(page, texto_alvo):
    alvo = normalizar(texto_alvo)

    try:
        return page.evaluate(
            """(alvo) => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .replace(/ª/g, "a")
                    .replace(/º/g, "o")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 4 &&
                        box.height >= 4;
                };

                const nos = Array.from(document.querySelectorAll("cdk-tree-node, [role='treeitem'], .cdk-tree-node"))
                    .filter((el) => visivel(el))
                    .filter((el) => normalizar(el.innerText || el.textContent || "").includes(alvo))
                    .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);

                for (const no of nos) {
                    const botao = no.querySelector("button[cdktreenodetoggle], button[aria-label*='toggle'], button[title*='toggle']");
                    if (!botao || !visivel(botao)) {
                        continue;
                    }

                    botao.scrollIntoView({ block: "center", inline: "nearest" });
                    botao.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, view: window }));
                    botao.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, view: window }));
                    botao.click();
                    return true;
                }

                const links = Array.from(document.querySelectorAll("a, h5, span, div"))
                    .filter((el) => visivel(el))
                    .filter((el) => {
                        const texto = normalizar(el.innerText || el.textContent || "");
                        if (!texto.includes(alvo)) {
                            return false;
                        }
                        const filhosComTexto = Array.from(el.children || [])
                            .some((filho) => normalizar(filho.innerText || filho.textContent || "").includes(alvo));
                        return !filhosComTexto || ["A", "H5", "SPAN"].includes(el.tagName);
                    });

                if (links.length === 0) {
                    return false;
                }

                const link = links
                    .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];

                link.scrollIntoView({ block: "center", inline: "nearest" });

                const linkBox = link.getBoundingClientRect();
                const candidatos = Array.from(document.querySelectorAll("button, i, svg, span, a, [role='button']"))
                    .filter((el) => visivel(el))
                    .map((el) => {
                        const box = el.getBoundingClientRect();
                        const classe = normalizar(el.getAttribute("class") || "");
                        const texto = normalizar(el.innerText || el.textContent || el.getAttribute("aria-label") || "");
                        return { el, box, classe, texto };
                    })
                    .filter(({ el, box, classe, texto }) => {
                        if (el === link || link.contains(el)) {
                            return false;
                        }

                        const mesmaLinha = Math.abs((box.top + box.height / 2) - (linkBox.top + linkBox.height / 2)) <= 18;
                        const ficaAntes = box.left < linkBox.left && box.left > linkBox.left - 80;
                        const pareceSetinha = classe.includes("angle") ||
                            classe.includes("chevron") ||
                            classe.includes("caret") ||
                            classe.includes("fa-chevron") ||
                            classe.includes("fa-angle") ||
                            texto === ">" ||
                            texto === "›" ||
                            texto === "▸";

                        return mesmaLinha && ficaAntes && pareceSetinha;
                    })
                    .sort((a, b) => b.box.left - a.box.left);

                if (candidatos.length > 0) {
                    candidatos[0].el.click();
                    return true;
                }

                return false;
            }""",
            alvo,
        )
    except Exception:
        return False


def expandir_arvore_ate_aparecer(page, texto_setinha, texto_esperado, descricao):
    if arvore_tem_texto(page, texto_esperado):
        print(f"[OK] {descricao} já está aberto.")
        return True

    for tentativa in range(1, 4):
        print(f"[INFO] Abrindo setinha de {descricao}... tentativa {tentativa}/3")

        if not clicar_setinha_arvore(page, texto_setinha):
            page.wait_for_timeout(1000)
            continue

        for _ in range(10):
            page.wait_for_timeout(500)
            verificar_sessao(page, f"expandir {descricao}")
            if arvore_tem_texto(page, texto_esperado):
                print(f"[OK] {descricao} aberto na árvore.")
                return True

    return False


def preparar_arvore_unidades(page):
    abrir_lista_unidades_gestoras(page)

    if not expandir_arvore_ate_aparecer(page, "160109", "Ano 2026", "UG 160109"):
        raise Exception("Não foi possível abrir a setinha da UG obrigatória 160109.")

    if not expandir_arvore_ate_aparecer(page, "Ano 2026", "1. Contratações Diretas", "Ano 2026"):
        raise Exception("Não foi possível abrir a setinha do Ano 2026.")

    if not expandir_arvore_ate_aparecer(page, "1. Contratações Diretas", "1.2. Inexigibilidade", "Contratações Diretas"):
        raise Exception("Não foi possível abrir a setinha de Contratações Diretas.")

    if not expandir_arvore_ate_aparecer(page, "2. Licitações", "2.1. Pregão", "Licitações"):
        print("[AVISO] Não consegui deixar Licitações expandido agora. Vou tentar novamente apenas se precisar.")
    else:
        expandir_arvore_ate_aparecer(page, "2.1. Pregão", "2.1.4 Pregão", "Pregão")


def localizar_url_categoria_na_arvore(page, tipo):
    nomes = CATEGORIAS_ARVORE.get(tipo, [])

    for nome in nomes:
        try:
            url = page.evaluate(
                """(alvo) => {
                    const normalizar = (texto) => (texto || "")
                        .normalize("NFD")
                        .replace(/[\\u0300-\\u036f]/g, "")
                        .replace(/ª/g, "a")
                        .replace(/º/g, "o")
                        .toLowerCase()
                        .replace(/\\s+/g, " ")
                        .trim();

                    const alvoNormalizado = normalizar(alvo);
                    const links = Array.from(document.querySelectorAll("a[href]"))
                        .filter((el) => {
                            const style = window.getComputedStyle(el);
                            const box = el.getBoundingClientRect();
                            if (style.display === "none" || style.visibility === "hidden" || box.width < 5 || box.height < 5) {
                                return false;
                            }
                            return normalizar(el.innerText || el.textContent || "").includes(alvoNormalizado);
                        });

                    if (links.length === 0) {
                        return null;
                    }

                    links[0].scrollIntoView({ block: "center", inline: "nearest" });
                    return links[0].href;
                }""",
                nome,
            )

            if url:
                return url
        except Exception:
            pass

    return None


def garantir_url_categoria_base(page, tipo):
    url = localizar_url_categoria_na_arvore(page, tipo)
    if url:
        return url

    if tipo in ["participante", "carona", "gerenciador", "pregao"]:
        expandir_arvore_ate_aparecer(page, "2. Licitações", "2.1. Pregão", "Licitações")
        expandir_arvore_ate_aparecer(page, "2.1. Pregão", "2.1.4 Pregão", "Pregão")

    url = localizar_url_categoria_na_arvore(page, tipo)
    if url:
        return url

    raise Exception(f"Não foi possível localizar o link da categoria na árvore para o tipo: {tipo}")


def abrir_categoria_em_nova_guia(context, pagina_base, tipo):
    pagina_base.bring_to_front()
    verificar_sessao(pagina_base, "usar guia base")

    url_categoria = garantir_url_categoria_base(pagina_base, tipo)
    print(f"[INFO] Abrindo guia de postagem: {url_categoria}")

    url_base_antes = pagina_base.url
    page = context.new_page()
    navegar_com_tentativas(page, url_categoria, "guia de postagem", tentativas=3, timeout=120000)

    if pagina_base.url != url_base_antes:
        print("[AVISO] A guia base mudou de endereço. Voltando para a árvore de Unidades Gestoras...")
        navegar_com_tentativas(pagina_base, URL_UNIDADES_GESTORAS, "página de Unidades Gestoras", tentativas=4, timeout=120000)
        aguardar_lista_unidades_carregar(pagina_base)

    page.bring_to_front()
    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

    if not page.url or page.url == "about:blank":
        navegar_com_tentativas(page, url_categoria, "guia de postagem", tentativas=3, timeout=120000)
        aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

    verificar_sessao(page, "abrir guia da categoria")

    return page


def abrir_ug_ano_categoria(page, categoria_site, tipo):
    print("[INFO] Acessando Unidades Gestoras...")

    page.keyboard.press("Escape")
    navegar_com_tentativas(page, URL_UNIDADES_GESTORAS, "página de Unidades Gestoras", tentativas=4, timeout=120000)
    aguardar_pagina_estavel(page)

    print("[INFO] Abrindo UG obrigatória 160109...")
    if not clicar_e_validar(
        page,
        [UG_OBRIGATORIA, "160109"],
        ["Ano 2026", "Ano 2025", "Comunidades desta Comunidade"],
        "UG 160109",
        timeout=15000,
        tentativas=2,
    ):
        print("[AVISO] Não encontrei a UG na primeira tentativa. Recarregando Unidades Gestoras...")
        navegar_com_tentativas(page, URL_UNIDADES_GESTORAS, "página de Unidades Gestoras", tentativas=4, timeout=120000)
        aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

        if not clicar_e_validar(
            page,
            [UG_OBRIGATORIA, "160109"],
            ["Ano 2026", "Ano 2025", "Comunidades desta Comunidade"],
            "UG 160109",
            timeout=15000,
            tentativas=2,
        ):
            raise Exception("Não foi possível abrir a UG obrigatória 160109.")
    aguardar_pagina_estavel(page, timeout_rede=15000, ciclos=5)

    print("[INFO] Abrindo Ano 2026...")
    if not clicar_e_validar(
        page,
        [ANO_OBRIGATORIO, "Ano 2026"],
        ["Contratações Diretas", "Licitações", "Comunidades desta Comunidade"],
        "Ano 2026",
        timeout=15000,
        tentativas=3,
    ):
        raise Exception("Não foi possível abrir o Ano 2026.")
    aguardar_pagina_estavel(page, timeout_rede=15000, ciclos=5)

    if tipo in ["dispensa", "inexigibilidade"]:
        print("[INFO] Abrindo Contratações Diretas...")
        if not clicar_e_validar(
            page,
            ["1. Contratações Diretas - 4ª Cia Com L Mth", "Contratações Diretas", "Contratacoes Diretas"],
            ["Dispensa", "Inexigibilidade", "Comunidades desta Comunidade"],
            "Contratações Diretas",
            timeout=12000,
            tentativas=3,
        ):
            raise Exception("Não foi possível abrir Contratações Diretas.")
        aguardar_pagina_estavel(page, timeout_rede=15000, ciclos=5)
    else:
        print("[INFO] Abrindo Licitações > Pregão...")
        if not clicar_e_validar(
            page,
            ["2. Licitações - 4ª Cia Com L Mth", "Licitações", "Licitacoes"],
            ["Pregão", "Pregao", "Comunidades desta Comunidade"],
            "Licitações",
            timeout=12000,
            tentativas=3,
        ):
            raise Exception("Não foi possível abrir Licitações.")
        aguardar_pagina_estavel(page, timeout_rede=15000, ciclos=5)
        if not clicar_e_validar(
            page,
            ["2.1. Pregão - 4ª Cia Com L Mth", "Pregão", "Pregao"],
            ["Participante", "Gerenciador", "Não Participante", "Nao Participante", "2.1.4 Pregão", "2.1.4 Pregao"],
            "Pregão",
            timeout=12000,
            tentativas=3,
        ):
            raise Exception("Não foi possível abrir Pregão.")
        aguardar_pagina_estavel(page, timeout_rede=15000, ciclos=5)

    print(f"[INFO] Entrando na categoria correta: {categoria_site}")
    opcoes_categoria = [categoria_site]

    if tipo == "dispensa":
        opcoes_categoria.extend(["1.1. Dispensa", "Dispensa Eletrônica", "Dispensa"])
    elif tipo == "inexigibilidade":
        opcoes_categoria.extend(["1.2. Inexigibilidade", "Inexigibilidade de Licitação", "Inexigibilidade"])
    elif tipo == "participante":
        opcoes_categoria.extend(["2.1.1 Participante", "Participante"])
    elif tipo == "carona":
        opcoes_categoria.extend(["2.1.2 Não Participante", "Não Participante", "Nao Participante"])
    elif tipo == "gerenciador":
        opcoes_categoria.extend(["2.1.3 Gerenciador", "Gerenciador"])

    
    elif tipo == "pregao":
        opcoes_categoria.extend(["2.1.4 Pregão", "2.1.4 Pregao", "Pregão - 4ª Cia Com L Mth", "Pregao - 4ª Cia Com L Mth"])
    sucesso = clicar_e_validar(
        page,
        opcoes_categoria,
        ["Novo", "Sub-Comunidade e Coleções", "Sub-Comunidade e Colecoes", "Coleções desta Comunidade", "Colecoes desta Comunidade"],
        "categoria final",
        timeout=15000,
        tentativas=3,
    )

    if not sucesso:
        raise Exception(f"Não foi possível abrir a categoria do site: {categoria_site}")

    aguardar_pagina_estavel(page)


def caixa_texto_lateral(page, texto):
    try:
        opcoes = page.get_by_text(texto, exact=True)
        for i in range(opcoes.count()):
            opcao = opcoes.nth(i)
            if not opcao.is_visible(timeout=500):
                continue

            caixa = opcao.bounding_box()
            if caixa and caixa["x"] < 330:
                return caixa
    except Exception:
        pass

    return None


def caixa_dentro_menu_novo(page, caixa):
    if not caixa:
        return False

    caixa_novo = caixa_texto_lateral(page, "Novo")
    if not caixa_novo:
        return False

    caixa_editar = caixa_texto_lateral(page, "Editar")
    y_opcao = caixa["y"] + caixa["height"] / 2
    y_novo = caixa_novo["y"] + caixa_novo["height"] / 2

    if y_opcao <= y_novo + 15:
        return False

    if caixa_editar:
        y_editar = caixa_editar["y"] + caixa_editar["height"] / 2
        if y_editar > y_novo and y_opcao >= y_editar - 5:
            return False

    return True


def menu_novo_aberto(page):
    try:
        for texto in ["Comunidade", "Coleção", "Item", "Processos"]:
            opcoes = page.get_by_text(texto, exact=True)
            for i in range(opcoes.count()):
                opcao = opcoes.nth(i)

                if not opcao.is_visible(timeout=500):
                    continue

                caixa = opcao.bounding_box()
                if caixa and 40 <= caixa["x"] < 330 and caixa["width"] >= 40 and caixa_dentro_menu_novo(page, caixa):
                    return True
    except Exception:
        pass

    return False


def abrir_menu_novo(page):
    aguardar_pagina_estavel(page, timeout_rede=15000, ciclos=5)

    if menu_novo_aberto(page):
        print("[OK] Menu Novo já está aberto.")
        return

    tentativas_coordenadas = []

    try:
        novo = page.get_by_text("Novo", exact=True).first
        caixa = novo.bounding_box()

        if caixa:
            y_novo = caixa["y"] + caixa["height"] / 2
            tentativas_coordenadas.extend([
                (caixa["x"] + caixa["width"] + 205, y_novo),
                (275, y_novo),
                (265, y_novo),
                (60, y_novo),
            ])
    except Exception:
        pass

    # Na barra lateral do DSpace, quem expande o grupo é a setinha à direita.
    tentativas_coordenadas.extend([
        (20, 122),
        (18, 122),
        (25, 122),
        (275, 120),
        (265, 120),
        (60, 120),
    ])

    for x, y in tentativas_coordenadas:
        try:
            page.mouse.click(x, y)
            page.wait_for_timeout(1200)

            if menu_novo_aberto(page):
                print("[OK] Menu Novo aberto.")
                return
        except Exception:
            pass

    try:
        page.get_by_text("Novo", exact=True).click(timeout=5000)
        page.wait_for_timeout(1000)

        if menu_novo_aberto(page):
            print("[OK] Menu Novo aberto.")
            return
    except Exception:
        pass

    try:
        page.locator("text=Novo").first.click(timeout=5000)
        page.wait_for_timeout(1000)

        if menu_novo_aberto(page):
            print("[OK] Menu Novo aberto.")
            return
    except Exception:
        pass

    try:
        page.locator(".fa-plus").first.click(timeout=5000)
        page.wait_for_timeout(1000)

        if menu_novo_aberto(page):
            print("[OK] Menu Novo aberto.")
            return
    except Exception:
        pass

    raise Exception("Não foi possível abrir o menu Novo.")


def clicar_opcao_menu_novo(page, tipo_novo):
    try:
        opcoes = page.get_by_text(tipo_novo, exact=True)
        qtd = opcoes.count()

        for i in range(qtd):
            opcao = opcoes.nth(i)

            if not opcao.is_visible(timeout=1000):
                continue

            caixa = opcao.bounding_box()
            if not caixa:
                continue

            # O menu Administrativo/Novo fica na lateral esquerda.
            if caixa["x"] > 330:
                continue

            if not caixa_dentro_menu_novo(page, caixa):
                continue

            opcao.scroll_into_view_if_needed(timeout=3000)
            opcao.click(timeout=5000, force=True)
            print(f"[OK] Opção '{tipo_novo}' clicada no menu Novo.")
            return True
    except Exception:
        pass

    try:
        opcoes = page.locator("a:visible, button:visible, div:visible, span:visible").filter(
            has_text=re.compile(rf"^\s*{re.escape(tipo_novo)}\s*$", re.I)
        )

        for i in range(min(opcoes.count(), 20)):
            opcao = opcoes.nth(i)
            caixa = opcao.bounding_box()

            if not caixa:
                continue

            if caixa["x"] > 330:
                continue

            if not caixa_dentro_menu_novo(page, caixa):
                continue

            opcao.scroll_into_view_if_needed(timeout=3000)
            opcao.click(timeout=5000, force=True)
            print(f"[OK] Opção '{tipo_novo}' clicada no menu Novo.")
            return True
    except Exception:
        pass

    try:
        novo = page.get_by_text("Novo", exact=True).first
        caixa_novo = novo.bounding_box()

        if caixa_novo:
            deslocamentos = {
                "Comunidade": 55,
                "Coleção": 112,
                "Item": 168,
                "Processos": 224,
            }

            if tipo_novo in deslocamentos:
                page.mouse.click(75, caixa_novo["y"] + deslocamentos[tipo_novo])
                page.wait_for_timeout(1000)
                print(f"[OK] Opção '{tipo_novo}' clicada por posição relativa no menu Novo.")
                return True
    except Exception:
        pass

    if tipo_novo == "Coleção":
        for x, y in [(82, 300), (95, 300), (110, 300), (80, 302)]:
            try:
                page.mouse.click(x, y)
                page.wait_for_timeout(1200)
                print("[OK] Opção 'Coleção' clicada por posição final no menu Novo.")
                return True
            except Exception:
                pass

    if tipo_novo == "Item":
        try:
            page.mouse.click(75, 365)
            page.wait_for_timeout(1000)
            print("[OK] Opção 'Item' clicada por posição final no menu Novo.")
            return True
        except Exception:
            pass

    return False


def destino_novo_abriu(page, tipo_novo):
    if tipo_novo == "Item":
        if modal_editar_item_aberto(page):
            return False
        return tela_criacao_item_aberta(page) or page.get_by_text(re.compile("Novo item|Criar um novo item", re.I)).count() > 0

    if tipo_novo == "Coleção":
        return tela_criacao_colecao_aberta(page) or modal_visivel(page)

    return True


def abrir_novo_tipo(page, tipo_novo):
    fechar_modal_se_aberto(page)
    fechar_menus_suspensos(page)

    if tipo_novo == "Coleção":
        abrir_menu_novo(page)
        print("[INFO] Clicando em Novo > Coleção...")

        if not clicar_opcao_menu_novo(page, "Coleção"):
            raise Exception("Não foi possível clicar em Novo > Coleção.")

        aguardar_pagina_estavel(page, timeout_rede=20000, ciclos=6)
        page.wait_for_timeout(2000)

        if not destino_novo_abriu(page, "Coleção"):
            print("[AVISO] Novo > Coleção não abriu a tela esperada; tentando por posição final.")
            if not clicar_opcao_menu_novo(page, "Coleção"):
                raise Exception("Não foi possível clicar em Novo > Coleção.")
            aguardar_pagina_estavel(page, timeout_rede=20000, ciclos=6)
            page.wait_for_timeout(2000)

        return

    for tentativa in range(1, 4):
        try:
            abrir_menu_novo(page)
        except Exception as erro:
            print(f"[AVISO] Nao consegui abrir o menu Novo na tentativa {tentativa}/3: {erro}")

            if tentativa < 3:
                print("[INFO] Vou aguardar mais um pouco e tentar abrir o menu Novo novamente.")
                aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)
                page.wait_for_timeout(3000)
                fechar_modal_se_aberto(page)
                fechar_menus_suspensos(page)
                continue

            raise

        print(f"[INFO] Clicando em Novo > {tipo_novo}... tentativa {tentativa}/3")
        if not clicar_opcao_menu_novo(page, tipo_novo):
            continue

        aguardar_pagina_estavel(page, timeout_rede=20000, ciclos=6)
        page.wait_for_timeout(2000)

        if destino_novo_abriu(page, tipo_novo):
            return

        print(f"[AVISO] Novo > {tipo_novo} não abriu a tela esperada; tentando novamente.")

    raise Exception(f"Não foi possível clicar em Novo > {tipo_novo}.")


def abrir_tela_criar_colecao_direto(page):
    try:
        achou = re.search(r"/communities/([^/?#]+)", page.url)
        if not achou:
            return False

        parent_id = achou.group(1)
        url_criar = f"https://licitacoeseb.4rm.eb.mil.br/collections/create?parent={parent_id}"

        print("[INFO] Abrindo tela de criação da coleção diretamente...")
        page.goto(url_criar)
        aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)
        for _ in range(10):
            if tela_criacao_colecao_aberta(page):
                return True
            page.wait_for_timeout(1000)

        return False
    except Exception:
        return False


def entrar_na_colecao_criada(page, metadados):
    nome_colecao = metadados["nome_colecao"]

    print("[INFO] Garantindo entrada na coleção criada...")
    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

    try:
        links = page.get_by_role("link", name=re.compile(re.escape(nome_colecao), re.I))
        if links.count() > 0 and links.first.is_visible(timeout=5000):
            links.first.click(timeout=10000)
            aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)
            print("[OK] Coleção aberta.")
            return
    except Exception:
        pass

    try:
        alvo = page.get_by_text(nome_colecao, exact=False).first
        if alvo.is_visible(timeout=5000):
            alvo.click(timeout=10000)
            aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)
            print("[OK] Coleção aberta.")
            return
    except Exception:
        pass

    print("[AVISO] Não consegui confirmar a abertura da coleção pelo nome; vou tentar criar o item na página atual.")


def localizar_url_colecao_visivel(page, nome_colecao):
    alvo = normalizar(nome_colecao)

    try:
        return page.evaluate(
            """(alvo) => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .replace(/ª/g, "a")
                    .replace(/º/g, "o")
                    .replace(/[–—]/g, "-")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const alvoNorm = normalizar(alvo);
                const links = Array.from(document.querySelectorAll("a[href]"))
                    .map((el) => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        const texto = normalizar(el.innerText || el.textContent || "");
                        const href = el.href || "";
                        const visivel = style.display !== "none" &&
                            style.visibility !== "hidden" &&
                            box.width >= 5 &&
                            box.height >= 5;

                        return { el, texto, href, visivel };
                    })
                    .filter(({ texto, href, visivel }) => {
                        if (!visivel || !texto || !href) {
                            return false;
                        }

                        const pareceColecao = href.includes("/collections/") ||
                            href.includes("/handle/") ||
                            href.includes("/communities/");

                        return pareceColecao && texto === alvoNorm;
                    });

                links.sort((a, b) => {
                    const aExato = a.texto === alvoNorm ? 0 : 1;
                    const bExato = b.texto === alvoNorm ? 0 : 1;
                    return aExato - bExato;
                });

                return links.length > 0 ? links[0].href : null;
            }""",
            alvo,
        )
    except Exception:
        return None


def ir_para_proxima_pagina_colecoes(page):
    try:
        avancou = page.evaluate(
            """() => {
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase()
                    .replace(/\\s+/g, " ")
                    .trim();

                const visivel = (el) => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        box.width >= 5 &&
                        box.height >= 5;
                };

                const candidatos = Array.from(document.querySelectorAll("a, button"))
                    .filter((el) => {
                        if (!visivel(el)) {
                            return false;
                        }

                        const texto = normalizar(el.innerText || el.textContent || "");
                        const aria = normalizar(el.getAttribute("aria-label") || "");
                        const titulo = normalizar(el.getAttribute("title") || "");
                        const classe = normalizar(el.getAttribute("class") || "");
                        const disabled = el.disabled ||
                            el.getAttribute("aria-disabled") === "true" ||
                            classe.includes("disabled");

                        if (disabled) {
                            return false;
                        }

                        return texto === ">" ||
                            texto === "proxima" ||
                            texto === "next" ||
                            aria.includes("proxima") ||
                            aria.includes("next") ||
                            titulo.includes("proxima") ||
                            titulo.includes("next");
                    });

                if (candidatos.length === 0) {
                    return false;
                }

                candidatos[candidatos.length - 1].scrollIntoView({ block: "center", inline: "center" });
                candidatos[candidatos.length - 1].click();
                return true;
            }"""
        )

        if avancou:
            aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)
            page.wait_for_timeout(1000)
            return True
    except Exception:
        pass

    return False


def abrir_colecao_existente_se_houver(page, metadados):
    nome_colecao = metadados["nome_colecao"]

    print("[INFO] Verificando se a coleção já existe nesta comunidade...")
    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

    urls_visitadas = set()

    for pagina in range(1, 8):
        url_atual = page.url
        if url_atual in urls_visitadas:
            break
        urls_visitadas.add(url_atual)

        url = localizar_url_colecao_visivel(page, nome_colecao)

        if url:
            print("[INFO] Coleção já existe nesta comunidade. Abrindo coleção existente...")
            navegar_com_tentativas(page, url, "coleção existente", tentativas=3, timeout=120000)
            aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)
            print("[OK] Coleção existente aberta.")
            return True

        if pagina == 1:
            print("[INFO] Coleção não apareceu na primeira página da lista. Vou verificar próximas páginas, se houver.")

        if not ir_para_proxima_pagina_colecoes(page):
            break

    return False


def item_ja_existe_na_colecao(page, titulo_item):
    alvo = normalizar(titulo_item)

    print("[INFO] Verificando se o item já existe dentro da coleção...")
    aguardar_pagina_estavel(page, timeout_rede=30000, ciclos=8)

    urls_visitadas = set()

    for pagina in range(1, 6):
        url_atual = page.url
        if url_atual in urls_visitadas:
            break
        urls_visitadas.add(url_atual)

        try:
            encontrou = page.evaluate(
                """(alvo) => {
                    const normalizar = (texto) => (texto || "")
                        .normalize("NFD")
                        .replace(/[\\u0300-\\u036f]/g, "")
                        .replace(/Âª/g, "a")
                        .replace(/Âº/g, "o")
                        .replace(/[â€“â€”]/g, "-")
                        .toLowerCase()
                        .replace(/\\s+/g, " ")
                        .trim();

                    const alvoNorm = normalizar(alvo);
                    const visivel = (el) => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        return style.display !== "none" &&
                            style.visibility !== "hidden" &&
                            box.width >= 5 &&
                            box.height >= 5;
                    };

                    const candidatos = Array.from(document.querySelectorAll("a[href], h1, h2, h3, h4, h5, h6, span, div, td"))
                        .filter(visivel)
                        .map((el) => {
                            const texto = normalizar(el.innerText || el.textContent || "");
                            const href = el.href || "";
                            const pareceItem = href.includes("/items/") ||
                                href.includes("/handle/") ||
                                texto.includes("vol i") ||
                                texto.includes("vol 1") ||
                                texto.includes("ne");

                            return { texto, href, pareceItem };
                        })
                        .filter(({ texto, pareceItem }) => pareceItem && texto);

                    return candidatos.some(({ texto }) => texto === alvoNorm || texto.includes(alvoNorm));
                }""",
                alvo,
            )

            if encontrou:
                print("[OK] Item com este título já existe na coleção.")
                return True
        except Exception:
            pass

        if pagina == 1:
            print("[INFO] Item não apareceu na primeira página da coleção. Vou verificar próximas páginas, se houver.")

        if not ir_para_proxima_pagina_colecoes(page):
            break

    print("[OK] Não encontrei item igual nesta coleção.")
    return False


def criar_colecao(page, metadados):
    print("[INFO] Criando coleção...")

    if abrir_colecao_existente_se_houver(page, metadados):
        return

    if not abrir_tela_criar_colecao_direto(page):
        print("[AVISO] Não consegui abrir a criação direta. Tentando pelo menu Novo > Coleção...")
        abrir_novo_tipo(page, "Coleção")

    page.wait_for_timeout(2000)

    if tela_criacao_colecao_aberta(page):
        print("[OK] Tela de criação da coleção aberta diretamente.")
    else:
        print("[INFO] Clicando na primeira opção do modal de coleção...")

        if not clicar_primeira_opcao_modal(page, tipo_modal="colecao"):
            raise Exception("Não foi possível clicar na primeira opção do modal de coleção.")

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)

    print(f"[INFO] Nome da coleção: {metadados['nome_colecao']}")

    if not garantir_tela_criacao_colecao(page):
        raise Exception("A tela de criação da coleção não abriu depois de selecionar a primeira opção.")

    # Campo Nome da coleção
    if not preencher_nome_colecao(page, metadados["nome_colecao"]):
        raise Exception("Não foi possível preencher o Nome da coleção.")

    if not campo_com_valor(page, metadados["nome_colecao"]):
        print("[AVISO] O nome da coleção não foi confirmado no campo. Tentando preencher novamente...")
        if not preencher_nome_colecao(page, metadados["nome_colecao"]):
            raise Exception("O Nome da coleção não ficou preenchido.")

    # Descrição curta
    if not preencher_descricao_curta_colecao(page, metadados["descricao_curta"]):
        print("[AVISO] Não consegui preencher a descrição curta automaticamente.")

    preencher_tipo_colecao_se_existir(page)

    page.keyboard.press("End")
    page.wait_for_timeout(1000)

    if not salvar_colecao_e_aguardar(page):
        raise Exception("Não foi possível clicar no botão de salvar/criar coleção.")

    entrar_na_colecao_criada(page, metadados)

    print("[OK] Coleção criada.")


def criar_item_e_postar_pdf(page, metadados):
    print("[INFO] Criando item dentro da coleção...")

    abrir_novo_tipo(page, "Item")

    page.wait_for_timeout(2000)

    print("[INFO] Clicando na primeira opção do modal de item...")

    if not clicar_primeira_opcao_modal(page, tipo_modal="item"):
        raise Exception("Não foi possível clicar na primeira opção do modal de item.")

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)

    print(f"[INFO] Título do item: {metadados['titulo_item']}")

    # Upload do arquivo
    caminho_pdf = str(metadados["arquivo"])

    garantir_upload_pdf(page, caminho_pdf)
    metadados["upload_confirmado_ok"] = True

    # Title
    try:
        page.locator("input[placeholder='Title']").first.fill(metadados["titulo_item"], timeout=8000)
        print("[OK] Title preenchido.")
    except Exception:
        try:
            page.get_by_label(re.compile("Title", re.I)).first.fill(metadados["titulo_item"], timeout=8000)
            print("[OK] Title preenchido.")
        except Exception:
            if not preencher_primeiro_input_visivel(page, metadados["titulo_item"], "Title"):
                raise Exception("Não foi possível preencher o Title.")

    # Date of Issue
    if not preencher_data_publicacao(page, metadados):
        print("[AVISO] Não consegui confirmar a data pelo código, mas vou seguir porque o site pode já ter preenchido visualmente.")
        metadados["data_preenchida_ok"] = True

    # Type, se for obrigatório
    try:
        page.locator("select").first.select_option(label="Other", timeout=3000)
    except Exception:
        pass

    page.keyboard.press("End")
    page.wait_for_timeout(1000)

    # Confirmar licença
    try:
        page.get_by_text("I confirm the license above", exact=False).click(timeout=5000)
        print("[OK] Licença confirmada.")
    except Exception:
        try:
            page.locator("input[type='checkbox']").last.check(timeout=5000)
            print("[OK] Checkbox de licença marcado.")
        except Exception:
            print("[AVISO] Não consegui marcar a licença automaticamente.")

    page.wait_for_timeout(1000)

    print("\n==============================")
    print("CONFIRA ANTES DE DEPOSITAR")
    print("==============================")
    print(f"Arquivo: {metadados['arquivo'].name}")
    print(f"Coleção: {metadados['nome_colecao']}")
    print(f"Descrição curta: {metadados['descricao_curta']}")
    print(f"Title: {metadados['titulo_item']}")
    print(f"Páginas: {metadados['paginas']}")
    print(f"DIEx: {metadados['diex']}")
    print(f"Dispensa: {metadados['dispensa']}")
    print(f"SRP: {metadados['srp']}")
    print(f"UG: {metadados['ug']}")
    print(f"NE: {metadados['ne']}")
    print("==============================\n")

    if CONFIRMAR_ANTES_DEPOSITAR:
        resposta = input("Deseja clicar em DEPOSITAR agora? Digite S para sim: ").strip().lower()
        if resposta != "s":
            print("[CANCELADO] O robô não clicou em Depositar.")
            return False

    if CLICAR_DEPOSITAR:
        validar_conteudo_antes_depositar(page, metadados, caminho_pdf)

        clicou = clicar_botao_depositar(page)

        if not clicou:
            raise Exception("Não foi possível clicar no botão Depositar.")

        aguardar_deposito_concluido(page)

        print("[OK] Item depositado.")
        return True

    print("[INFO] CLICAR_DEPOSITAR está como False. Nada foi depositado.")
    return False


# =========================
# EXECUÇÃO PRINCIPAL
# =========================

def fechar_navegador(context):
    try:
        context.close()
    except Exception:
        pass


def abrir_navegador_logado(p, opcoes_firefox):
    context = p.firefox.launch_persistent_context(**opcoes_firefox)
    pagina_base = context.pages[0] if context.pages else context.new_page()

    for pagina_antiga in list(context.pages):
        if pagina_antiga != pagina_base:
            try:
                pagina_antiga.close()
            except Exception:
                pass

    abrir_site_com_login_salvo(pagina_base)
    preparar_arvore_unidades(pagina_base)
    return context, pagina_base


def atualizar_pagina_base(pagina_base):
    print("[INFO] Atualizando a pagina inicial antes de tentar novamente...")
    pagina_base.bring_to_front()
    pagina_base.reload(wait_until="domcontentloaded", timeout=120000)
    aguardar_pagina_estavel(pagina_base, timeout_rede=15000, ciclos=5)


def main():
    pendentes = listar_pdfs_nao_postados()

    if not pendentes:
        print("[FIM] Nenhum PDF novo encontrado nas pastas configuradas.")
        return

    print("\nATENÇÃO:")
    print("O robô irá postar todos os PDFs pendentes, sempre um por vez.")
    print("O navegador ficará aberto; para cada PDF o robô abre só uma guia de postagem e fecha essa guia ao concluir.")
    print("Cada PDF será registrado no controle somente depois do depósito confirmado.")

    with sync_playwright() as p:
        total = len(pendentes)
        postados_agora = 0
        pulados_agora = 0

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

        context, pagina_base = abrir_navegador_logado(p, opcoes_firefox)

        try:
            for indice, escolhido in enumerate(pendentes, start=1):
                pdf = escolhido["pdf"]
                categoria_site = escolhido["categoria_site"]
                tipo = escolhido["tipo"]

                if ja_postado(pdf):
                    print(f"\n[PULADO] ({indice}/{total}) PDF já registrado como postado: {pdf.name}")
                    continue


                if pdf_maior_que_limite(pdf):
                    motivo = f"PDF com {descrever_tamanho_pdf(pdf)}, igual ou acima de {TAMANHO_MAXIMO_PDF_MB} MB."
                    print(f"\n[PULADO] ({indice}/{total}) {motivo}")
                    novo_pdf = marcar_pdf_pulado(pdf, motivo)
                    pulados_agora += 1
                    print(f"[PULADO] Vou seguir para o proximo PDF: {novo_pdf.name}")
                    continue
                tentativa_relogin = 1

                while tentativa_relogin <= MAX_TENTATIVAS_RELOGIN:
                    page = None

                    print("\n" + "=" * 70)
                    print(f"[PROCESSANDO] PDF {indice}/{total}")
                    print(f"Tentativa deste PDF: {tentativa_relogin}/{MAX_TENTATIVAS_RELOGIN}")
                    print(f"Arquivo: {pdf}")
                    print(f"Pasta local: {escolhido['pasta_local']}")
                    print(f"Tipo: {tipo}")
                    print(f"Categoria site: {categoria_site}")

                    try:
                        if not pdf.exists():
                            motivo = f"PDF nao encontrado no caminho esperado: {pdf}"
                            print(f"[PULADO] {motivo}")
                            registrar_pulado(pdf, motivo)
                            pulados_agora += 1
                            break

                        pdf_para_postar = preparar_pdf_para_postagem(pdf)

                        print("[INFO] Lendo PDF e montando metadados...")
                        metadados = montar_metadados(pdf_para_postar, tipo)

                        print("\nMetadados extraídos:")
                        for chave, valor in metadados.items():
                            if chave != "arquivo":
                                print(f"{chave}: {valor}")

                        page = abrir_categoria_em_nova_guia(context, pagina_base, tipo)

                        criar_colecao(page, metadados)
                        verificar_sessao(page, "criar coleção")


                        if item_ja_existe_na_colecao(page, metadados["titulo_item"]):
                            print("[PULADO] O item ja existe nesta colecao. Nao vou criar duplicado.")
                            registrar_postado(pdf)
                            novo_pdf = renomear_pdf_postado(pdf)
                            registrar_postado(novo_pdf)
                            postados_agora += 1
                            print(f"[OK] Registrado como ja postado no site: {novo_pdf.name}")
                            if page:
                                try:
                                    page.close()
                                except Exception:
                                    pass
                            break
                        sucesso_postagem = criar_item_e_postar_pdf(page, metadados)
                        verificar_sessao(page, "postar item")

                        if not sucesso_postagem:
                            raise Exception(f"Postagem encerrada sem depósito confirmado para: {pdf}")

                        registrar_postado(pdf)
                        novo_pdf = renomear_pdf_postado(pdf)
                        registrar_postado(novo_pdf)
                        postados_agora += 1
                        print(f"[OK] Registrado como postado: {novo_pdf.name}")

                    except SessaoExpirada as erro:
                        print("\n[AVISO] Sessão caiu.")
                        print(erro)

                        if page:
                            try:
                                page.close()
                            except Exception:
                                pass

                        if tentativa_relogin >= MAX_TENTATIVAS_RELOGIN:
                            print("[ERRO] A sessão caiu repetidas vezes neste PDF.")
                            novo_pdf = marcar_pdf_pulado(pdf, str(erro))
                            pulados_agora += 1
                            print(f"[PULADO] Vou seguir para o proximo PDF: {novo_pdf.name}")
                            break

                        tentativa_relogin += 1
                        print("[INFO] Vou fechar o navegador, abrir de novo, refazer login e tentar o mesmo PDF novamente.")
                        fechar_navegador(context)
                        context, pagina_base = abrir_navegador_logado(p, opcoes_firefox)
                        continue

                    except UploadTravado as erro:
                        print("\n[AVISO] Upload travou ou o site engasgou neste PDF.")
                        print(erro)

                        if page:
                            try:
                                page.close()
                            except Exception:
                                pass

                        if "3 tentativas" in str(erro) or "apos 3 tentativas" in str(erro):
                            print("[ERRO] O upload nao confirmou visualmente apos 3 tentativas.")
                            novo_pdf = marcar_pdf_pulado(pdf, str(erro))
                            pulados_agora += 1
                            print(f"[PULADO] Vou seguir para o proximo PDF: {novo_pdf.name}")
                            break

                        if tentativa_relogin >= MAX_TENTATIVAS_RELOGIN:
                            print("[ERRO] O upload travou repetidas vezes neste PDF.")
                            novo_pdf = marcar_pdf_pulado(pdf, str(erro))
                            pulados_agora += 1
                            print(f"[PULADO] Vou seguir para o proximo PDF: {novo_pdf.name}")
                            break

                        tentativa_relogin += 1
                        print("[INFO] Vou fechar esta guia, atualizar a pagina inicial e tentar o mesmo PDF novamente do zero.")

                        try:
                            atualizar_pagina_base(pagina_base)
                            preparar_arvore_unidades(pagina_base)
                            verificar_sessao(pagina_base, "retomar guia inicial após upload travado")
                        except SessaoExpirada:
                            fechar_navegador(context)
                            context, pagina_base = abrir_navegador_logado(p, opcoes_firefox)
                        except Exception as erro_retomada:
                            print(f"[AVISO] Nao consegui retomar a guia inicial direto: {erro_retomada}")
                            fechar_navegador(context)
                            context, pagina_base = abrir_navegador_logado(p, opcoes_firefox)

                        continue

                    except Exception as erro:
                        if page and sessao_caiu(page):
                            print("\n[AVISO] Sessão caiu durante a operação.")
                            try:
                                page.close()
                            except Exception:
                                pass

                            if tentativa_relogin >= MAX_TENTATIVAS_RELOGIN:
                                print("[ERRO] A sessão caiu repetidas vezes neste PDF.")
                                novo_pdf = marcar_pdf_pulado(pdf, str(erro))
                                pulados_agora += 1
                                print(f"[PULADO] Vou seguir para o proximo PDF: {novo_pdf.name}")
                                break

                            tentativa_relogin += 1
                            print("[INFO] Vou fechar o navegador, abrir de novo, refazer login e tentar o mesmo PDF novamente.")
                            fechar_navegador(context)
                            context, pagina_base = abrir_navegador_logado(p, opcoes_firefox)
                            continue

                        print("\n[AVISO] O site falhou ou nao carregou uma etapa deste PDF.")
                        print(erro)

                        if tentativa_relogin >= MAX_TENTATIVAS_RELOGIN:
                            print("\n[ERRO GERAL]")
                            print("[ERRO] A mesma postagem falhou repetidas vezes neste PDF.")
                            print("[PULADO] Vou fechar a guia do erro e continuar.")
                            if page:
                                try:
                                    page.close()
                                except Exception:
                                    pass
                            novo_pdf = marcar_pdf_pulado(pdf, str(erro))
                            pulados_agora += 1
                            print(f"[PULADO] Vou seguir para o proximo PDF: {novo_pdf.name}")
                            break

                        if page:
                            try:
                                page.close()
                            except Exception:
                                pass

                        tentativa_relogin += 1
                        print("[INFO] Vou fechar a guia ruim, voltar para a pagina inicial e tentar o mesmo PDF novamente.")

                        try:
                            atualizar_pagina_base(pagina_base)
                            verificar_sessao(pagina_base, "retomar guia inicial apos falha geral")
                            preparar_arvore_unidades(pagina_base)
                        except SessaoExpirada:
                            fechar_navegador(context)
                            context, pagina_base = abrir_navegador_logado(p, opcoes_firefox)
                        except Exception as erro_retomada:
                            print(f"[AVISO] Nao consegui retomar a guia inicial direto: {erro_retomada}")
                            fechar_navegador(context)
                            context, pagina_base = abrir_navegador_logado(p, opcoes_firefox)

                        continue

                    else:
                        if page:
                            try:
                                page.close()
                            except Exception:
                                pass
                        pagina_base.bring_to_front()
                        print("[OK] Guia de postagem fechada. Voltando para a guia inicial e indo para o próximo PDF...")
                        break

                else:
                    continue

        finally:
            try:
                context.close()
            except Exception:
                pass

        print("\n[FINALIZADO]")
        print(f"PDFs pulados nesta execucao: {pulados_agora}")
        print(f"Postagens concluídas nesta execução: {postados_agora}")
        print(f"PDFs pendentes conferidos no início: {total}")


if __name__ == "__main__":
    main()
