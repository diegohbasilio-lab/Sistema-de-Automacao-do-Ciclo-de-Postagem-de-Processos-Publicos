import os
import re
import shutil
import unicodedata
import hashlib
try:
    from pypdf import PdfReader
except Exception:
    from PyPDF2 import PdfReader

input_folder = "entrada/"
output_base = "processos_separados/"

categorias = [
    "processo_participante",
    "processo_gerenciador",
    "processo_adesao",
    "processo_dispensa",
    "processo_inexigibilidade",
    "processo_sem_nota_empenho",
    "fora_2026_ignorados",
    "nao_categorizado",
    "duplicados_ignorados"
]

for cat in categorias:
    os.makedirs(os.path.join(output_base, cat), exist_ok=True)


def normalizar(texto):
    if not texto:
        return ""

    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = texto.replace("º", "o").replace("ª", "a")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def calcular_hash_arquivo(caminho_arquivo):
    """
    Calcula o hash SHA-256 do arquivo.
    Se dois PDFs forem exatamente iguais, terão o mesmo hash.
    """
    sha256 = hashlib.sha256()

    with open(caminho_arquivo, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha256.update(bloco)

    return sha256.hexdigest()


def construir_indice_hashes_processados(output_base):
    """
    Varre todas as pastas de saída e monta um índice dos PDFs já separados.
    Assim, se o mesmo PDF aparecer novamente na entrada, ele será ignorado.
    """
    hashes = {}

    if not os.path.exists(output_base):
        return hashes

    for raiz, pastas, arquivos in os.walk(output_base):
        for arquivo in arquivos:
            if not arquivo.lower().endswith(".pdf"):
                continue

            caminho = os.path.join(raiz, arquivo)

            try:
                if not os.path.exists(caminho):
                    continue

                hash_pdf = calcular_hash_arquivo(caminho)

                # Evita usar a própria pasta de duplicados como referência principal
                if "duplicados_ignorados" not in caminho:
                    hashes[hash_pdf] = caminho

            except Exception as e:
                print(f"Não foi possível calcular hash de {caminho}: {e}")

    return hashes


def extrair_texto_pdf(pdf_path):
    textos_paginas = []
    texto_total = ""

    try:
        reader = PdfReader(pdf_path)

        for page in reader.pages:
            try:
                texto = page.extract_text() or ""
            except Exception:
                texto = ""

            texto = normalizar(texto)
            textos_paginas.append(texto)
            texto_total += " " + texto

    except Exception as e:
        print(f"Erro ao ler PDF {pdf_path}: {e}")

    return normalizar(texto_total), textos_paginas


def extrair_nup(texto_total):
    match = re.search(r"\b\d{5}\.\d{6}/\d{4}-\d{2}\b", texto_total)
    if match:
        return match.group(0)
    return None


def limpar_assunto(assunto):
    assunto = normalizar(assunto)

    assunto = re.sub(r"\b(rachurado|pdf|processo|administrativo|nup)\b", " ", assunto)
    assunto = re.sub(r"\b\d{5}\.\d{6}/\d{4}-\d{2}\b", " ", assunto)
    assunto = re.sub(r"\b20\d{2}ne\d+\b", " ", assunto)
    assunto = re.sub(r"\b\d+\s*/\s*20\d{2}\b", " ", assunto)
    assunto = re.sub(r"\s+", " ", assunto).strip(" .;:-_")

    paradas = [
        " despacho ",
        " termo ",
        " justificativa ",
        " estudo tecnico ",
        " nota de empenho ",
        " declaracao ",
        " autorizacao ",
        " mapa ",
        " sicaf ",
        " folha ",
        " fl ",
    ]

    assunto_com_espaco = f" {assunto} "
    cortes = [assunto_com_espaco.find(parada) for parada in paradas if assunto_com_espaco.find(parada) > 12]
    if cortes:
        assunto = assunto_com_espaco[:min(cortes)].strip()

    assunto = re.sub(r"\s+", " ", assunto).strip(" .;:-_")

    if len(assunto) < 8:
        return None

    if len(assunto) > 95:
        assunto = assunto[:95].rsplit(" ", 1)[0].strip()

    return assunto


def assunto_do_nome_arquivo(pdf_file):
    stem = os.path.splitext(pdf_file)[0]
    partes = [p.strip() for p in re.split(r"\s+-\s+| – | — ", stem) if p.strip()]

    candidatos = []
    if len(partes) >= 2:
        candidatos.append(partes[-1])
        candidatos.append(" ".join(partes[1:]))

    candidatos.append(stem)

    termos_genericos = [
        "apro",
        "aprov",
        "almox",
        "fisc adm",
        "enc mat",
        "sec",
        "s1",
        "1 secao",
        "4 cia com l mth",
    ]

    for candidato in candidatos:
        limpo = limpar_assunto(candidato)
        if not limpo:
            continue

        muito_generico = normalizar(limpo) in termos_genericos
        tem_assunto = re.search(
            r"\b(aquisicao|contratacao|servico|fornecimento|manutencao|material|genero|generos|energia|agua|esgoto|lavanderia|limpeza|publicidade|telefonia|correios|dosimetria)\b",
            limpo,
        )

        if tem_assunto and not muito_generico:
            return limpo, "assunto identificado pelo nome do arquivo"

    return None, None


def extrair_assunto_texto(textos_paginas):
    base = normalizar(" ".join(textos_paginas[:8]))

    padroes = [
        r"\bobjeto\s*[:\-]?\s*(.{10,160})",
        r"\bassunto\s*[:\-]?\s*(.{10,160})",
        r"\brequisicao\s+de\s+(.{10,150})",
        r"\bsolicitacao\s+de\s+(.{10,150})",
        r"\baquisicao\s+de\s+(.{10,150})",
        r"\bcontratacao\s+de\s+(.{10,150})",
        r"\bservico\s+de\s+(.{10,150})",
        r"\bfornecimento\s+de\s+(.{10,150})",
        r"\bmaterial\s+de\s+(.{10,150})",
    ]

    prefixos = {
        r"\brequisicao\s+de\s+": "requisicao de ",
        r"\bsolicitacao\s+de\s+": "solicitacao de ",
        r"\baquisicao\s+de\s+": "aquisicao de ",
        r"\bcontratacao\s+de\s+": "contratacao de ",
        r"\bservico\s+de\s+": "servico de ",
        r"\bfornecimento\s+de\s+": "fornecimento de ",
        r"\bmaterial\s+de\s+": "material de ",
    }

    for padrao in padroes:
        achou = re.search(padrao, base)
        if not achou:
            continue

        trecho = achou.group(1)
        for padrao_prefixo, prefixo in prefixos.items():
            if re.search(padrao_prefixo, padrao):
                trecho = prefixo + trecho
                break

        assunto = limpar_assunto(trecho)
        if assunto:
            return assunto, f"assunto identificado no texto: {padrao}"

    termos_diretos = [
        "energia eletrica",
        "fornecimento de agua e esgoto",
        "servico de lavanderia",
        "publicidade legal",
        "material de limpeza",
        "genero alimenticio",
        "generos alimenticios",
        "material medico e odontologico",
        "telefonia movel",
        "servicos postais",
        "dosimetria",
    ]

    for termo in termos_diretos:
        if termo in base:
            return termo, "assunto identificado por termo direto no texto"

    return None, None


def identificar_assunto_processo(pdf_file, textos_paginas):
    assunto, motivo = assunto_do_nome_arquivo(pdf_file)
    if assunto:
        return assunto, motivo

    assunto, motivo = extrair_assunto_texto(textos_paginas)
    if assunto:
        return assunto, motivo

    return None, "assunto não identificado"


def formatar_assunto_para_nome(assunto):
    if not assunto:
        return None

    assunto = re.sub(r'[<>:"/\\|?*]', " ", assunto)
    assunto = re.sub(r"\s+", " ", assunto).strip(" .-_")

    if not assunto:
        return None

    palavras_minusculas = {"de", "da", "do", "das", "dos", "e", "para", "por", "com", "em"}
    palavras = []
    for palavra in assunto.split():
        if palavra in palavras_minusculas:
            palavras.append(palavra)
        else:
            palavras.append(palavra[:1].upper() + palavra[1:])

    return " ".join(palavras)


def abreviar_assunto_nome(assunto):
    if not assunto:
        return None

    abreviacoes = [
        (r"\baquisição futura e eventual\b", "Aqs Fut/Event"),
        (r"\baquisicao futura e eventual\b", "Aqs Fut/Event"),
        (r"\bfutura e eventual aquisição\b", "Fut/Event Aqs"),
        (r"\bfutura e eventual aquisicao\b", "Fut/Event Aqs"),
        (r"\brequisição\b", "Req"),
        (r"\brequisicao\b", "Req"),
        (r"\baquisição\b", "Aqs"),
        (r"\baquisicao\b", "Aqs"),
        (r"\bcontratação\b", "Contr"),
        (r"\bcontratacao\b", "Contr"),
        (r"\bsolicitação\b", "Solic"),
        (r"\bsolicitacao\b", "Solic"),
        (r"\bserviços\b", "Sv"),
        (r"\bservicos\b", "Sv"),
        (r"\bserviço\b", "Sv"),
        (r"\bservico\b", "Sv"),
        (r"\bfornecimento\b", "Forn"),
        (r"\bmaterial\b", "Mat"),
        (r"\bmateriais\b", "Mat"),
        (r"\bprocesso\b", "Proc"),
        (r"\blicitatório\b", "Lic"),
        (r"\blicitatorio\b", "Lic"),
        (r"\bempresa\b", "Emp"),
        (r"\brealização\b", "Realiz"),
        (r"\brealizacao\b", "Realiz"),
        (r"\bmanutenção\b", "Mnt"),
        (r"\bmanutencao\b", "Mnt"),
        (r"\bcomunicação\b", "Com"),
        (r"\bcomunicacao\b", "Com"),
        (r"\btelecomunicações\b", "Telecom"),
        (r"\btelecomunicacoes\b", "Telecom"),
        (r"\binformática\b", "Info"),
        (r"\binformatica\b", "Info"),
        (r"\btecnologia\b", "Tec"),
        (r"\bsegurança\b", "Seg"),
        (r"\bseguranca\b", "Seg"),
        (r"\belétrica\b", "Elet"),
        (r"\beletrica\b", "Elet"),
        (r"\balimentício\b", "Alim"),
        (r"\balimenticio\b", "Alim"),
        (r"\bgênero\b", "Gen"),
        (r"\bgenero\b", "Gen"),
        (r"\bgêneros\b", "Gen"),
        (r"\bgeneros\b", "Gen"),
        (r"\bodontológico\b", "Odont"),
        (r"\bodontologico\b", "Odont"),
        (r"\bmédico\b", "Med"),
        (r"\bmedico\b", "Med"),
        (r"\badministrativo\b", "Adm"),
        (r"\badministrativa\b", "Adm"),
        (r"\bfutura\b", "Fut"),
        (r"\beventual\b", "Event"),
        (r"\badequação\b", "Adeq"),
        (r"\badequacao\b", "Adeq"),
    ]

    resultado = assunto
    for padrao, abreviado in abreviacoes:
        resultado = re.sub(padrao, abreviado, resultado, flags=re.IGNORECASE)

    resultado = re.sub(r"\s+", " ", resultado).strip(" .-_")
    return resultado


def limpar_nome_arquivo(nome):
    nome_base, extensao = os.path.splitext(nome)
    nome_base = re.sub(r'[<>:"/\\|?*]', " ", nome_base)
    nome_base = re.sub(r"\s+", " ", nome_base).strip(" .-_")

    if not extensao:
        extensao = ".pdf"

    return f"{nome_base}{extensao}"


def limitar_nome_arquivo(nome, limite=145):
    nome = limpar_nome_arquivo(nome)
    nome_base, extensao = os.path.splitext(nome)

    if len(nome) <= limite:
        return nome

    limite_base = max(30, limite - len(extensao))
    partes = [p.strip() for p in re.split(r"\s+-\s+", nome_base) if p.strip()]

    if len(partes) >= 2:
        prefixo = partes[0][:45].strip()
        sufixo = partes[-1][:70].strip()
        novo_base = f"{prefixo} - {sufixo}".strip(" -")
    else:
        novo_base = nome_base[:limite_base].rsplit(" ", 1)[0].strip()

    if len(novo_base) > limite_base:
        novo_base = novo_base[:limite_base].rsplit(" ", 1)[0].strip()

    return f"{novo_base}{extensao}"


def nome_com_assunto(pdf_file, assunto):
    assunto_nome = formatar_assunto_para_nome(abreviar_assunto_nome(assunto))
    if not assunto_nome:
        return limitar_nome_arquivo(pdf_file)

    nome_base, extensao = os.path.splitext(pdf_file)

    if normalizar(assunto_nome) in normalizar(nome_base):
        return limitar_nome_arquivo(pdf_file)

    return limitar_nome_arquivo(f"{nome_base} - {assunto_nome}{extensao}")


def identificar_ano_processo(pdf_file, textos_paginas):
    """
    Identifica o ano do processo por sinais fortes, evitando confundir com ano de NE/SRP.
    Se não encontrar 2026 de forma confiável, o PDF será ignorado para não ir para postagem.
    """

    nome = normalizar(pdf_file)
    primeiras_paginas = normalizar(" ".join(textos_paginas[:10]))
    base = normalizar(f"{nome} {primeiras_paginas}")

    padroes_prioritarios = [
        (r"\bdiex\s*(?:n|nr|numero|no|nro)?\s*[:.\-]?\s*\d+\s*/\s*(20\d{2})\b", "ano encontrado em DIEx"),
        (r"\bdie\s*x\s*(?:n|nr|numero|no|nro)?\s*[:.\-]?\s*\d+\s*/\s*(20\d{2})\b", "ano encontrado em DIEx"),
        (r"\brequisicao\s*(?:n|nr|numero|no|nro)?\s*[:.\-]?\s*\d+\s*/\s*(20\d{2})\b", "ano encontrado em requisição"),
        (r"\bsolicitacao\s*(?:n|nr|numero|no|nro)?\s*[:.\-]?\s*\d+\s*/\s*(20\d{2})\b", "ano encontrado em solicitação"),
        (r"\bprocesso\s*(?:administrativo)?\s*(?:n|nr|numero|no|nro)?\s*[:.\-]?\s*[\d./-]+/(20\d{2})\b", "ano encontrado em processo"),
        (r"\bnup\s*(?:n|nr|numero|no|nro)?\s*[:.\-]?\s*\d{5}\.\d{6}/(20\d{2})-\d{2}\b", "ano encontrado em NUP"),
        (r"\b\d{5}\.\d{6}/(20\d{2})-\d{2}\b", "ano encontrado em NUP"),
        (r"\b(20\d{2})\s*-\s*\d+\b", "ano encontrado no nome/texto do processo"),
        (r"\b(20\d{2})\s*/\s*\d+\b", "ano encontrado no nome/texto do processo"),
    ]

    for padrao, motivo in padroes_prioritarios:
        achou = re.search(padrao, base)
        if achou:
            return achou.group(1), motivo

    # Último recurso: nomes como "... 2026-1 ..." indicam exercício/processo 2026.
    achou_nome = re.search(r"\b(2026)(?:[-_/]\d+)?\b", nome)
    if achou_nome:
        return "2026", "ano 2026 encontrado no nome do arquivo"

    anos_suspeitos = sorted(set(re.findall(r"\b20\d{2}\b", base)))
    anos_suspeitos = [ano for ano in anos_suspeitos if ano != "2026"]

    if anos_suspeitos:
        return anos_suspeitos[0], "ano diferente de 2026 encontrado no início do processo"

    return None, "ano do processo não identificado como 2026"


def eh_pagina_sicaf_ou_ocorrencia(texto):
    termos = [
        "sistema de cadastramento unificado de fornecedores",
        "sicaf",
        "relatorio de ocorrencias ativas",
        "ocorrencias ativas",
        "ocorrencias impeditivas",
        "consulta consolidada de pessoa juridica",
        "cadastro informativo de creditos nao quitados",
        "cadin",
        "licitantes inidoneos",
        "cadastro nacional de empresas inidoneas",
        "cadastro nacional de empresas punidas"
    ]

    return any(t in texto for t in termos)


def montar_textos_confiaveis(textos_paginas):
    """
    Monta dois blocos:
    1. texto_confiavel: início do processo, DIEx, termo, despachos e NE.
    2. texto_ne: apenas páginas que parecem Nota de Empenho real.

    Ignora SICAF/ocorrências para não contaminar classificação.
    """

    paginas_confiaveis = []
    paginas_ne = []

    for i, texto in enumerate(textos_paginas):
        if not texto:
            continue

        # Ignora SICAF e ocorrências, pois causam falso positivo
        if eh_pagina_sicaf_ou_ocorrencia(texto):
            continue

        # Primeiras páginas costumam ter capa, peças processuais, termo, DIEx e despachos
        if i <= 8:
            paginas_confiaveis.append(texto)

        # Página típica de Nota de Empenho real
        tem_ne_real = (
            "nota de empenho" in texto
            and "impressao completa" in texto
            and (
                "ano tipo numero" in texto
                or "celula orcamentaria" in texto
                or "modalidade de licitacao" in texto
                or "sistema de origem" in texto
                or "favorecido" in texto
            )
        )

        if tem_ne_real:
            paginas_ne.append(texto)
            paginas_confiaveis.append(texto)

    texto_confiavel = normalizar(" ".join(paginas_confiaveis))
    texto_ne = normalizar(" ".join(paginas_ne))

    return texto_confiavel, texto_ne


def possui_nota_empenho(texto_total, textos_paginas):
    """
    Verifica se existe NE real do processo.
    Não considera 'Nota de Empenho' citada dentro de SICAF, multas ou ocorrências antigas.
    """

    texto_total = normalizar(texto_total)

    # Verifica na capa/lista de peças processuais
    # Exemplo: 14- 2026NE000014 - BRASIDAS LTDA...
    padrao_peca_ne = r"\b\d+\s*-\s*20\d{2}\s*ne\s*0*\d{1,6}\b"

    if re.search(padrao_peca_ne, texto_total):
        return True, "NE encontrada na lista de peças processuais"

    # Verifica páginas reais de Nota de Empenho, ignorando SICAF/ocorrências
    for texto in textos_paginas:
        if eh_pagina_sicaf_ou_ocorrencia(texto):
            continue

        tem_ne_real = (
            "nota de empenho" in texto
            and "impressao completa" in texto
            and (
                "ano tipo numero" in texto
                or "celula orcamentaria" in texto
                or "modalidade de licitacao" in texto
                or "sistema de origem" in texto
                or "favorecido" in texto
            )
        )

        if tem_ne_real:
            return True, "página real de Nota de Empenho encontrada"

    return False, "não encontrou Nota de Empenho real do processo"


def contem_regex(texto, padroes):
    for padrao in padroes:
        if re.search(padrao, texto):
            return True, padrao
    return False, None


def classificar_processo(pdf_file, texto_confiavel, texto_ne):
    nome = normalizar(pdf_file)

    # A decisão prioriza:
    # nome + páginas iniciais + Nota de Empenho
    base = normalizar(f"{nome} {texto_confiavel} {texto_ne}")

    scores = {
        "processo_participante": 0,
        "processo_gerenciador": 0,
        "processo_adesao": 0,
        "processo_dispensa": 0,
        "processo_inexigibilidade": 0
    }

    motivos = []

    # ---------------------------------------------------------
    # 1. INEXIGIBILIDADE REAL - energia elétrica
    # Cuidado: NÃO confundir com GERADOR DE ENERGIA.
    # ---------------------------------------------------------

    padroes_energia_eletrica_real = [
        r"energia\s+eletrica",
        r"fornecimento\s+de\s+energia\s+eletrica",
        r"servico\s+de\s+energia\s+eletrica",
        r"concessionaria\s+de\s+energia",
        r"distribuidora\s+de\s+energia",
        r"conta\s+de\s+energia",
        r"unidade\s+consumidora",
        r"\buc\s+\d{3,}",
        r"cemig",
        r"companhia\s+energetica"
    ]

    achou, padrao = contem_regex(base, padroes_energia_eletrica_real)

    if achou:
        scores["processo_inexigibilidade"] += 200
        motivos.append(f"inexigibilidade por energia elétrica: {padrao}")

    # Proteção: gerador não é energia elétrica/inexigibilidade
    padroes_gerador_nao_inex = [
        r"gerador\s+de\s+energia",
        r"gerador\s+energia",
        r"equipamentos\s+energeticos",
        r"maquinas\s+e\s+equipamentos\s+energeticos",
        r"aplicacao\s+fornecimento\s+de\s+energia"
    ]

    achou_gerador, padrao_gerador = contem_regex(base, padroes_gerador_nao_inex)

    if achou_gerador:
        scores["processo_inexigibilidade"] -= 150
        motivos.append(f"proteção: gerador não é energia elétrica/inexigibilidade: {padrao_gerador}")

    # ---------------------------------------------------------
    # 2. GERENCIADOR - Correios, telefonia móvel e dosimetria
    # ---------------------------------------------------------

    padroes_gerenciador_especial = [
        r"correios",
        r"empresa\s+brasileira\s+de\s+correios",
        r"\bebct\b",
        r"servicos\s+postais",
        r"postagem",
        r"telefonia\s+movel",
        r"telefone\s+movel",
        r"servico\s+movel\s+pessoal",
        r"\bsmp\b",
        r"claro\s+s\.?a\.?",
        r"tim\s+s\.?a\.?",
        r"vivo\s+s\.?a\.?",
        r"telefonica\s+brasil",
        r"dosimetria",
        r"dosimetro",
        r"dosimetros",
        r"monitoramento\s+individual",
        r"radiacao\s+ionizante"
    ]

    achou, padrao = contem_regex(base, padroes_gerenciador_especial)

    if achou:
        scores["processo_gerenciador"] += 180
        scores["processo_adesao"] -= 100
        motivos.append(f"gerenciador por serviço especial: {padrao}")

    # ---------------------------------------------------------
    # 3. ADESÃO / CARONA
    # Só deve vencer quando houver N PART, não participante, carona ou adesão clara.
    # ---------------------------------------------------------

    padroes_adesao_fortes = [
        r"\(n\s*part\)",
        r"\(n\.\s*part\)",
        r"\(nao\s*part\)",
        r"\(nao\s*participante\)",
        r"nao\s+participante",
        r"orgao\s+nao\s+participante",
        r"processo\s+de\s+carona",
        r"solicitacao\s+de\s+carona",
        r"solicitar\s+carona",
        r"pedido\s+de\s+carona",
        r"adesao\s+a\s+ata",
        r"adesao\s+a\s+ata\s+de\s+registro\s+de\s+precos",
        r"justificativa\s+da\s+vantagem\s+da\s+adesao",
        r"estudo\s+de\s+eficiencia.*orgao\s+nao\s+participante"
    ]

    achou, padrao = contem_regex(base, padroes_adesao_fortes)

    if achou:
        scores["processo_adesao"] += 150
        scores["processo_participante"] -= 80
        motivos.append(f"adesão/carona forte: {padrao}")

    # ---------------------------------------------------------
    # 4. PARTICIPANTE
    # PART, PARTICIPANTE e UASG participante.
    # ---------------------------------------------------------

    padroes_participante_fortes = [
        r"\(part\)",
        r"\(part\.\)",
        r"\(participante\)",
        r"uasg:\s*\d{6}\s*\(participante\)",
        r"uasg\s+\d{6}\s*\(participante\)",
        r"ug\s+\d{6}.*\(part\)",
        r"ug\s+\d{6}.*\(participante\)"
    ]

    achou, padrao = contem_regex(base, padroes_participante_fortes)

    if achou:
        # Só reforça participante se não for N PART
        if not re.search(r"\(n\s*part\)|\(n\.\s*part\)|nao\s+participante", base):
            scores["processo_participante"] += 150
            scores["processo_adesao"] -= 40
            motivos.append(f"participante forte: {padrao}")

    # Regra adicional: tem SRP/UG/Pregão e não tem N PART/carona/adesão
    if (
        re.search(r"\bsrp\s+\d{5}/\d{4}", base)
        and re.search(r"\bug[:\s]+\d{6}", base)
        and "pregao" in base
        and not re.search(r"\(n\s*part\)|\(n\.\s*part\)|nao\s+participante|carona|adesao", base)
    ):
        scores["processo_participante"] += 70
        motivos.append("participante por SRP/UG/Pregão sem sinais de N PART/carona/adesão")

    # ---------------------------------------------------------
    # 5. DISPENSA
    # ---------------------------------------------------------

    padroes_dispensa = [
        r"dispensa\s+de\s+licitacao",
        r"dispensa\s+eletronica",
        r"aviso\s+de\s+dispensa",
        r"art\.?\s*75\b",
        r"artigo\s+75\b"
    ]

    achou, padrao = contem_regex(base, padroes_dispensa)

    if achou:
        scores["processo_dispensa"] += 130
        motivos.append(f"dispensa: {padrao}")

    # ---------------------------------------------------------
    # 6. INEXIGIBILIDADE GERAL
    # ---------------------------------------------------------

    padroes_inex = [
        r"inexigibilidade",
        r"inexigivel",
        r"fornecedor\s+exclusivo",
        r"fornecedor\s+unico",
        r"exclusividade",
        r"atestado\s+de\s+exclusividade",
        r"notoria\s+especializacao",
        r"art\.?\s*74\b",
        r"artigo\s+74\b"
    ]

    achou, padrao = contem_regex(base, padroes_inex)

    if achou:
        scores["processo_inexigibilidade"] += 130
        motivos.append(f"inexigibilidade geral: {padrao}")

    # ---------------------------------------------------------
    # 7. GERENCIADOR GERAL
    # ---------------------------------------------------------

    padroes_gerenciador = [
        r"orgao\s+gerenciador",
        r"uasg\s+gerenciadora",
        r"unidade\s+gerenciadora",
        r"ug\s+gerenciadora",
        r"gerenciador\s+da\s+ata"
    ]

    achou, padrao = contem_regex(base, padroes_gerenciador)

    if achou:
        scores["processo_gerenciador"] += 100
        motivos.append(f"gerenciador geral: {padrao}")

    # ---------------------------------------------------------
    # Ajustes de proteção
    # ---------------------------------------------------------

    # Se for Correios/telefonia/dosimetria, não deixar adesão vencer
    if scores["processo_gerenciador"] >= 150:
        scores["processo_adesao"] -= 120
        scores["processo_participante"] -= 30

    # Se for energia elétrica real, deixa inexigibilidade vencer
    if scores["processo_inexigibilidade"] >= 200:
        scores["processo_adesao"] -= 120
        scores["processo_participante"] -= 80
        scores["processo_gerenciador"] -= 60

    # Se for gerador com PART, participante deve vencer
    if achou_gerador and re.search(r"\(part\)|\(part\.\)|\(participante\)", base):
        scores["processo_participante"] += 120
        scores["processo_inexigibilidade"] -= 100
        motivos.append("correção final: gerador com PART deve ser participante")

    melhor_categoria = max(scores, key=scores.get)
    melhor_score = scores[melhor_categoria]

    if melhor_score < 40:
        return "nao_categorizado", melhor_score, scores, motivos

    return melhor_categoria, melhor_score, scores, motivos


def classificar_pdf(pdf_path, pdf_file):
    texto_total, textos_paginas = extrair_texto_pdf(pdf_path)

    if not texto_total:
        return "nao_categorizado", 0, {}, ["sem texto extraível"], None

    ano_processo, motivo_ano = identificar_ano_processo(pdf_file, textos_paginas)
    assunto, motivo_assunto = identificar_assunto_processo(pdf_file, textos_paginas)

    if ano_processo != "2026":
        ano_info = ano_processo if ano_processo else "não identificado"
        return "fora_2026_ignorados", 999, {}, [
            f"processo ignorado: ano {ano_info}",
            motivo_ano,
            motivo_assunto,
        ], assunto

    # 1. Confere NE real antes de qualquer categoria
    tem_ne, motivo_ne = possui_nota_empenho(texto_total, textos_paginas)

    if not tem_ne:
        return "processo_sem_nota_empenho", 999, {}, [motivo_ne, motivo_assunto], assunto

    # 2. Monta textos confiáveis, ignorando SICAF/ocorrências
    texto_confiavel, texto_ne = montar_textos_confiaveis(textos_paginas)

    # 3. Classifica pelo conjunto do processo
    categoria, score, scores, motivos = classificar_processo(
        pdf_file,
        texto_confiavel,
        texto_ne
    )

    motivos.append(motivo_assunto)

    return categoria, score, scores, motivos, assunto


def gerar_caminho_sem_sobrescrever(destino_folder, pdf_file):
    pdf_file = limitar_nome_arquivo(pdf_file)
    destino_path = os.path.join(destino_folder, pdf_file)

    if not os.path.exists(destino_path):
        return destino_path

    nome_base, extensao = os.path.splitext(pdf_file)
    contador = 1

    while True:
        novo_nome = f"{nome_base}_{contador}{extensao}"
        destino_path = os.path.join(destino_folder, novo_nome)

        if not os.path.exists(destino_path):
            return destino_path

        contador += 1


# ---------------------------------------------------------
# PROCESSAMENTO FINAL
# ---------------------------------------------------------

# Cria índice de PDFs já separados anteriormente
hashes_processados = construir_indice_hashes_processados(output_base)

pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".pdf")]

