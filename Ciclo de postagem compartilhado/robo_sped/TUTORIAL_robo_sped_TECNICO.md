# Tutorial tecnico do robo_sped

Este documento explica o funcionamento do arquivo:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\robo_sped.py`

A explicacao segue a ordem do codigo e mostra o papel de cada linha ou bloco.

## Visao geral

O script automatiza o SPED com Playwright.

Fluxo principal:

1. Abre o Chrome.
2. Espera o usuario fazer login e ir para `Processos Encaminhados`.
3. Percorre a tabela de processos.
4. Filtra processos/documentos que nao sejam de `2026`.
5. Abre cada processo valido.
6. Identifica o primeiro PDF de `Documentos assinados`.
7. Verifica se esse PDF ja foi baixado antes.
8. Se ja esta em `Downloads`, ignora sem baixar.
9. Se ja esta em `SEM_NOTA_DE_EMPENHO`, baixa temporariamente apenas para conferir se agora existe NE.
10. Le o texto do PDF com `PyPDF2` ou, se ele nao estiver instalado, com `pypdf`.
11. Procura padroes de Nota de Empenho.
12. Move o PDF para `Downloads` ou `SEM_NOTA_DE_EMPENHO`, respeitando a regra de nao substituir arquivos antigos sem necessidade.
13. Se falhar repetidas vezes, cria registro em `PULADOS`.

## Dependencias

O codigo usa:

- `playwright`: controla o navegador.
- `pathlib.Path`: monta caminhos de arquivo.
- `re`: usa expressoes regulares para limpar texto, achar anos e achar NE.
- `time`: pausa entre acoes.
- `shutil`: move arquivos.
- `PyPDF2.PdfReader` ou `pypdf.PdfReader`: extrai texto dos PDFs baixados. O codigo tenta primeiro `PyPDF2`; se nao existir, usa `pypdf`.

## Explicacao por linhas

| Linha(s) | Codigo / ideia | O que faz |
|---|---|---|
| 1 | `from playwright.sync_api import sync_playwright` | Importa a versao sincronizada do Playwright para controlar o Chrome. |
| 2 | `from pathlib import Path` | Importa a classe usada para trabalhar com caminhos de arquivos e pastas. |
| 3 | `import re` | Importa expressoes regulares. O robo usa isso para limpar nomes, achar anos e achar NE. |
| 4 | `import time` | Importa pausas simples, como `time.sleep(1)`. |
| 5 | `import shutil` | Importa funcoes de movimentacao de arquivos. |
| 6 | `try:` | Inicia a tentativa de usar a biblioteca principal de leitura de PDF. |
| 7 | `from PyPDF2 import PdfReader` | Tenta importar o leitor de PDF pelo pacote `PyPDF2`. |
| 8 | `except ModuleNotFoundError:` | Se o `PyPDF2` nao estiver instalado, entra no plano alternativo. |
| 9 | `from pypdf import PdfReader` | Usa o pacote `pypdf` como alternativa para ler PDFs. |
| 11-12 | Comentarios com usuario/senha | Comentarios. Nao sao executados pelo Python. |
| 14 | `URL_LOGIN` | Guarda o endereco inicial do SPED. |
| 15 | `URL_PROCESSOS` | Guarda o endereco da tela de processos encaminhados. |
| 16 | `ANO_ALVO = "2026"` | Define o ano que o robo deve aceitar. |
| 17 | `MAX_TENTATIVAS_PROCESSO = 3` | Define quantas vezes um processo pode falhar antes de virar `PULADO`. |
| 19 | `PASTA_BASE` | Define a pasta base usada para salvar resultados. Hoje aponta para `C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped`. |
| 20 | `PASTA_DOWNLOADS` | Pasta dos PDFs com Nota de Empenho encontrada. |
| 21 | `PASTA_SEM_NE` | Pasta dos PDFs sem Nota de Empenho encontrada. |
| 22 | `PASTA_PULADOS` | Pasta onde ficam registros de processos pulados. |
| 23 | `PASTA_TEMP` | Pasta temporaria usada antes de decidir o destino final do PDF. |
| 25-28 | `mkdir(...)` | Garante que as pastas existem. Se nao existirem, cria automaticamente. |

## Funcao `limpar_nome`

Linhas 28-32.

```python
def limpar_nome(nome):
```

Cria uma funcao para deixar nomes de arquivo seguros para o Windows.

| Linha(s) | O que faz |
|---|---|
| 29 | Troca `/` por `-`, porque barra nao pode ser usada em nome de arquivo. |
| 30 | Remove caracteres proibidos no Windows: `\ : * ? " < > |`. |
| 31 | Troca varios espacos por um espaco so e remove espacos no inicio/fim. |
| 32 | Limita o nome a 180 caracteres para evitar caminho grande demais. |

