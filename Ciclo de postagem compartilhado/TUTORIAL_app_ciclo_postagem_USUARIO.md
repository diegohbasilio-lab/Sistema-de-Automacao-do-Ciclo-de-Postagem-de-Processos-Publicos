# Tutorial simples do app_ciclo_postagem.py

Este tutorial explica como usar o aplicativo `Ciclo de Postagem` sem precisar abrir o VS Code ou rodar comandos no terminal.

## Para que serve

O `app_ciclo_postagem.py` e uma janela de controle para executar os robos do ciclo de postagem.

Ele centraliza quatro etapas:

1. baixar processos do SPED;
2. rachurar PDFs;
3. separar PDFs;
4. postar PDFs no site de licitacoes.

Ele tambem abre as principais pastas de trabalho com botoes, para voce colocar ou conferir arquivos com mais facilidade.

## Onde fica

Arquivo principal:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\app_ciclo_postagem.py
```

Pasta principal do ciclo:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem
```

## Como abrir o app

Entre na pasta `Ciclo de postagem` e execute:

```powershell
python app_ciclo_postagem.py
```

Se voce tiver criado um atalho para esse arquivo, basta abrir pelo atalho.

## Como a tela e organizada

A tela tem duas partes principais.

Na esquerda ficam:

- botoes para executar os robos;
- botoes para abrir pastas.

Na direita ficam:

- status atual;
- botao `Enviar ENTER`;
- botao `Parar robo`;
- area de acompanhamento, onde aparece tudo que o robo escreve.

## Botoes dos robos

`Executar ciclo completo`

Roda as quatro etapas em sequencia:

1. `robo_sped.py`;
2. `rachurar_pdfs.py`;
3. `separador_pdf.py`;
4. `postar.py`.

O app so passa para a proxima etapa se a etapa anterior terminar sem erro.

`1. Baixar processos do SPED`

Executa:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\robo_sped.py
```

Serve para baixar os processos do SPED e separar o que tem Nota de Empenho.

`2. Rachurar PDFs`

Executa:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\rachurador_pdf\rachurar_pdfs.py
```

Serve para ocultar CPF, CNPJ e dados sensiveis dos PDFs.

`3. Separar PDFs`

Executa:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\separador_pdf.py
```

Serve para classificar os PDFs rachurados nas pastas corretas.

`4. Postar no site`

Executa:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\postar.py
```

Serve para postar os PDFs pendentes no site de licitacoes.

## Botoes das pastas

`Pasta geral do ciclo`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem
```

`Abrir downloads sped`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\Downloads
```

E onde ficam os processos baixados do SPED com Nota de Empenho.

`SPED - sem nota de empenho`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\SEM_NOTA_DE_EMPENHO
```

E onde ficam os processos baixados sem Nota de Empenho identificada.

`SPED - pulados`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\PULADOS
```

E onde ficam registros de processos que o `robo_sped` pulou.

`Abrir entrada rachurador`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\rachurador_pdf\entrada
```

Coloque aqui os PDFs que precisam ser rachurados.

`Abrir saida rachurador`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\rachurador_pdf\saida
```

Aqui ficam os PDFs depois de rachurados.

`Abrir entrada separador pdf`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\entrada
```

Coloque aqui os PDFs que o separador deve classificar.

`Abrir pasta processos separados`

Abre:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\separador-postagem\processos_separados
```

Aqui ficam os PDFs separados por tipo de processo.

## Como usar no dia a dia

Fluxo manual recomendado:

1. Clique em `1. Baixar processos do SPED`.
2. Quando terminar, confira a pasta `Abrir downloads sped`.
3. Coloque os PDFs que devem ser rachurados na pasta `Abrir entrada rachurador`.
4. Clique em `2. Rachurar PDFs`.
5. Coloque os PDFs rachurados na pasta `Abrir entrada separador pdf`, se necessario.
6. Clique em `3. Separar PDFs`.
7. Confira `Abrir pasta processos separados`.
8. Clique em `4. Postar no site`.

Fluxo automatico:

1. Clique em `Executar ciclo completo`.
2. Acompanhe o texto na area de log.
3. Se alguma etapa der erro, o ciclo para nessa etapa para evitar continuar com arquivos errados.

## Botao Enviar ENTER

Alguns robos podem esperar que voce aperte `ENTER`.

Quando um robo esta rodando, o botao `Enviar ENTER` fica liberado. Ele envia um ENTER para o robo como se voce tivesse apertado ENTER no terminal.

Exemplo comum: o `robo_sped` pode pedir ENTER depois que voce fizer login e entrar na tela certa.

## Botao Parar robo

O botao `Parar robo` tenta interromper o robo atual como um `Ctrl+C`.

No Windows, ele tenta primeiro enviar uma interrupcao ao processo. Se o robo nao parar em alguns segundos, o app encerra a arvore de processos.

Use esse botao quando:

- o robo travou;
- voce clicou no robo errado;
- o site parou de responder;
- voce precisa interromper tudo antes de continuar.

## Area de acompanhamento

A area escura da direita mostra as mensagens do robo em tempo real.

Ela mostra:

- hora de cada mensagem;
- qual robo iniciou;
- pasta de trabalho usada;
- mensagens do proprio robo;
- codigo final quando o robo termina.

Codigo final `0` normalmente significa que a etapa terminou sem erro.

Codigo diferente de `0` normalmente significa que a etapa terminou com erro ou foi interrompida.

## O que acontece se tentar rodar dois robos ao mesmo tempo

O app nao deixa.

Enquanto um robo esta rodando:

- os botoes de execucao ficam bloqueados;
- `Enviar ENTER` fica liberado;
- `Parar robo` fica liberado.

Quando o robo termina, os botoes voltam ao normal.

## O que acontece ao fechar o app com robo rodando

Se voce tentar fechar a janela enquanto um robo esta rodando, o app pergunta se voce quer fechar e parar o robo.

Se voce confirmar, ele tenta interromper o processo antes de fechar.

## Resumo rapido

Use o app para:

- executar cada robo sem terminal;
- acompanhar o andamento;
- enviar ENTER quando um robo pedir;
- parar um robo travado;
- abrir as pastas certas sem procurar no Windows.

