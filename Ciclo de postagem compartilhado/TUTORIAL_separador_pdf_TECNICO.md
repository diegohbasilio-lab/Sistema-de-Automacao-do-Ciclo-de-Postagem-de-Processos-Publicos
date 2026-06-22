# Tutorial tecnico do separador_pdf.py

Este documento explica o funcionamento tecnico do arquivo:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\separador_pdf.py`

## Objetivo do codigo

O `separador_pdf.py` classifica PDFs de processos administrativos.

Ele le arquivos da pasta `entrada`, identifica ano, Nota de Empenho, assunto e tipo de processo, e move cada PDF para uma pasta em `processos_separados`.

## Bibliotecas usadas

| Biblioteca | Uso |
|---|---|
| `os` | Manipular pastas, nomes e caminhos. |
| `re` | Expressoes regulares para identificar padroes. |
| `shutil` | Mover arquivos. |
| `unicodedata` | Remover acentos e normalizar texto. |
| `hashlib` | Calcular hash SHA-256 para detectar duplicados. |
| `pypdf` ou `PyPDF2` | Ler texto dos PDFs. |

## Pastas principais

```python
input_folder = "entrada/"
output_base = "processos_separados/"
```

`input_folder`

Pasta onde ficam os PDFs de entrada.

`output_base`

Pasta onde o robo salva os PDFs separados.

## Categorias criadas

O codigo cria automaticamente estas pastas:

- `processo_participante`
- `processo_gerenciador`
- `processo_adesao`
- `processo_dispensa`
- `processo_inexigibilidade`
- `processo_sem_nota_empenho`
- `fora_2026_ignorados`
- `nao_categorizado`
- `duplicados_ignorados`

## Criacao das pastas

O bloco:

```python
for cat in categorias:
    os.makedirs(os.path.join(output_base, cat), exist_ok=True)
