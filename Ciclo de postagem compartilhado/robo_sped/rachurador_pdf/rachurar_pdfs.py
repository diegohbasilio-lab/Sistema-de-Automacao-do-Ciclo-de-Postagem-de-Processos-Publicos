import fitz
import re
from pathlib import Path

PASTA_ENTRADA = Path("entrada")
PASTA_SAIDA = Path("saida")

APAGAR_IMAGENS_GRANDES = True
AREA_MINIMA_IMAGEM = 0.18

PADROES_CPF = [
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",
    r"\*\*\*\.?\d{3}\.?\d{3}-?\*\*",
    r"\b\d{3}\.XXX\.XXX-\d{2}\b",
]

POSTOS = [
    "Sd", "Cb", "Sgt", "ST", "Sub Ten",
    "3º Sgt", "2º Sgt", "1º Sgt",
    "2º Ten", "1º Ten",
    "Cap", "Maj", "TC", "Cel"
]

PALAVRAS_PROIBIDAS_NOME = [
    "MINISTÉRIO", "EXÉRCITO", "COMPANHIA", "COMUNICAÇÕES", "MONTANHA",
    "PRESIDÊNCIA", "REPÚBLICA", "TERMO", "ABERTURA", "PROCESSO",
    "DOCUMENTO", "ASSUNTO", "ANEXOS", "DESPACHO", "CÓDIGO",
    "VERIFICAÇÃO", "FISCAL", "ADMINISTRATIVO", "APROVISIONAMENTO",
    "FORNECEDOR", "COPASA", "SANEAMENTO", "MINAS", "GERAIS",
    "BRASÍLIA", "BELO", "HORIZONTE", "LEI", "DECRETO", "CADASTRO",
    "CONSULTA", "RESULTADO", "DIRETORIA", "GESTAO", "GESTÃO",
    "ÁGUA", "ESGOTO", "SERVIÇO", "CONTRATAÇÃO", "PESSOA", "JURÍDICA"
]

CONTEXTOS_PROIBIDOS = [
    "ANEXOS", "OBSERVACAO", "OBSERVAÇÃO", "RAZÃO SOCIAL", "RAZAO SOCIAL",
    "CADASTRO", "CONSULTA", "RESULTADO", "RESULTADOS", "ÓRGÃO GESTOR",
    "ORGAO GESTOR", "DIRETORIA", "GESTAO", "GESTÃO", "ATD COMPLEMENTO",
    "FORNECIMENTO", "OBJETO", "PORTAL", "PESSOA JURÍDICA",
    "PESSOA JURIDICA", "SANEAMENTO", "COMPANHIA DE SANEAMENTO",
    "TESOURO NACIONAL", "PRESIDÊNCIA DA REPÚBLICA", "TERMO DE ABERTURA",
    "TERMO DE JUNTADA"
]

CONTEXTOS_DE_NOME = [
    "DOCUMENTO ASSINADO ELETRONICAMENTE",
    "LANCADO POR",
    "LANÇADO POR",
    "USUARIO:",
    "USUÁRIO:",
    "NOME:",
    "CPF NOME",
    "CARGO/FUNÇÃO",
    "CARGO/FUNCAO",
    "RESPONSÁVEL PELA CONTRATAÇÃO",
    "RESPONSAVEL PELA CONTRATACAO",
    "AUTORIDADE COMPETENTE",
    "ORDENADOR DE DESPESA",
    "RESPONSÁVEL PELA NOTA DE EMPENHO",
    "RESPONSAVEL PELA NOTA DE EMPENHO",
]

def remover_postos(texto):
    texto_limpo = texto
    for posto in sorted(POSTOS, key=len, reverse=True):
        texto_limpo = re.sub(rf"\b{re.escape(posto)}\b", "", texto_limpo, flags=re.IGNORECASE)
    return texto_limpo.strip(" -")

def parece_nome_pessoal(nome):
    nome = remover_postos(nome.strip())
    nome = re.sub(r"\s+", " ", nome)

    if len(nome) < 10 or len(nome) > 50:
        return False

    nome_upper = nome.upper()

    if any(p in nome_upper for p in PALAVRAS_PROIBIDAS_NOME):
        return False

    palavras = nome.split()

    if len(palavras) < 2 or len(palavras) > 6:
        return False

    conectores = {"de", "da", "do", "das", "dos", "e"}
    validas = [p for p in palavras if p.lower() not in conectores]

    if len(validas) < 2:
        return False

    return all(p.isupper() or p[0].isupper() for p in validas)

