# Tutorial simples do separador_pdf.py

Este tutorial explica como usar o separador de PDFs sem precisar entender programacao.

## Para que serve

O `separador_pdf.py` pega PDFs da pasta `entrada` e separa cada processo na pasta correta.

Ele ajuda a preparar os arquivos para o `postar.py`.

O separador:

- identifica se o PDF e de 2026;
- verifica se existe Nota de Empenho real;
- separa por tipo de processo;
- ignora duplicados;
- move cada PDF para a pasta certa.

## Onde fica

Arquivo principal:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\separador_pdf.py`

Pasta do robô:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem`

## Pastas usadas

`entrada`

Coloque aqui os PDFs que ainda precisam ser separados.

`processos_separados`

O robo cria/usa esta pasta para guardar os PDFs classificados.

Dentro dela, existem pastas como:

- `processo_participante`
- `processo_gerenciador`
- `processo_adesao`
- `processo_dispensa`
- `processo_inexigibilidade`
- `processo_sem_nota_empenho`
- `fora_2026_ignorados`
- `nao_categorizado`
- `duplicados_ignorados`

## O que cada pasta significa

`processo_participante`

Processos em que a unidade aparece como participante.

`processo_gerenciador`

Processos em que a unidade e gerenciadora.

`processo_adesao`

Processos de adesao/carona/nao participante.

`processo_dispensa`

Processos de dispensa.

`processo_inexigibilidade`

Processos de inexigibilidade.

`processo_sem_nota_empenho`

PDFs que parecem validos, mas nao possuem Nota de Empenho real identificada.

`fora_2026_ignorados`

PDFs que nao parecem ser de 2026.

`nao_categorizado`

PDFs que o robo nao conseguiu classificar com seguranca.

`duplicados_ignorados`

PDFs repetidos. O robo compara o conteudo do arquivo, nao apenas o nome.

## Como usar

1. Coloque os PDFs na pasta:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\entrada
```

2. Abra o PowerShell.

3. Entre na pasta:

```powershell
cd "C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem"
```

4. Rode:

```powershell
python separador_pdf.py
```

5. Aguarde terminar.

## O que acontece durante a execucao

Para cada PDF na pasta `entrada`, o robo:

1. le o texto do PDF;
2. verifica se e duplicado;
3. tenta identificar o ano do processo;
4. se nao for 2026, move para `fora_2026_ignorados`;
5. procura Nota de Empenho real;
6. se nao encontrar, move para `processo_sem_nota_empenho`;
7. tenta descobrir o tipo de processo;
8. move o PDF para a pasta correta;
9. renomeia o arquivo com assunto quando consegue identificar.

## Como saber se terminou

No fim aparece:

```text
Processo concluido.
```

Ele tambem mostra no terminal o destino de cada arquivo.

## O que fazer depois

Depois que os PDFs forem separados, rode o `postar.py` para postar os arquivos das pastas corretas.

Normalmente, o `postar.py` usa estas pastas:

- `processo_dispensa`
- `processo_inexigibilidade`
- `processo_participante`
- `processo_adesao`
- `processo_gerenciador`

## Cuidados

Nao coloque arquivos que nao sejam PDF na pasta `entrada`.

Se o PDF for escaneado como imagem e nao tiver texto pesquisavel, o robo pode nao conseguir classificar.

Se cair em `nao_categorizado`, precisa verificar manualmente.

Se cair em `processo_sem_nota_empenho`, precisa conferir se realmente nao ha NE.

Se cair em `fora_2026_ignorados`, confira se o processo realmente nao e de 2026.

## Resumo rapido

```powershell
cd "C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem"
python separador_pdf.py
```

Entrada:

`entrada`

Saida:

`processos_separados`

