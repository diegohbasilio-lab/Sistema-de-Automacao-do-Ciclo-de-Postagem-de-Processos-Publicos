# Tutorial tecnico do postar.py

Este documento explica o funcionamento tecnico do arquivo:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\postar.py`

O arquivo e grande, entao a explicacao esta organizada por blocos e funcoes principais.

## Objetivo do codigo

O `postar.py` automatiza a publicacao dos PDFs ja separados pelo `separador_pdf.py`.

Ele:

1. localiza PDFs pendentes;
2. extrai metadados do PDF;
3. abre o site de licitacoes;
4. faz login automaticamente;
5. navega ate a UG, ano e categoria correta;
6. cria ou abre colecao;
7. cria item;
8. anexa PDF;
9. clica em `Depositar`;
10. registra o PDF como postado ou pulado.

Atualizacao revisada: o codigo agora tambem pula PDFs com 10 MB ou mais, simplifica nomes antes de renomear, usa copia temporaria para caminhos muito longos, procura colecao por nome exato, verifica item existente dentro da colecao e so deposita depois da confirmacao visual do upload pronto.

## Bibliotecas usadas

| Biblioteca | Uso |
|---|---|
| `pathlib.Path` | Manipular caminhos de arquivos. |
| `re` | Expressões regulares para extrair DIEx, SRP, UG, NE e limpar textos. |
| `json` | Ler e salvar controle de postados/pulados e credenciais. |
| `unicodedata` | Normalizar acentos para comparacoes robustas. |
| `datetime` | Datas de publicacao. |
| `pypdf.PdfReader` | Ler texto e contar paginas dos PDFs. |
| `playwright.sync_api` | Controlar Firefox e interagir com o site. |

## Configuracoes principais

Linhas principais do inicio do arquivo:

```python
URL_SITE = "https://licitacoeseb.4rm.eb.mil.br/home"
URL_UNIDADES_GESTORAS = "https://licitacoeseb.4rm.eb.mil.br/community-list"
PASTA_SCRIPT = Path(__file__).parent
PASTA_PROCESSOS_SEPARADOS = PASTA_SCRIPT / "processos_separados"
PASTA_BASE = PASTA_PROCESSOS_SEPARADOS if PASTA_PROCESSOS_SEPARADOS.exists() else PASTA_SCRIPT
ARQUIVO_CONTROLE = PASTA_BASE / "postados_teste.json"
ARQUIVO_CREDENCIAIS = PASTA_SCRIPT / "credenciais_login.json"
UG_OBRIGATORIA = "160109 - 4ª Cia Com L Mth"
ANO_OBRIGATORIO = "Ano 2026 - 4ª Cia Com L Mth"
CONFIRMAR_ANTES_DEPOSITAR = False
CLICAR_DEPOSITAR = True
MAX_TENTATIVAS_RELOGIN = 5
TAMANHO_MAXIMO_PDF_MB = 10
PASTA_TEMP_UPLOAD = PASTA_SCRIPT / "_upload_temp"
```

### O que cada configuracao faz

`URL_SITE`

Pagina inicial do sistema.

`URL_UNIDADES_GESTORAS`

Pagina da arvore/lista de unidades gestoras.

`PASTA_SCRIPT`

Pasta onde o `postar.py` esta salvo.

`PASTA_PROCESSOS_SEPARADOS`

Pasta esperada com os PDFs classificados.

`PASTA_BASE`

Se existir `processos_separados`, usa ela. Se nao existir, usa a propria pasta do script.

`ARQUIVO_CONTROLE`

Arquivo JSON que guarda PDFs ja postados e pulados.

`ARQUIVO_CREDENCIAIS`

Arquivo JSON com credenciais para login automatico.

`UG_OBRIGATORIA`

UG que o robo procura.

`ANO_OBRIGATORIO`

Ano da arvore que o robo abre.

`CONFIRMAR_ANTES_DEPOSITAR`

Se `True`, pede confirmacao antes de depositar. Hoje esta `False`.

`CLICAR_DEPOSITAR`

Se `True`, deposita. Se `False`, faz teste sem depositar.

`MAX_TENTATIVAS_RELOGIN`

Quantidade maxima de tentativas por PDF antes de marcar como `PULADO`.

`TAMANHO_MAXIMO_PDF_MB`

Limite de tamanho do PDF para postagem. Arquivo com 10 MB ou mais e marcado como `PULADO` antes de tentar abrir o site.

`PASTA_TEMP_UPLOAD`

Pasta temporaria usada quando o caminho original do PDF fica grande demais para o upload/Windows.

## Mapeamento de pastas para categorias

O dicionario `MAPEAMENTO` liga a pasta local com a categoria do site:

| Pasta local | Tipo interno | Categoria no site |
|---|---|---|
| `processo_dispensa` | `dispensa` | `1.1. Dispensa Eletronica e Dispensa de Licitacao` |
| `processo_inexigibilidade` | `inexigibilidade` | `1.2. Inexigibilidade de Licitacao` |
| `processo_participante` | `participante` | `2.1.1 Participante` |
| `processo_adesao` | `carona` | `2.1.2 Nao Participante` |
| `processo_gerenciador` | `gerenciador` | `2.1.3 Gerenciador` |

O dicionario `CATEGORIAS_ARVORE` guarda nomes alternativos usados para localizar as categorias na arvore do site, inclusive com e sem acento.

## Extracao de metadados

As funcoes principais sao:

| Funcao | O que faz |
|---|---|
| `ler_texto_pdf` | Le todo o texto do PDF. |
| `contar_paginas_pdf` | Conta paginas do PDF. |
| `extrair_numero_die_x_nome` | Extrai o numero do DIEx pelo nome do arquivo. |
| `extrair_numero_dispensa` | Procura numero da dispensa no texto. |
| `extrair_srp` | Procura numero de SRP. |
| `extrair_ug` | Procura UG. |
| `extrair_nota_empenho` | Procura Nota de Empenho. |
| `extrair_descricao_curta` | Cria uma descricao curta a partir do nome do arquivo. |
| `montar_metadados` | Junta tudo em um dicionario usado para postar. |

## `montar_metadados`

Essa e uma das funcoes centrais.

Ela recebe:

```python
montar_metadados(caminho_pdf, tipo)
```

E devolve um dicionario com campos como:

- `arquivo`
- `tipo`
- `paginas`
- `descricao_curta`
- `diex`
- `dispensa`
- `srp`
- `ug`
- `ne`
- `nome_colecao`
- `titulo_item`
- `ano`
- `mes`
- `dia`

Esses campos alimentam o nome da colecao e os campos do item no site.

## Controle de postados e pulados

Funcoes:

| Funcao | Uso |
|---|---|
| `carregar_controle` | Le `postados_teste.json`. |
| `salvar_controle` | Salva o JSON de controle. |
| `ja_postado` | Verifica se o PDF ja tem `POSTADO`, `PULADO` ou esta no controle. |
| `registrar_postado` | Registra PDF como postado. |
| `registrar_pulado` | Registra PDF como pulado, com motivo. |
| `renomear_pdf_postado` | Adiciona `- POSTADO` ao nome. |
| `renomear_pdf_pulado` | Adiciona `- PULADO` ao nome. |
| `marcar_pdf_pulado` | Registra e renomeia como pulado. |
| `simplificar_nome_pdf` | Abrevia palavras grandes antes de salvar `POSTADO` ou `PULADO`. |
| `caminho_longo_windows` | Prepara caminhos longos com prefixo do Windows quando necessario. |
| `preparar_pdf_para_postagem` | Cria copia temporaria com nome curto para upload quando o caminho original e longo. |
| `pdf_maior_que_limite` | Confere se o arquivo tem 10 MB ou mais. |

## Simplificacao de nomes

A funcao `simplificar_nome_pdf` fica por volta da linha 379.

Ela recebe o nome original sem extensao e devolve um nome menor e mais seguro. A funcao:

1. remove acentos;
2. troca termos longos por abreviacoes;
3. remove pontuacao repetida;
4. corta o resultado no limite configurado;
5. entrega o texto para `renomear_pdf_postado` ou `renomear_pdf_pulado`.

Exemplos de abreviacao:

| Termo original | Termo salvo |
|---|---|
| `servico` | `sv` |
| `aquisicao` | `aqs` |
| `requisicao` | `req` |
| `generos alimenticios` | `gen almt` |
| `material permanente` | `mat perm` |
| `material de consumo` | `mat cons` |
| `dispensa de licitacao` | `disp lic` |
| `prorrogacao contratual` | `prorr contrat` |

Isso reduz o risco de erro por nome de arquivo muito grande.

## Listagem de PDFs pendentes

`listar_pdfs_nao_postados` percorre as pastas do `MAPEAMENTO`.

Para cada PDF:

1. verifica se ja foi postado ou pulado;
2. se nao foi, adiciona na lista `pendentes`;
3. mostra contagem no terminal.

No `main`, antes de processar de verdade, o robo ainda confere se o arquivo tem 10 MB ou mais. Se tiver, ele chama `marcar_pdf_pulado` e passa para o proximo PDF.

## Normalizacao

A funcao `normalizar` transforma texto para facilitar comparacoes:

- coloca em minusculo;
- remove acentos;
- troca multiplos espacos por um so;
- remove espacos nas pontas.

Isso evita falhas por diferenca de acento, maiuscula/minuscula ou espacos.

## Automacao com Playwright

O codigo usa Playwright para controlar o Firefox.

As funcoes de automacao estao espalhadas por grupos:

| Grupo | Exemplos |
|---|---|
| Clique e validacao | `clicar_texto`, `clicar_link_ou_texto`, `clicar_e_validar` |
| Sessao/login | `sessao_caiu`, `verificar_sessao`, `abrir_site_com_login_salvo` |
| Pagina estavel | `aguardar_pagina_estavel`, `navegar_com_tentativas` |
| Login automatico | `carregar_credenciais_login`, `tentar_login_com_credenciais_salvas` |
| Upload | `anexar_pdf`, `aguardar_upload_concluido`, `garantir_upload_pdf` |
| Deposito | `validar_conteudo_antes_depositar`, `clicar_botao_depositar`, `aguardar_deposito_concluido` |

## Tratamento de sessao

Existe a classe:

```python
class SessaoExpirada(Exception):
    pass