```

garante que todas as pastas de saida existam.

Se ja existirem, nao da erro.

## Normalizacao de texto

Funcao:

```python
normalizar(texto)
```

Ela:

1. transforma em minusculo;
2. remove acentos;
3. corrige alguns caracteres quebrados;
4. troca multiplos espacos por um so;
5. remove espacos das pontas.

Isso melhora a classificacao porque evita diferencas por acento, caixa alta ou espacos.

## Deteccao de duplicados

Funcoes:

- `calcular_hash_arquivo`
- `construir_indice_hashes_processados`

`calcular_hash_arquivo` le o PDF em blocos e calcula SHA-256.

Se dois arquivos tiverem o mesmo conteudo, terao o mesmo hash.

`construir_indice_hashes_processados` varre as pastas de saida e monta um dicionario:

```python
hash_do_pdf -> caminho_do_pdf_ja_separado
```

Quando um PDF novo tem hash ja conhecido, ele vai para:

`duplicados_ignorados`

## Extracao de texto

Funcao:

```python
extrair_texto_pdf(pdf_path)
```

Ela:

1. abre o PDF;
2. percorre pagina por pagina;
3. extrai texto;
4. normaliza cada pagina;
5. junta tudo em `texto_total`;
6. retorna `texto_total` e `textos_paginas`.

`textos_paginas` e importante porque algumas regras olham so as primeiras paginas ou ignoram paginas de SICAF.

## Extracao de NUP

Funcao:

```python
extrair_nup(texto_total)
```

Procura padrao:

```text
00000.000000/0000-00
```

Se encontrar, retorna o NUP.

## Identificacao e limpeza de assunto

Funcoes:

- `limpar_assunto`
- `assunto_do_nome_arquivo`
- `extrair_assunto_texto`
- `identificar_assunto_processo`
- `formatar_assunto_para_nome`
- `abreviar_assunto_nome`
- `nome_com_assunto`

### `limpar_assunto`

Remove termos genericos como:

- `rachurado`
- `pdf`
- `processo`
- `administrativo`
- `nup`
- NE
- numeros de processo

Tambem corta trechos depois de palavras como `despacho`, `termo`, `justificativa`, `nota de empenho`, etc.

### `assunto_do_nome_arquivo`

Tenta descobrir o assunto usando o proprio nome do PDF.

Ele valoriza termos como:

- aquisicao;
- contratacao;
- servico;
- fornecimento;
- manutencao;
- material;
- energia;
- agua;
- telefonia;
- correios.

### `extrair_assunto_texto`

Procura o assunto nas primeiras paginas usando padroes como:

- `objeto:`
- `assunto:`
- `requisicao de`
- `solicitacao de`
- `aquisicao de`
- `contratacao de`

### `identificar_assunto_processo`

Primeiro tenta pelo nome do arquivo.

Se nao encontrar, tenta pelo texto do PDF.

### `formatar_assunto_para_nome`

Prepara o assunto para aparecer no nome do arquivo.

### `abreviar_assunto_nome`

Troca termos longos por abreviacoes, por exemplo:

- `aquisicao` -> `Aqs`
- `contratacao` -> `Contr`
- `servico` -> `Sv`
- `material` -> `Mat`

### `nome_com_assunto`

Adiciona o assunto ao nome do PDF, quando ele ainda nao esta no nome.

## Controle de nome de arquivo

Funcoes:

- `limpar_nome_arquivo`
- `limitar_nome_arquivo`
- `gerar_caminho_sem_sobrescrever`

Elas evitam:

- caracteres proibidos no Windows;
- nome longo demais;
- sobrescrever arquivo existente.

Se ja existir um arquivo com o mesmo nome, o robo adiciona contador.

## Identificacao do ano do processo

Funcao:

```python
identificar_ano_processo(pdf_file, textos_paginas)
```

Ela tenta identificar o ano por sinais fortes:

- DIEx com ano;
- requisicao com ano;
- solicitacao com ano;
- processo administrativo com ano;
- NUP;
- ano no nome do arquivo;
- padroes como `2026-1` ou `2026/1`.

Se nao encontrar `2026`, o PDF vai para:

`fora_2026_ignorados`

Isso evita postar processo de outro ano.

## Paginas ignoradas

Funcao:

```python
eh_pagina_sicaf_ou_ocorrencia(texto)
```

Identifica paginas de:

- SICAF;
- ocorrencias ativas;
- CADIN;
- CEIS;
- consultas consolidadas.

Essas paginas podem citar Nota de Empenho antiga ou informacoes de fornecedor, entao sao ignoradas para evitar falso positivo.

## Texto confiavel

Funcao:

```python
montar_textos_confiaveis(textos_paginas)
```

Ela monta dois blocos:

`texto_confiavel`

Usa inicio do processo e paginas de NE real.

`texto_ne`

Usa apenas paginas que parecem ser Nota de Empenho real.

Esse filtro evita que SICAF ou ocorrencias contaminem a classificacao.

## Verificacao de Nota de Empenho

Funcao:

```python
possui_nota_empenho(texto_total, textos_paginas)
```

Ela considera NE real quando encontra:

- NE na lista de pecas processuais;
- ou pagina com `nota de empenho`;
- e sinais como `impressao completa`, `ano tipo numero`, `celula orcamentaria`, `favorecido`, etc.

Se nao encontrar NE real, o PDF vai para:

`processo_sem_nota_empenho`

## Classificacao por pontuacao

Funcao:

```python
classificar_processo(pdf_file, texto_confiavel, texto_ne)
```

Ela cria um dicionario de pontuacao:

```python
scores = {
    "processo_participante": 0,
    "processo_gerenciador": 0,
    "processo_adesao": 0,
    "processo_dispensa": 0,
    "processo_inexigibilidade": 0
}
```

Depois aplica regras.

## Principais regras de classificacao

### Inexigibilidade por energia eletrica

Procura termos como:

- `energia eletrica`
- `concessionaria de energia`
- `conta de energia`
- `unidade consumidora`

Ganha pontuacao alta para `processo_inexigibilidade`.

### Protecao contra falso positivo de gerador

Se aparecer `gerador de energia`, o codigo reduz pontuacao de inexigibilidade.

Isso evita confundir compra/manutencao de gerador com fornecimento de energia eletrica.

### Gerenciador especial

Termos como:

- Correios;
- telefonia movel;
- dosimetria;

favorecem `processo_gerenciador`.

### Adesao/carona

Termos fortes:

- `nao participante`;
- `orgao nao participante`;
- `carona`;
- `adesao a ata`;
- `estudo de eficiencia`.

favorecem `processo_adesao`.

### Participante

Termos como:

- `(part)`;
- `(participante)`;
- `UASG participante`;
- SRP + UG + Pregao sem sinais de carona.

favorecem `processo_participante`.

### Dispensa

Termos como:

- `dispensa de licitacao`;
- `dispensa eletronica`;
- `art. 75`.

favorecem `processo_dispensa`.

### Inexigibilidade geral

Termos como:

- `inexigibilidade`;
- `fornecedor exclusivo`;
- `atestado de exclusividade`;
- `art. 74`.

favorecem `processo_inexigibilidade`.

## Resultado da classificacao

A maior pontuacao vence.

Se o melhor score for menor que `40`, o PDF vai para:

`nao_categorizado`

## Funcao `classificar_pdf`

Essa funcao organiza o fluxo de decisao:

1. extrai texto;
2. se nao houver texto, retorna `nao_categorizado`;
3. identifica ano;
4. identifica assunto;
5. se nao for 2026, retorna `fora_2026_ignorados`;
6. verifica Nota de Empenho;
7. se nao tiver NE, retorna `processo_sem_nota_empenho`;
8. monta texto confiavel;
9. classifica o processo por pontuacao;
10. retorna categoria, score, scores, motivos e assunto.

## Processamento final

O bloco final executa quando o arquivo roda.

Fluxo:

1. monta indice de hashes ja processados;
2. lista PDFs da pasta `entrada`;
3. para cada PDF:
   - calcula hash;
   - se hash ja existe, move para `duplicados_ignorados`;
   - se nao existe, classifica;
   - escolhe pasta destino;
   - monta nome com assunto;
   - gera caminho sem sobrescrever;
   - move o arquivo;
   - adiciona hash ao indice;
   - imprime categoria, score, scores e motivos.
4. no final imprime `Processo concluido.`

## Arquivos duplicados

O robo nao olha apenas o nome.

Ele calcula hash SHA-256 do conteudo.

Entao dois arquivos com nomes diferentes, mas conteudo igual, sao considerados duplicados.

## Onde mexer se precisar ajustar

### Alterar pasta de entrada

```python
input_folder = "entrada/"
```

### Alterar pasta de saida

```python
output_base = "processos_separados/"
```

### Alterar categorias

Editar a lista:

```python
categorias = [...]
```

### Alterar regra de ano

Editar a funcao:

```python
identificar_ano_processo(...)
```

### Alterar regra de Nota de Empenho

Editar:

```python
possui_nota_empenho(...)
```

### Alterar classificacao

Editar:

```python
classificar_processo(...)
```

## Resumo tecnico curto

Entrada:

- PDFs na pasta `entrada`.

Processamento:

- leitura de texto;
- hash para duplicados;
- identificacao de ano;
- validacao de NE;
- classificacao por pontuacao;
- renomeacao com assunto.

Saida:

- PDFs movidos para `processos_separados`;
- duplicados isolados;
- PDFs fora de 2026 ignorados;
- PDFs sem NE separados;
- logs com motivos e pontuacoes.