## Funcao `normalizar_texto`

Linhas 35-51.

Serve para padronizar o texto antes de procurar NE.

| Linha(s) | O que faz |
|---|---|
| 36 | Converte tudo para maiusculo. |
| 38-45 | Cria um dicionario de substituicoes para corrigir acentos quebrados. |
| 47-48 | Percorre as substituicoes e troca cada caractere problemático. |
| 50 | Troca quebras e espacos repetidos por um espaco simples. |
| 51 | Devolve o texto limpo. |

## Funcao `identificar_anos`

Linhas 54-55.

```python
return sorted(set(re.findall(r"\b20\d{2}\b", texto or "")))
```

Procura qualquer ano no formato `20xx`, por exemplo:

- `2024`
- `2025`
- `2026`

Usa `set` para remover repetidos e `sorted` para ordenar.

## Funcao `deve_processar_por_ano`

Linhas 58-72.

Decide se um processo/documento deve ser processado conforme o ano.

| Linha(s) | O que faz |
|---|---|
| 64 | Chama `identificar_anos` para achar anos no texto recebido. |
| 66-67 | Se nao achou ano, deixa seguir. A validacao pode acontecer depois. |
| 69-70 | Se achou `ANO_ALVO`, permite processar. |
| 72 | Se achou anos mas nenhum e `2026`, bloqueia o processo. |

## Funcao `extrair_texto_pdf`

Linhas 75-90.

Abre um PDF e tenta extrair todo o texto.

| Linha(s) | O que faz |
|---|---|
| 76 | Comeca com texto vazio. |
| 79 | Abre o PDF com `PdfReader`. |
| 81-83 | Percorre as paginas e junta o texto extraido. |
| 85-88 | Se der erro, mostra o erro e retorna texto vazio. |
| 90 | Retorna o texto completo. |

## Funcao `identificar_notas_empenho`

Linhas 93-159.

Procura possiveis Notas de Empenho no texto do PDF.

| Linha(s) | O que faz |
|---|---|
| 105 | Normaliza o texto para facilitar a busca. |
| 107 | Cria lista vazia para guardar NEs encontradas. |
| 109-121 | Define padroes fortes de NE. |
| 123-129 | Aplica cada padrao, limpa o resultado e evita duplicados. |
| 133-139 | Verifica se o texto menciona claramente Nota de Empenho. |
| 141-146 | Define padroes complementares, como `NE 000123`. |
| 148-157 | Procura esses padroes complementares e adiciona resultados validos. |
| 159 | Retorna a lista de NEs encontradas. |

### Padroes fortes usados

O robo procura modelos como:

- `1605232026NE000123`
- `167158 2026 NE 000251`
- `2026NE000123`
- `2026 NE 000123`

### Padroes complementares

So sao aceitos quando o documento menciona termos como:

- `NOTA DE EMPENHO`
- `EMPENHO DA DESPESA`
- `NATUREZA DE DESPESA`
- `EMISSAO` junto com `EMPENHO`

Isso evita aceitar qualquer `NE 000123` solto sem contexto.

## Funcao `possui_nota_empenho`

Linhas 162-174.

