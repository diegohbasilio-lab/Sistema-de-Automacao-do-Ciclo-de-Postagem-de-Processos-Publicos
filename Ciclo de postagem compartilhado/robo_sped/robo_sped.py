from playwright.sync_api import sync_playwright
from pathlib import Path
import re
import time
import shutil
try:
    from PyPDF2 import PdfReader
except ModuleNotFoundError:
    from pypdf import PdfReader

# ten_eros
# Montanha@123

URL_LOGIN = "http://sped3.4ciacomlmth.eb.mil.br/#/"
URL_PROCESSOS = "http://sped3.4ciacomlmth.eb.mil.br/#/processos-encaminhados"
ANO_ALVO = "2026"
MAX_TENTATIVAS_PROCESSO = 3

PASTA_BASE = Path(r"C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped")
PASTA_DOWNLOADS = PASTA_BASE / "Downloads"
PASTA_SEM_NE = PASTA_BASE / "SEM_NOTA_DE_EMPENHO"
PASTA_PULADOS = PASTA_BASE / "PULADOS"
PASTA_TEMP = PASTA_BASE / "TEMP"

PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)
PASTA_SEM_NE.mkdir(parents=True, exist_ok=True)
PASTA_PULADOS.mkdir(parents=True, exist_ok=True)
PASTA_TEMP.mkdir(parents=True, exist_ok=True)


def limpar_nome(nome):
    nome = nome.replace("/", "-")
    nome = re.sub(r'[\\:*?"<>|]', "", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome[:180]


def normalizar_texto(texto):
    texto = texto.upper()

    substituicoes = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Õ": "O", "Ô": "O",
        "Ú": "U",
        "Ç": "C",
    }

    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def identificar_anos(texto):
    return sorted(set(re.findall(r"\b20\d{2}\b", texto or "")))


def deve_processar_por_ano(texto):
    """
    Se o texto informar algum ano, processa somente quando houver o ano alvo.
    Quando a tela nao mostra ano nenhum, deixa o fluxo seguir para validar depois.
    """

    anos = identificar_anos(texto)

    if not anos:
        return True, "ano nao identificado na tela"

    if ANO_ALVO in anos:
        return True, f"ano {ANO_ALVO} encontrado"

    return False, f"anos encontrados: {', '.join(anos)}"


def extrair_texto_pdf(caminho_pdf):
    texto_total = ""

    try:
        reader = PdfReader(str(caminho_pdf))

        for pagina in reader.pages:
            texto = pagina.extract_text() or ""
            texto_total += "\n" + texto

    except Exception as erro:
        print(f"ERRO ao ler PDF: {caminho_pdf}")
        print(f"Detalhe: {erro}")
        return ""

    return texto_total


def identificar_notas_empenho(texto):
    """
    Retorna uma lista de possíveis Notas de Empenho encontradas.

    A função procura padrões fortes, como:
    - 2025NE000123
    - 2026NE000045
    - 1605232025NE000123
    - 1671582024NE000251
    - NE 000123 quando o texto também menciona NOTA DE EMPENHO
    """

    texto_norm = normalizar_texto(texto)

    notas_encontradas = []

    padroes_fortes = [
        # Exemplo: 1605232025NE000123
        r"\b\d{6}\s*20\d{2}\s*NE\s*\d{6}\b",

        # Exemplo: 167158 2024 NE 000251
        r"\b\d{6}\s+20\d{2}\s+NE\s+\d{6}\b",

        # Exemplo: 2025NE000123
        r"\b20\d{2}\s*NE\s*\d{6}\b",

        # Exemplo: 2025 NE 000123
        r"\b20\d{2}\s+NE\s+\d{6}\b",
    ]

    for padrao in padroes_fortes:
        encontrados = re.findall(padrao, texto_norm)

        for item in encontrados:
            item_limpo = re.sub(r"\s+", "", item)
            if item_limpo not in notas_encontradas:
                notas_encontradas.append(item_limpo)

    # Análise complementar:
    # Só aceita "NE 000123" se o documento mencionar claramente Nota de Empenho.
    menciona_nota_empenho = (
        "NOTA DE EMPENHO" in texto_norm
        or "NOTA DE EMPENHO DA DESPESA" in texto_norm
        or "EMPENHO DA DESPESA" in texto_norm
        or "NATUREZA DE DESPESA" in texto_norm
        or "EMISSAO" in texto_norm and "EMPENHO" in texto_norm
    )

    if menciona_nota_empenho:
        padroes_complementares = [
            r"\bNE\s*N?[ºO°.]?\s*\d{6}\b",
            r"\bEMPENHO\s*N?[ºO°.]?\s*\d{6}\b",
            r"\bNUMERO\s+DO\s+EMPENHO\s*N?[ºO°.]?\s*\d{6}\b",
        ]

        for padrao in padroes_complementares:
            encontrados = re.findall(padrao, texto_norm)

            for item in encontrados:
                item_limpo = re.sub(r"\s+", " ", item).strip()

                # Evita aceitar textos muito genéricos sem número.
                if re.search(r"\d{6}", item_limpo):
                    if item_limpo not in notas_encontradas:
                        notas_encontradas.append(item_limpo)

    return notas_encontradas


