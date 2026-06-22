# Tutorial simples do postar.py

Este tutorial explica como usar o robo de postagem sem precisar entender programacao.

## Para que serve

O `postar.py` pega os PDFs que ja foram separados pelo `separador_pdf.py` e posta esses arquivos no site:

`https://licitacoeseb.4rm.eb.mil.br/home`

Ele cria ou abre a colecao correta, cria o item, anexa o PDF, preenche os dados principais e clica em `Depositar`.

Atualizacao importante: o robo tambem evita ficar preso em PDFs problematicos. Se o PDF for muito grande, se o upload falhar repetidamente ou se o mesmo item ja existir na colecao, ele registra o caso e segue o trabalho.

## Onde fica

Arquivo principal:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\postar.py`

Pasta usada:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem`

## De onde ele pega os PDFs

Ele procura PDFs dentro da pasta:

`separador-postagem\processos_separados`

As pastas usadas para postagem sao:

- `processo_dispensa`
- `processo_inexigibilidade`
- `processo_participante`
- `processo_adesao`
- `processo_gerenciador`

Ele nao posta pastas como `processo_sem_nota_empenho`, `fora_2026_ignorados`, `nao_categorizado` e `duplicados_ignorados`.

## O que cada pasta significa

`processo_dispensa`

Processos classificados como dispensa de licitacao.

`processo_inexigibilidade`

Processos classificados como inexigibilidade.

`processo_participante`

Processos de pregao/SRP em que a unidade aparece como participante.

`processo_adesao`

Processos de adesao/carona, tambem chamados de nao participante.

`processo_gerenciador`

Processos em que a unidade e gerenciadora.

## Antes de rodar

Verifique se:

1. Os PDFs ja estao separados nas pastas certas.
2. O arquivo `credenciais_login.json` existe na pasta `separador-postagem`.
3. O Firefox/Playwright consegue abrir o site.
4. Voce nao precisa mexer no navegador enquanto o robo trabalha.

## Como rodar

Abra o PowerShell e rode:

```powershell
cd "C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem"
python postar.py
```

Se o comando `python` nao funcionar, use o Python instalado para o projeto, se existir no seu ambiente.

## O que acontece quando inicia

O robo mostra uma conferencia:

```text
PDFs encontrados nas pastas
PDFs ja registrados como postados
PDFs pendentes para postagem
```

Depois ele abre o site, tenta confirmar o login e prepara a arvore:

- UG `160109`
- Ano `2026`
- Contratacoes Diretas
- Licitacoes
- Pregao

## Como ele escolhe onde postar

Cada pasta local aponta para uma categoria no site:

- `processo_dispensa` vai para `1.1. Dispensa Eletronica e Dispensa de Licitacao`
- `processo_inexigibilidade` vai para `1.2. Inexigibilidade de Licitacao`
- `processo_participante` vai para `2.1.1 Participante`
- `processo_adesao` vai para `2.1.2 Nao Participante`
- `processo_gerenciador` vai para `2.1.3 Gerenciador`

## O que ele faz em cada PDF

Para cada PDF pendente, o robo:

1. Confere se ele ja tem `POSTADO` ou `PULADO`.
2. Confere se o tamanho e menor que 10 MB.
3. Le o PDF.
4. Extrai metadados, como DIEx, NE, UG, SRP, dispensa e paginas.
5. Monta o nome da colecao.
6. Abre a categoria correta no site.
7. Verifica se a colecao ja existe com o nome exato.
8. Se existir, abre a colecao.
9. Se nao existir, cria a colecao.
10. Confere se o item com aquele titulo ja existe dentro da colecao.
11. Se o item ja existir, marca o PDF como `POSTADO` e segue.
12. Se o item nao existir, cria um item dentro da colecao.
13. Anexa o PDF.
14. Aguarda o site mostrar visualmente que o PDF esta pronto.
15. Preenche titulo, data e licenca.
16. Valida novamente se o PDF continua anexado.
17. Clica em `Depositar`.
18. Confirma que o deposito terminou.
19. Marca o PDF como postado.
20. Renomeia o PDF com `POSTADO`.