| Linha(s) | O que faz |
|---|---|
| 163 | Extrai texto do PDF. |
| 165-167 | Se nao houver texto, informa alerta e retorna `False`. |
| 169 | Chama `identificar_notas_empenho`. |
| 171-172 | Se encontrou NE, retorna `True` e a lista de NEs. |
| 174 | Se nao encontrou, retorna `False`. |

## Funcoes de arquivo

### `remover_se_existir`

Linhas 177-179.

Remove um arquivo se ele ja existir.

### `mover_substituindo`

Linhas 182-194.

Move um arquivo para o destino final.

| Linha(s) | O que faz |
|---|---|
| 188 | Cria a pasta de destino se precisar. |
| 190-192 | Se ja existir arquivo com mesmo nome, apaga o antigo. |
| 194 | Move o arquivo da origem para o destino. |

### `remover_arquivo_da_pasta_errada`

Linhas 197-214.

Garante que o mesmo PDF nao fique ao mesmo tempo em `Downloads` e `SEM_NOTA_DE_EMPENHO`.

| Linha(s) | O que faz |
|---|---|
| 204-207 | Lista as pastas que podem conter o arquivo. |
| 209-214 | Se o arquivo estiver em uma pasta errada, remove. |

### `descartar_temporario`

Remove um PDF que foi baixado em `TEMP`, mas nao deve substituir nenhum arquivo antigo.

Essa funcao e usada principalmente quando o processo ja existia em `SEM_NOTA_DE_EMPENHO` e, depois de uma nova conferencia, continua sem Nota de Empenho.

Assim o robo evita sobrescrever o arquivo antigo com uma copia igual ou equivalente.

## Funcao `registrar_pulado`

Linhas 217-255.

Cria um arquivo `.txt` na pasta `PULADOS` quando o processo falha repetidas vezes.

| Linha(s) | O que faz |
|---|---|
| 218 | Pega as linhas da tabela. |
| 219 | Comeca com texto vazio. |
| 221-224 | Tenta capturar o texto da linha do processo. Se falhar, continua. |
| 226 | Limpa o texto da linha para usar no nome do arquivo. |
| 228-231 | Monta o nome do arquivo `PULADO`. |
| 233 | Define o caminho do arquivo pulado. |
| 235-238 | Se ja existir arquivo com esse nome, cria outro com contador. |
| 240-252 | Escreve um `.txt` com motivo, pagina, tentativa e texto da linha. |
| 254 | Mostra no terminal onde o registro foi salvo. |
| 255 | Retorna o caminho do registro criado. |

## Funcoes de navegacao

### `esperar_tabela`

Linhas 258-259.

Espera aparecer pelo menos uma linha na tabela de processos.

### `voltar_para_pagina`

Linhas 262-270.

Volta para a tela de processos e retorna ate a pagina em que o robo estava.

| Linha(s) | O que faz |
|---|---|
| 263 | Abre a URL de processos encaminhados. |
| 264 | Espera a rede estabilizar. |
| 265 | Espera a tabela carregar. |
| 267-270 | Clica em proxima pagina ate chegar na pagina original. |

### `existe_proxima_pagina`

Linhas 273-276.

Verifica se o botao de proxima pagina esta habilitado.

Se a classe do botao nao tiver `ui-state-disabled`, existe proxima pagina.

## Funcao `baixar_processo`

Linhas 279-350.

Esta e a funcao que abre um processo e baixa o PDF.