def encontrar_nomes(linha):
    padrao = (
        r"\b(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}|[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)"
        r"(?:\s+(?:de|da|do|das|dos|e|"
        r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}|[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)){1,5}\b"
    )

    candidatos = re.findall(padrao, linha)
    return [n for n in candidatos if parece_nome_pessoal(n)]

def tarjar_texto(pagina, texto):
    for area in pagina.search_for(texto):
        pagina.add_redact_annot(area, fill=(0, 0, 0))

def apagar_imagens_grandes(pagina):
    area_pagina = pagina.rect.width * pagina.rect.height

    for img in pagina.get_images(full=True):
        xref = img[0]

        for rect in pagina.get_image_rects(xref):
            area_img = rect.width * rect.height

            if area_img / area_pagina >= AREA_MINIMA_IMAGEM:
                pagina.add_redact_annot(rect, fill=(0, 0, 0))

def deve_procurar_nome(linha):
    linha_upper = linha.upper()

    if any(c in linha_upper for c in CONTEXTOS_DE_NOME):
        return True

    if re.search(r"\s-\s(?:ST|Sd|Cb|Sgt|1º Sgt|2º Sgt|3º Sgt|1º Ten|2º Ten|Cap|Maj|TC|Cel)\b", linha):
        return True

    if any(c in linha_upper for c in CONTEXTOS_PROIBIDOS):
        return False

    return False

def pagina_tem_tabela_responsaveis(texto):
    texto_upper = texto.upper()

    return (
        "RESPONSÁVEIS" in texto_upper
        or "RESPONSAVEIS" in texto_upper
        or ("CPF" in texto_upper and "NOME" in texto_upper and "CARGO/FUNÇÃO" in texto_upper)
        or ("CPF" in texto_upper and "NOME" in texto_upper and "CARGO/FUNCAO" in texto_upper)
    )

def processar_pdf(arquivo):
    saida = PASTA_SAIDA / f"{arquivo.stem} RACHURADO.pdf"
    doc = fitz.open(arquivo)

    for pagina in doc:
        texto = pagina.get_text()
        linhas = texto.splitlines()

        # Tarja CPF. Não tarja CNPJ nem conta bancária.
        for padrao in PADROES_CPF:
            for encontrado in re.findall(padrao, texto):
                tarjar_texto(pagina, encontrado)

        # Caso especial: tabela de responsáveis
        if pagina_tem_tabela_responsaveis(texto):
            for linha_tabela in linhas:
                linha_tabela = linha_tabela.strip()

                if not linha_tabela:
                    continue

                for nome in encontrar_nomes(linha_tabela):
                    tarjar_texto(pagina, nome)

        for i, linha in enumerate(linhas):
            linha = linha.strip()

            if not linha:
                continue

            if deve_procurar_nome(linha):
                for nome in encontrar_nomes(linha):
                    tarjar_texto(pagina, nome)

            if linha.upper() in [
                "ORDENADOR DE DESPESA",
                "RESPONSÁVEL PELA NOTA DE EMPENHO",
                "RESPONSAVEL PELA NOTA DE EMPENHO",
                "CPF NOME CARGO/FUNÇÃO",
                "CPF NOME CARGO/FUNCAO",
            ]:
                for prox in linhas[i + 1:i + 6]:
                    for nome in encontrar_nomes(prox.strip()):
                        tarjar_texto(pagina, nome)

        if APAGAR_IMAGENS_GRANDES:
            apagar_imagens_grandes(pagina)

        pagina.apply_redactions()

    doc.save(saida)
    doc.close()
    print(f"OK: {saida}")

def main():
    PASTA_ENTRADA.mkdir(exist_ok=True)
    PASTA_SAIDA.mkdir(exist_ok=True)

    arquivos = list(PASTA_ENTRADA.glob("*.pdf"))

    if not arquivos:
        print("Nenhum PDF encontrado na pasta entrada.")
        return

    for arquivo in arquivos:
        processar_pdf(arquivo)

if __name__ == "__main__":
    main()