def possui_nota_empenho(caminho_pdf):
    texto = extrair_texto_pdf(caminho_pdf)

    if not texto.strip():
        print("ATENÇÃO: Não foi possível extrair texto do PDF.")
        return False, []

    notas = identificar_notas_empenho(texto)

    if notas:
        return True, notas

    return False, []


def remover_se_existir(caminho):
    if caminho.exists():
        caminho.unlink()


def mover_substituindo(origem, destino):
    """
    Move o arquivo para o destino.
    Se já existir arquivo com mesmo nome, substitui.
    """

    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        print(f"Arquivo já existia e será substituído: {destino.name}")
        destino.unlink()

    shutil.move(str(origem), str(destino))


def remover_arquivo_da_pasta_errada(nome_arquivo, pasta_correta):
    """
    Garante que o mesmo arquivo não fique nas duas categorias.
    Se o processo for COM NE, remove da pasta SEM_NE.
    Se o processo for SEM NE, remove da pasta Downloads.
    """

    possiveis_pastas = [
        PASTA_DOWNLOADS,
        PASTA_SEM_NE,
    ]

    for pasta in possiveis_pastas:
        caminho = pasta / nome_arquivo

        if pasta != pasta_correta and caminho.exists():
            print(f"Removendo arquivo da pasta errada: {caminho}")
            caminho.unlink()


def descartar_temporario(caminho_temp):
    if caminho_temp.exists():
        print(f"Descartando download temporario: {caminho_temp.name}")
        caminho_temp.unlink()