| Linha(s) | O que faz |
|---|---|
| 280-281 | Localiza a linha desejada da tabela. |
| 283-284 | Clica na linha e espera meio segundo. |
| 286-287 | Clica no botao de visualizar e espera carregar. |
| 289 | Espera aparecer `Documentos assinados`. |
| 291-293 | Localiza a tabela de documentos assinados. |
| 295-296 | Pega a primeira linha da tabela de documentos e suas colunas. |
| 298 | Pega o numero do documento. |
| 299 | Pega o assunto do documento. |
| 301-302 | Junta numero e assunto para validar o ano. |
| 304-306 | Se o documento nao for do ano alvo, retorna `ignorado_ano`. |
| 308 | Monta o nome final do PDF. |
| 316-317 | Monta os caminhos possiveis em `Downloads` e `SEM_NOTA_DE_EMPENHO`. |
| 319-321 | Se o arquivo ja existe em `Downloads`, retorna `ja_baixado` sem baixar novamente. |
| 323-329 | Se ja existe em `SEM_NOTA_DE_EMPENHO`, marca que vai baixar so para nova conferencia de NE. |
| 331 | Define o caminho temporario. |
| 333 | Remove temporario antigo com o mesmo nome. |
| 335 | Mostra que vai baixar para analise. |
| 337-341 | Clica no botao de impressao/processo, espera download e salva no `TEMP`. |
| 343 | Mostra que vai analisar NE. |
| 345 | Chama `possui_nota_empenho`. |
| 347-358 | Se encontrou NE, move para `Downloads` e retorna `baixou_com_ne`. Se havia copia em `SEM_NOTA_DE_EMPENHO`, ela e removida por `remover_arquivo_da_pasta_errada`. |
| 360-379 | Se nao encontrou NE, move para `SEM_NOTA_DE_EMPENHO` somente quando ainda nao existia la. Se ja existia, descarta o temporario e retorna `ja_baixado_sem_ne`. |

## Regra tecnica de arquivo ja baixado

A regra nova evita substituicoes desnecessarias.

### Caso 1: arquivo ja existe em `Downloads`

O codigo verifica:

```python
caminho_ja_com_ne = PASTA_DOWNLOADS / nome_final
```

Se esse caminho existe:

1. o robo entende que o processo ja foi baixado com Nota de Empenho;
2. retorna `ja_baixado`;
3. nao baixa novamente;
4. se houver copia antiga em `SEM_NOTA_DE_EMPENHO`, remove essa copia.

### Caso 2: arquivo ja existe em `SEM_NOTA_DE_EMPENHO`

O codigo verifica:

```python
caminho_ja_sem_ne = PASTA_SEM_NE / nome_final
ja_estava_sem_ne = caminho_ja_sem_ne.exists()
```

Se ja estava sem NE, ele baixa para `TEMP` e analisa.

Se a nova analise encontrar Nota de Empenho:

- move o PDF temporario para `Downloads`;
- remove o antigo de `SEM_NOTA_DE_EMPENHO`;
- retorna `baixou_com_ne`.

Se a nova analise continuar sem Nota de Empenho:

- chama `descartar_temporario(caminho_temp)`;
- mantem o arquivo antigo;
- retorna `ja_baixado_sem_ne`.

### Caso 3: arquivo ainda nao existe

O fluxo normal continua:

- com NE: salva em `Downloads`;
- sem NE: salva em `SEM_NOTA_DE_EMPENHO`.

## Funcao `main`

Linhas 353-475.

Controla o fluxo completo.