```

Ela representa queda de login/sessao.

`sessao_caiu(page)` procura sinais como:

- `Authentication is required`
- `Unauthorized`
- `Sessao expirada`
- tela de login
- modal aberto sem colecoes

`verificar_sessao(page, contexto)` chama `sessao_caiu` e levanta `SessaoExpirada` quando detecta problema.

## Login automatico

Fluxo:

1. `abrir_site_com_login_salvo` abre o site.
2. Se o perfil salvo ja estiver logado, continua.
3. Se nao estiver, tenta usar `credenciais_login.json`.
4. Se conseguir login, chama `aguardar_pos_login`.
5. Se nao conseguir, gera erro.

## Navegacao na arvore

Funcoes principais:

| Funcao | O que faz |
|---|---|
| `abrir_lista_unidades_gestoras` | Vai para lista de UGs. |
| `clicar_setinha_arvore` | Clica na seta de uma categoria. |
| `expandir_arvore_ate_aparecer` | Abre uma parte da arvore ate aparecer o alvo. |
| `preparar_arvore_unidades` | Abre UG 160109, Ano 2026, Contratacoes Diretas, Licitacoes e Pregao. |
| `localizar_url_categoria_na_arvore` | Descobre a URL da categoria correta. |
| `abrir_categoria_em_nova_guia` | Abre a categoria em uma nova aba. |

## Criacao de colecao

Funcoes principais:

| Funcao | O que faz |
|---|---|
| `abrir_colecao_existente_se_houver` | Procura colecao ja existente. |
| `localizar_url_colecao_visivel` | Procura a colecao por nome normalizado exato, evitando confundir nomes parecidos. |
| `criar_colecao` | Cria a colecao se nao existir. |
| `preencher_nome_colecao` | Preenche nome da colecao. |
| `preencher_descricao_curta_colecao` | Preenche descricao curta. |
| `salvar_colecao_e_aguardar` | Salva e aguarda confirmacao. |

O ponto importante e que a busca de colecao nao deve aceitar apenas "contem o texto". Ela normaliza o nome da tela e compara com o nome esperado. Isso reduz o risco de abrir uma colecao parecida, mas errada.

## Criacao de item e postagem

Funcao principal:

```python
criar_item_e_postar_pdf(page, metadados)
```

Fluxo:

1. Abre `Novo > Item`.
2. Seleciona a primeira opcao do modal.
3. Preenche titulo.
4. Anexa PDF.
5. Aguarda upload.
6. Preenche data.
7. Marca licenca.
8. Mostra conferencia no terminal.
9. Valida conteudo antes de depositar.
10. Clica em `Depositar`.
11. Aguarda conclusao.
12. Retorna `True` se depositou.

Antes de chamar essa funcao, o `main` usa `item_ja_existe_na_colecao(page, titulo_item)`. Essa funcao procura o titulo do item dentro da colecao aberta. Se o item ja existir, o robo registra o PDF como `POSTADO`, renomeia o arquivo e nao cria uma copia duplicada no site.

## Upload

O upload tem varias protecoes:

- detecta upload em andamento;
- detecta falha de upload;
- detecta upload parado em `0%`;
- detecta o visual de PDF pronto;
- confere se o PDF aparece anexado com nome, tamanho e botoes/sinais visuais;
- se o PDF nao aparecer pronto, tenta anexar novamente;
- se falhar 3 vezes, levanta `UploadTravado`.

Funcoes importantes:

- `upload_em_andamento`
- `upload_falhou`
- `upload_concluido`
- `pdf_anexado_na_tela`
- `area_upload_mostra_pdf_pronto`
- `upload_visual_em_processamento`
- `upload_visual_com_erro_percentual`
- `aguardar_upload_concluido`
- `garantir_upload_pdf`
- `validar_conteudo_antes_depositar`

### Linha a linha logica do upload atual

`area_upload_mostra_pdf_pronto`, por volta da linha 3152, e a trava principal. Ela olha o texto visivel da pagina e so retorna `True` quando:

1. nao aparece `Nenhum arquivo enviado ainda`;
2. aparece o nome do PDF ou partes fortes do nome;
3. aparece tamanho de arquivo, como `(1.27 MB)`;
4. aparece algum sinal de arquivo pronto, como `Sem Miniatura`, botao de baixar, editar, excluir ou check verde.

`upload_visual_com_erro_percentual`, por volta da linha 3278, identifica erro visual quando a linha do PDF aparece com `0%`.

`aguardar_upload_concluido`, por volta da linha 3485, executa a espera visual:

1. verifica se houve erro de upload;
2. se aparecer `0%`, considera falha;
3. se `area_upload_mostra_pdf_pronto` retornar `True`, libera imediatamente;
4. se aparecer botao de realizar upload, tenta clicar nele;
5. enquanto houver processamento visual, continua aguardando;
6. se passar de 3 minutos sem visual pronto, retorna falha.

`garantir_upload_pdf`, por volta da linha 3761, controla as 3 tentativas:

1. se o PDF ja aparece pronto, nao envia de novo;
2. espera a area de upload carregar;
3. chama `anexar_pdf`;
4. chama `aguardar_upload_concluido`;
5. se falhar, recarrega a pagina;
6. repete ate 3 vezes;
7. se nenhuma tentativa confirmar o upload, levanta `UploadTravado`.

`validar_conteudo_antes_depositar`, por volta da linha 3830, e a ultima barreira antes do clique em `Depositar`. Ela confirma novamente se o upload esta pronto e, se nao estiver, chama `garantir_upload_pdf`.

## Deposito

`clicar_botao_depositar` tenta clicar no botao `Depositar`.

Ele tenta por:

- botao visivel;
- botao por posicao;
- confirmacao de mudanca na tela.

Se nada mudar, tenta mais uma vez.

Se mesmo assim nao confirmar, retorna `False` e o fluxo principal trata como erro.

## Recuperacao automatica

O fluxo principal usa `MAX_TENTATIVAS_RELOGIN = 5`.

Para cada PDF:

- se a sessao cair, fecha o navegador, abre de novo, faz login e tenta novamente;
- se o upload travar, tenta reenviar ate 3 vezes dentro do item; se ainda falhar, marca `PULADO`;
- se der erro comum, fecha a guia ruim, atualiza a pagina inicial e tenta novamente;
- se o mesmo PDF falhar 5 vezes, chama `marcar_pdf_pulado`.

## Funcoes auxiliares recentes

`fechar_navegador(context)`

Fecha o contexto/navegador sem deixar erro quebrar o fluxo.

`abrir_navegador_logado(p, opcoes_firefox)`

Abre Firefox com perfil persistente, fecha abas extras, abre o site, loga e prepara a arvore.

`atualizar_pagina_base(pagina_base)`

Traz a pagina inicial para frente, recarrega e espera estabilizar.

## Fluxo principal `main`

Passo a passo:

1. Lista PDFs pendentes.
2. Se nao houver pendentes, encerra.
3. Abre Playwright.
4. Configura Firefox persistente.
5. Abre navegador logado.
6. Para cada PDF:
   - verifica se ja foi postado;
   - se tiver 10 MB ou mais, marca `PULADO`;
   - faz ate 5 tentativas;
   - cria copia temporaria se o caminho for longo;
   - monta metadados;
   - abre categoria correta;
   - cria/abre colecao;
   - verifica se o item ja existe na colecao;
   - cria item e posta;
   - registra como postado;
   - renomeia com `POSTADO`.
7. Se falhar 5 vezes:
   - registra como pulado;
   - renomeia com `PULADO`;
   - segue para o proximo.
8. Fecha o navegador no `finally`.
9. Mostra resumo final.

## Arquivos gerados ou alterados

`postados_teste.json`

Controle de arquivos postados e pulados.

PDFs renomeados com `POSTADO`

Arquivos ja depositados.

PDFs renomeados com `PULADO`

Arquivos que falharam no limite de tentativas.

## Configuracoes que podem ser alteradas

### Nao depositar, apenas testar

```python
CLICAR_DEPOSITAR = False
```

### Pedir confirmacao antes de depositar

```python
CONFIRMAR_ANTES_DEPOSITAR = True
```

### Alterar tentativas por PDF

```python
MAX_TENTATIVAS_RELOGIN = 5
```

### Alterar UG/Ano

```python
UG_OBRIGATORIA = "160109 - 4ª Cia Com L Mth"
ANO_OBRIGATORIO = "Ano 2026 - 4ª Cia Com L Mth"
```

## Resumo tecnico curto

Entrada:

- PDFs classificados em `processos_separados`.

Processamento:

- extracao de metadados;
- login automatico;
- navegacao no site;
- criacao/abertura de colecao;
- upload e deposito;
- controle de falhas.

Saida:

- PDFs com `POSTADO`;
- PDFs com `PULADO`;
- controle JSON atualizado;
- resumo final no terminal.