## Regra dos PDFs grandes

PDF com 10 MB ou mais nao e postado.

Quando isso acontece, o robo:

1. registra o motivo;
2. renomeia o arquivo com `PULADO`;
3. segue para o proximo PDF.

Essa regra existe porque os PDFs maiores costumam travar ou falhar no upload do site.

## O que significa POSTADO

Quando o robo conclui um PDF, ele renomeia o arquivo adicionando:

```text
- POSTADO
```

Isso evita que o mesmo PDF seja postado de novo.

Ele tambem registra o caminho no arquivo:

`processos_separados\postados_teste.json`

## O que significa PULADO

Se o mesmo PDF falhar varias vezes, ou se for grande demais, o robo nao fica preso nele.

O limite atual e:

```text
5 tentativas
```

Depois disso, ou depois de 3 falhas de upload no mesmo item, ele:

1. renomeia o PDF com `- PULADO`;
2. registra o motivo no controle;
3. fecha a guia ruim;
4. segue para o proximo PDF.

O nome final tambem e simplificado antes de receber `POSTADO` ou `PULADO`. Exemplos:

- `servico` vira `sv`;
- `aquisicao` vira `aqs`;
- `requisicao` vira `req`;
- `generos alimenticios` vira `gen almt`;
- `material permanente` vira `mat perm`.

Isso evita nomes enormes e problemas de caminho muito longo no Windows.

## Como o robo sabe que o upload terminou

Ele nao deve clicar em `Depositar` apenas porque esperou um tempo.

Antes de depositar, o robo procura sinais visuais na tela:

- o nome do PDF aparece na area de upload;
- aparece o tamanho do arquivo, como `(1.27 MB)`;
- aparece `Sem Miniatura` ou botoes como baixar, editar ou excluir;
- nao aparece a mensagem `Nenhum arquivo enviado ainda`;
- nao aparece erro de upload, como barra parada em `0%`.

Se o PDF aparecer pronto, ele deposita sem esperar 3 minutos.

Se o upload ficar carregando e nao aparecer pronto, ele aguarda ate 3 minutos. Se nao concluir, recarrega a pagina e tenta anexar de novo. Sao no maximo 3 tentativas de upload por PDF.

## O que acontece em caso de erro

O robo foi ajustado para trabalhar sozinho:

- erro comum: fecha a guia ruim, atualiza a pagina inicial, prepara a arvore e tenta de novo;
- queda de login/sessao: fecha o navegador, abre novamente, refaz login e tenta de novo;
- upload travado ou com erro visual: recarrega a pagina, tenta anexar novamente e, se falhar 3 vezes, marca `PULADO`;
- 5 falhas no mesmo PDF: marca como `PULADO` e segue.

## Quando ele pode pedir alguma coisa

Existe uma configuracao chamada:

```python
CONFIRMAR_ANTES_DEPOSITAR = False
```

Como esta `False`, ele nao deve pedir confirmacao antes de depositar.

Se alguem mudar para `True`, o robo vai perguntar no terminal antes de clicar em `Depositar`.

## Como testar sem depositar

No arquivo `postar.py`, existe:

```python
CLICAR_DEPOSITAR = True
```

Se trocar para `False`, o robo preenche tudo, mas nao deposita.

Use isso apenas para teste.

## Resultado final

No final, ele mostra algo parecido com:

```text
[FINALIZADO]
PDFs pulados nesta execucao: ...
Postagens concluidas nesta execucao: ...
PDFs pendentes conferidos no inicio: ...
```

## Resumo rapido

1. Rode o `separador_pdf.py` primeiro para separar os PDFs.
2. Confira as pastas em `processos_separados`.
3. Rode:

```powershell
cd "C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem"
python postar.py
```

4. Deixe o navegador aberto e nao mexa enquanto o robo trabalha.