| Linha(s) | O que faz |
|---|---|
| 354 | Inicia o Playwright. |
| 355-358 | Abre o Chrome visivel. |
| 360-362 | Cria contexto aceitando downloads. |
| 364 | Cria uma nova aba. |
| 365 | Abre a tela inicial do SPED. |
| 367 | Pausa e espera o usuario fazer login e apertar ENTER. |
| 369-371 | Vai para `Processos Encaminhados` e espera a tabela. |
| 373 | Comeca na pagina 1. |
| 374-379 | Inicializa contadores do resumo final. |
| 381 | Comeca o loop de paginas. |
| 382 | Mostra no terminal a pagina atual. |
| 384-385 | Espera a tabela e conta as linhas. |
| 387 | Percorre cada linha da tabela. |
| 388 | Mostra qual processo esta sendo tratado. |
| 390 | Comeca um bloco de protecao contra erro. |
| 391-394 | Lê o texto da linha e valida o ano. |
| 396-399 | Se nao for `2026`, ignora e segue. |
| 401-402 | Prepara variaveis de resultado e ultimo erro. |
| 404 | Inicia ate `MAX_TENTATIVAS_PROCESSO` tentativas. |
| 406 | Tenta baixar/processar o processo. |
| 407 | Se deu certo, sai do loop de tentativas. |
| 408-414 | Se deu erro, guarda e mostra o detalhe. |
| 416-418 | Se ainda ha tentativas, volta para a pagina e tenta de novo. |
| 420-431 | Se todas falharam, registra como `PULADO`, volta para a pagina e segue. |
| 433-437 | Se o documento foi ignorado por ano, conta e segue. |
| 469-473 | Se o documento ja tinha sido baixado, conta em `total_ja_baixados` e segue. |
| 475 | Conta processo realmente processado. |
| 477-480 | Atualiza contadores de com NE ou sem NE. |
| 446-449 | Captura erros fora do fluxo de tentativa. |
| 451-452 | Volta para a pagina atual e espera. |
| 454-455 | Se nao existe proxima pagina, termina. |
| 457-461 | Se existe, clica em proxima pagina e incrementa o contador. |
| 463-473 | Mostra o resumo final e as pastas usadas. |
| 475 | Espera ENTER antes de fechar, para o usuario conseguir ler o resultado. |

## Bloco final

Linhas 478-479.

```python
if __name__ == "__main__":
    main()
```

Isso significa: se o arquivo for executado diretamente com `python robo_sped.py`, rode a funcao `main`.

## Como alterar configuracoes

### Ano alvo

Linha 13:

```python
ANO_ALVO = "2026"
```

Troque para outro ano se precisar.

### Tentativas antes de pular

Linha 14:

```python
MAX_TENTATIVAS_PROCESSO = 3
```

Se quiser que ele tente 5 vezes antes de pular:

```python
MAX_TENTATIVAS_PROCESSO = 5
```

### Pasta base

Linha 16:

```python
PASTA_BASE = Path(r"C:\Users\salcaux05\Desktop\robo_sped")
```

Essa linha define onde ficam `Downloads`, `SEM_NOTA_DE_EMPENHO`, `PULADOS` e `TEMP`.

Se quiser que as saidas fiquem dentro da pasta `Ciclo de postagem`, altere para algo como:

```python
PASTA_BASE = Path(r"C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped")
```

## Pontos importantes de funcionamento

### O login ainda e manual

O script abre o SPED e pausa na linha 367.

O usuario precisa:

1. fazer login;
2. ir para `Processos Encaminhados`;
3. apertar ENTER no terminal.

Depois disso o processo e automatico.

### O filtro de ano e preventivo

O robo ignora processos de outro ano quando encontra ano na linha da tabela ou no documento.

Se nenhum ano aparecer na tela, ele deixa seguir, porque pode conseguir validar depois.

### Ele baixa somente o primeiro documento assinado

Na funcao `baixar_processo`, o codigo usa:

```python
primeira_linha_doc = tabela_docs.first
```

Ou seja, ele sempre trabalha com o primeiro documento da tabela `Documentos assinados`.

### Classificacao por Nota de Empenho

Depois de baixar o PDF:

- se encontrar NE, vai para `Downloads`;
- se nao encontrar NE, vai para `SEM_NOTA_DE_EMPENHO`;
- se ja existir em `Downloads`, nao baixa de novo;
- se ja existir em `SEM_NOTA_DE_EMPENHO`, so substitui se a nova versao tiver NE;
- se falhar varias vezes, cria registro em `PULADOS`.

## Resumo tecnico curto

Entrada:

- tabela de processos encaminhados no SPED.

Processamento:

- filtro por ano;
- abertura do processo;
- download do PDF;
- leitura do PDF;
- busca por NE;
- separacao em pastas.

Saida:

- PDFs com NE;
- PDFs sem NE;
- registros de processos pulados;
- resumo final no terminal.