for pdf_file in pdf_files:
    pdf_path = os.path.join(input_folder, pdf_file)

    try:
        hash_atual = calcular_hash_arquivo(pdf_path)
    except Exception as e:
        print(f"Erro ao calcular hash de {pdf_file}: {e}")
        continue

    # Se o PDF já foi separado anteriormente, não classifica de novo
    if hash_atual in hashes_processados:
        destino_folder = os.path.join(output_base, "duplicados_ignorados")
        os.makedirs(destino_folder, exist_ok=True)

        destino_path = gerar_caminho_sem_sobrescrever(destino_folder, pdf_file)

        try:
            shutil.move(pdf_path, destino_path)

            print("=" * 100)
            print(f"Arquivo duplicado ignorado: {pdf_file}")
            print(f"Já existe separado em: {hashes_processados[hash_atual]}")
            print(f"Duplicado movido para: {destino_path}")

        except Exception as e:
            print(f"Erro ao mover duplicado {pdf_file}: {e}")

        continue

    # Se não for duplicado, classifica normalmente
    categoria, score, scores, motivos, assunto = classificar_pdf(pdf_path, pdf_file)

    destino_folder = os.path.join(output_base, categoria)
    os.makedirs(destino_folder, exist_ok=True)

    pdf_file_destino = nome_com_assunto(pdf_file, assunto)
    destino_path = gerar_caminho_sem_sobrescrever(destino_folder, pdf_file_destino)

    try:
        shutil.move(pdf_path, destino_path)

        # Adiciona o hash ao índice para evitar duplicado dentro da mesma rodada
        hashes_processados[hash_atual] = destino_path

        print("=" * 100)
        print(f"Arquivo: {pdf_file}")
        if pdf_file_destino != pdf_file:
            print(f"Arquivo renomeado com assunto: {pdf_file_destino}")
        if assunto:
            print(f"Assunto identificado: {formatar_assunto_para_nome(assunto)}")
        print(f"Categoria final: {categoria}")
        print(f"Score final: {score}")
        print(f"Scores: {scores}")
        print("Motivos:")
        for m in motivos:
            print(f" - {m}")
        print(f"Destino: {destino_path}")

        print("Arquivo movido com sucesso.")

    except Exception as e:
        print(f"Erro ao processar {pdf_file}: {e}")

print("Processo concluído.")