def registrar_pulado(page, pagina_atual, indice_linha, motivo):
    linhas = page.locator("table tbody tr")
    texto_linha = ""

    try:
        texto_linha = linhas.nth(indice_linha).inner_text().strip()
    except Exception:
        pass

    identificacao = limpar_nome(texto_linha) if texto_linha else ""

    if identificacao:
        nome_arquivo = f"PULADO - {identificacao}.txt"
    else:
        nome_arquivo = f"PULADO - pagina {pagina_atual} - processo {indice_linha + 1}.txt"

    caminho_pulado = PASTA_PULADOS / nome_arquivo

    contador = 2
    while caminho_pulado.exists():
        caminho_pulado = PASTA_PULADOS / f"{caminho_pulado.stem} ({contador}).txt"
        contador += 1

    caminho_pulado.write_text(
        "\n".join(
            [
                "PULADO",
                f"Pagina: {pagina_atual}",
                f"Processo na pagina: {indice_linha + 1}",
                f"Motivo: {motivo}",
                f"Tentativas: {MAX_TENTATIVAS_PROCESSO}",
                f"Texto da linha: {texto_linha}",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Processo marcado como PULADO: {caminho_pulado}")
    return caminho_pulado


def esperar_tabela(page):
    page.wait_for_selector("table tbody tr", timeout=20000)


def voltar_para_pagina(page, pagina_atual):
    page.goto(URL_PROCESSOS)
    page.wait_for_load_state("networkidle")
    esperar_tabela(page)

    for _ in range(1, pagina_atual):
        page.locator(".ui-paginator-next").last.click()
        page.wait_for_timeout(1500)
        esperar_tabela(page)


def existe_proxima_pagina(page):
    proximo = page.locator(".ui-paginator-next").last
    classe = proximo.get_attribute("class") or ""
    return "ui-state-disabled" not in classe


def baixar_processo(page, indice_linha):
    linhas = page.locator("table tbody tr")
    linha = linhas.nth(indice_linha)

    linha.click()
    page.wait_for_timeout(500)

    page.locator("button[name='btnView']").click()
    page.wait_for_timeout(2500)

    page.wait_for_selector("text=Documentos assinados", timeout=20000)

    tabela_docs = page.locator(
        "fieldset:has-text('Documentos assinados') table tbody tr"
    )

    primeira_linha_doc = tabela_docs.first
    colunas_doc = primeira_linha_doc.locator("td")

    numero_doc = colunas_doc.nth(4).inner_text().strip()
    assunto_doc = colunas_doc.nth(5).inner_text().strip()

    texto_documento_tela = f"{numero_doc} {assunto_doc}"
    pode_processar, motivo_ano = deve_processar_por_ano(texto_documento_tela)

    if not pode_processar:
        print(f"Ignorado: documento nao e de {ANO_ALVO} ({motivo_ano}).")
        return "ignorado_ano"

    nome_final = limpar_nome(f"{numero_doc} - {assunto_doc}.pdf")

    caminho_ja_com_ne = PASTA_DOWNLOADS / nome_final
    caminho_ja_sem_ne = PASTA_SEM_NE / nome_final

    if caminho_ja_com_ne.exists():
        print(f"Ignorado: arquivo ja baixado com Nota de Empenho: {nome_final}")
        if caminho_ja_sem_ne.exists():
            print("Removendo copia antiga da pasta SEM_NOTA_DE_EMPENHO.")
            caminho_ja_sem_ne.unlink()
        return "ja_baixado"

    ja_estava_sem_ne = caminho_ja_sem_ne.exists()

    if ja_estava_sem_ne:
        print(
            "Arquivo ja existe em SEM_NOTA_DE_EMPENHO. "
            "Vou baixar novamente apenas para conferir se agora possui NE."
        )

    caminho_temp = PASTA_TEMP / nome_final

    remover_se_existir(caminho_temp)

    print(f"Baixando temporariamente para análise: {nome_final}")

    with page.expect_download(timeout=60000) as download_info:
        page.locator("#impressaoProcesso").click()

    download = download_info.value
    download.save_as(str(caminho_temp))

    print("Analisando existência de Nota de Empenho...")

    tem_ne, notas_encontradas = possui_nota_empenho(caminho_temp)

    if tem_ne:
        pasta_destino = PASTA_DOWNLOADS
        caminho_final = pasta_destino / nome_final

        print("Nota de Empenho encontrada.")
        print(f"NE(s) identificada(s): {', '.join(notas_encontradas)}")

        remover_arquivo_da_pasta_errada(nome_final, pasta_destino)
        mover_substituindo(caminho_temp, caminho_final)

        print(f"Salvo em: {caminho_final}")
        return "baixou_com_ne"

    else:
        pasta_destino = PASTA_SEM_NE
        caminho_final = pasta_destino / nome_final

        if ja_estava_sem_ne:
            print(
                "Arquivo ja existia em SEM_NOTA_DE_EMPENHO e continua sem NE. "
                "Nao vou substituir o arquivo antigo."
            )
            descartar_temporario(caminho_temp)
            return "ja_baixado_sem_ne"

        print("ATENÇÃO: Processo sem Nota de Empenho identificada.")
        print("O processo será separado e não ficará na pasta Downloads.")

        remover_arquivo_da_pasta_errada(nome_final, pasta_destino)
        mover_substituindo(caminho_temp, caminho_final)

        print(f"Movido para análise manual: {caminho_final}")
        return "sem_ne"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False
        )

        context = browser.new_context(
            accept_downloads=True
        )

        page = context.new_page()
        page.goto(URL_LOGIN)

        input("Faça login no SPED, vá para Processos Encaminhados e aperte ENTER...")

        page.goto(URL_PROCESSOS)
        page.wait_for_load_state("networkidle")
        esperar_tabela(page)

        pagina_atual = 1
        total_com_ne = 0
        total_sem_ne = 0
        total_ignorados_ano = 0
        total_ja_baixados = 0
        total_pulados = 0
        total_processados = 0
        total_erros = 0

        while True:
            print(f"\n===== PÁGINA {pagina_atual} =====")

            esperar_tabela(page)
            total_linhas = page.locator("table tbody tr").count()

            for indice in range(total_linhas):
                print(f"\nPágina {pagina_atual} - Processo {indice + 1}")

                try:
                    linha = page.locator("table tbody tr").nth(indice)
                    pode_processar, motivo_ano = deve_processar_por_ano(
                        linha.inner_text()
                    )

                    if not pode_processar:
                        total_ignorados_ano += 1
                        print(f"Ignorado: processo nao e de {ANO_ALVO} ({motivo_ano}).")
                        continue

                    resultado = None
                    ultimo_erro = None

                    for tentativa in range(1, MAX_TENTATIVAS_PROCESSO + 1):
                        try:
                            resultado = baixar_processo(page, indice)
                            break
                        except Exception as erro:
                            ultimo_erro = erro
                            print(
                                f"Falha na tentativa {tentativa} de "
                                f"{MAX_TENTATIVAS_PROCESSO}."
                            )
                            print(f"Detalhe: {erro}")

                            if tentativa < MAX_TENTATIVAS_PROCESSO:
                                voltar_para_pagina(page, pagina_atual)
                                time.sleep(1)

                    if resultado is None:
                        total_erros += 1
                        total_pulados += 1
                        registrar_pulado(
                            page,
                            pagina_atual,
                            indice,
                            str(ultimo_erro) if ultimo_erro else "falha sem detalhe",
                        )
                        voltar_para_pagina(page, pagina_atual)
                        time.sleep(1)
                        continue

                    if resultado == "ignorado_ano":
                        total_ignorados_ano += 1
                        voltar_para_pagina(page, pagina_atual)
                        time.sleep(1)
                        continue

                    if resultado in ("ja_baixado", "ja_baixado_sem_ne"):
                        total_ja_baixados += 1
                        voltar_para_pagina(page, pagina_atual)
                        time.sleep(1)
                        continue

                    total_processados += 1

                    if resultado == "baixou_com_ne":
                        total_com_ne += 1
                    elif resultado == "sem_ne":
                        total_sem_ne += 1

                except Exception as erro:
                    total_erros += 1
                    print("ERRO ao processar este processo.")
                    print(f"Detalhe: {erro}")

                voltar_para_pagina(page, pagina_atual)
                time.sleep(1)

            if not existe_proxima_pagina(page):
                break

            page.locator(".ui-paginator-next").last.click()
            page.wait_for_timeout(2000)
            esperar_tabela(page)

            pagina_atual += 1

        print("\nFINALIZADO")
        print(f"Total processado: {total_processados}")
        print(f"Processos com Nota de Empenho: {total_com_ne}")
        print(f"Processos sem Nota de Empenho: {total_sem_ne}")
        print(f"Processos ignorados por ano diferente de {ANO_ALVO}: {total_ignorados_ano}")
        print(f"Processos ignorados por ja terem sido baixados: {total_ja_baixados}")
        print(f"Processos pulados apos falhas repetidas: {total_pulados}")
        print(f"Erros: {total_erros}")

        print(f"\nPasta de processos com NE: {PASTA_DOWNLOADS}")
        print(f"Pasta de processos sem NE: {PASTA_SEM_NE}")
        print(f"Pasta de processos pulados: {PASTA_PULADOS}")

        input("Pressione ENTER para fechar...")


if __name__ == "__main__":
    main()
