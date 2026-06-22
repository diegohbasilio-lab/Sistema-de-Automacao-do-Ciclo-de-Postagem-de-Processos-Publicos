# Tutorial tecnico do app_ciclo_postagem.py

Este documento explica o funcionamento tecnico do arquivo:

```text
C:\Users\salcaux05\Desktop\Ciclo de postagem\app_ciclo_postagem.py
```

O objetivo e ajudar voce a entender o codigo do aplicativo `Ciclo de Postagem`.

## Visao geral

O `app_ciclo_postagem.py` cria uma interface grafica com `tkinter`.

Ele nao substitui os robos. Ele funciona como um painel de controle que:

1. mostra botoes para executar os scripts;
2. abre pastas importantes;
3. mostra a saida dos robos em tempo real;
4. envia ENTER para o robo atual;
5. para o robo atual quando necessario;
6. executa o ciclo completo em sequencia.

## Bibliotecas usadas

| Linha / biblioteca | O que faz |
|---|---|
| `import os` | Usa recursos do sistema, como abrir pastas e detectar Windows. |
| `import signal` | Envia sinal de interrupcao para parar robos. |
| `import subprocess` | Abre outro programa/script Python por dentro do app. |
| `import sys` | Importado para recursos do Python, embora hoje quase nao seja usado diretamente. |
| `import threading` | Roda leitura de saida e parada de processo em segundo plano. |
| `import queue` | Cria fila segura para mandar mensagens da thread para a tela. |
| `from datetime import datetime` | Gera horario mostrado no log. |
| `from pathlib import Path` | Monta caminhos de arquivos e pastas. |
| `import tkinter as tk` | Biblioteca principal da interface grafica. |
| `from tkinter import messagebox, ttk` | Usa caixas de mensagem e componentes visuais mais modernos. |

## Constantes de caminho

Logo no inicio:

```python
ROOT = Path(__file__).resolve().parent
ROBO_SPED_DIR = ROOT / "robo_sped"
RACHURADOR_DIR = ROBO_SPED_DIR / "rachurador_pdf"
SEPARADOR_DIR = ROOT / "separador-postagem"
```

`ROOT`

Representa a pasta onde o `app_ciclo_postagem.py` esta salvo.

`ROBO_SPED_DIR`

Aponta para a pasta do robo do SPED.

`RACHURADOR_DIR`

Aponta para a pasta do rachurador, que fica dentro de `robo_sped`.

`SEPARADOR_DIR`

Aponta para a pasta `separador-postagem`.

Esses caminhos sao a base de quase todo o app.

## Dicionario `SCRIPTS`

`SCRIPTS` guarda as quatro etapas executaveis pelo app.

Cada item tem:

- `titulo`: texto mostrado no botao e no log;
- `arquivo`: caminho do script Python;
- `pasta`: pasta de trabalho usada ao executar;
- `descricao`: texto curto mostrado na interface.

Entradas atuais:

| Chave | Script executado | Funcao |
|---|---|---|
| `robo_sped` | `robo_sped.py` | Baixa processos do SPED. |
| `rachurador` | `rachurar_pdfs.py` | Rachura dados sensiveis dos PDFs. |
| `separador` | `separador_pdf.py` | Separa PDFs por tipo de processo. |
| `postador` | `postar.py` | Posta PDFs no site de licitacoes. |

Quando voce clica em um botao, o app usa essa chave para saber qual arquivo abrir.

## Lista `FOLDERS`

`FOLDERS` guarda os botoes de abrir pasta.

Cada item tem:

```python
("Texto do botao", caminho_da_pasta)
```

O app percorre essa lista e cria um botao para cada pasta.

Se a pasta nao existir, o metodo `_abrir_pasta` cria a pasta antes de abrir.

## Classe `CicloPostagemApp`

```python
class CicloPostagemApp(tk.Tk):
```

Essa classe representa a janela principal.

Ela herda de `tk.Tk`, que e a janela base do `tkinter`.

## Metodo `__init__`

Executa quando o app inicia.

Ele faz:

1. chama `super().__init__()` para iniciar a janela;
2. define titulo da janela;
3. define tamanho inicial `980x680`;
4. define tamanho minimo `860x560`;
5. cria `log_queue`, a fila de mensagens;
6. define `processo_atual` como `None`;
7. define `nome_processo_atual` como `None`;
8. cria `fila_execucao`, usada no ciclo completo;
9. cria `botoes_execucao`, lista de botoes que serao bloqueados enquanto um robo roda;
10. chama `_configurar_estilo`;
11. chama `_montar_tela`;
12. agenda `_atualizar_log` para rodar a cada 150 ms;
13. configura o fechamento da janela para passar por `_ao_fechar`.

## Metodo `_configurar_estilo`

Define o visual dos componentes `ttk`.

Ele configura:

- fundo geral;
- fonte do titulo;
- fonte do subtitulo;
- estilo dos botoes;
- estilo da barra de status.

Esse metodo nao executa robos. Ele so cuida da aparencia.

## Metodo `_montar_tela`

Monta a interface inteira.

Fluxo principal:

1. cria o frame principal com margem;
2. cria o topo com titulo e subtitulo;
3. cria o corpo com duas colunas;
4. cria a coluna esquerda com rolagem;
5. cria a coluna direita com status, botoes e log;
6. chama `_montar_painel_robos`;
7. chama `_montar_painel_pastas`;
8. registra a primeira mensagem no log.

## Rolagem da coluna esquerda

A parte esquerda usa:

- `tk.Canvas`;
- `ttk.Scrollbar`;
- um `Frame` dentro do canvas.

Funcoes internas:

| Funcao interna | O que faz |
|---|---|
| `atualizar_rolagem` | Atualiza a area rolavel conforme o conteudo cresce. |
| `ajustar_largura` | Faz o frame interno acompanhar a largura do canvas. |
| `rolar_esquerda` | Move a rolagem com a roda do mouse. |
| `ativar_rolagem_esquerda` | Liga a roda do mouse quando o mouse entra na parte esquerda. |
| `desativar_rolagem_esquerda` | Desliga a roda do mouse quando o mouse sai da parte esquerda. |

Essa foi a correcao para a rolagem funcionar na area esquerda inteira, nao apenas em cima da barra.

## Metodo `_montar_painel_robos`

Cria a secao `Robos`.

Primeiro cria o botao:

```python
Executar ciclo completo
```

Depois percorre o dicionario `SCRIPTS` e cria um botao para cada robo.

Cada botao chama:

```python
self._executar_script(c)
```

Onde `c` e a chave do robo, por exemplo `postador`.

Cada botao criado e adicionado em `self.botoes_execucao`. Isso permite bloquear todos eles enquanto algum robo esta rodando.

## Metodo `_montar_painel_pastas`

Cria a secao `Pastas`.

Ele percorre `FOLDERS` e cria um botao para cada pasta.

Cada botao chama:

```python
self._abrir_pasta(p)
```

## Metodo `_executar_ciclo_completo`

Inicia a sequencia completa.

Primeiro verifica se ja existe robo rodando. Se existir, mostra aviso e nao inicia outro.

Depois monta:

```python
self.fila_execucao = ["robo_sped", "rachurador", "separador", "postador"]
```

Em seguida registra mensagem no log e chama `_executar_proxima_etapa`.

## Metodo `_executar_proxima_etapa`

Controla a fila do ciclo completo.

Se a fila estiver vazia:

- registra que o ciclo terminou;
- para.

Se ainda houver etapa:

1. remove a primeira chave da fila com `pop(0)`;
2. chama `_executar_script(proxima, pela_fila=True)`.

## Metodo `_executar_script`

Esse e o metodo central de execucao.

Ele recebe:

```python
chave
pela_fila=False
```

`chave`

Indica qual robo executar.

`pela_fila`

Indica se a chamada veio do ciclo completo.

Fluxo:

1. verifica se ja existe processo rodando;
2. se nao veio da fila, limpa `fila_execucao`;
3. busca os dados em `SCRIPTS[chave]`;
4. verifica se o arquivo existe;
5. cria a pasta de trabalho, se precisar;
6. monta o ambiente com `_ambiente_para`;
7. monta o comando com `_comando_para`;
8. escreve cabecalho no log;
9. chama `subprocess.Popen` para iniciar o robo;
10. guarda o processo em `self.processo_atual`;
11. guarda o nome em `self.nome_processo_atual`;
12. chama `_marcar_rodando(True)`;
13. cria uma thread para `_ler_saida_processo`.

O `subprocess.Popen` usa:

- `cwd`: pasta de trabalho do robo;
- `stdout=subprocess.PIPE`: captura o texto que o robo escreve;
- `stderr=subprocess.STDOUT`: junta erros na mesma saida;
- `stdin=subprocess.PIPE`: permite enviar ENTER;
- `text=True`: trata saida como texto;
- `encoding="utf-8"`: usa UTF-8;
- `errors="replace"`: evita quebrar por caractere invalido;
- `creationflags`: no Windows, cria novo grupo de processo e sem janela extra.

## Metodo `_comando_para`

Monta o comando usado para executar o script.

No Windows, ele retorna uma chamada para `powershell.exe`.

O comando tenta nesta ordem:

1. `python`;
2. `py -3`;
3. `venv\Scripts\python.exe` dentro da pasta do script;
4. `venv\Scripts\python.exe` na pasta pai;
5. `robo_sped\venv\Scripts\python.exe`;
6. se nada existir, mostra erro `Python nao encontrado`.

Ele tambem limpa:

```powershell
$env:PYTHONPATH=''
```

Isso evita que uma pasta errada de dependencias atrapalhe a execucao.

Em sistemas que nao sao Windows, retorna:

```python
["python", "-u", str(arquivo)]
```

## Metodo `_ambiente_para`

Cria o ambiente de execucao para o robo.

Ele:

1. copia as variaveis atuais do Windows;
2. define `PYTHONUNBUFFERED=1`;
3. define `PYTHONIOENCODING=utf-8`;
4. remove `PYTHONPATH`, se existir.

`PYTHONUNBUFFERED=1` ajuda o log aparecer em tempo real.

## Metodo `_ler_saida_processo`

Roda em uma thread separada.

Ele le cada linha que o robo escreve e coloca na fila:

```python
self.log_queue.put(("log", linha))
```

Quando o processo termina, coloca:

```python
self.log_queue.put(("fim", titulo, codigo))
```

Isso e necessario porque o `tkinter` nao deve ser atualizado diretamente por thread secundaria.

## Metodo `_atualizar_log`

Roda a cada 150 ms.

Ele pega eventos de `self.log_queue`.

Se o evento for `log`:

- chama `_registrar_log`.

Se o evento for `fim`:

1. mostra codigo final;
2. limpa `processo_atual`;
3. limpa `nome_processo_atual`;
4. se houver fila e codigo for `0`, inicia a proxima etapa;
5. se houver fila e codigo nao for `0`, interrompe o ciclo;
6. se nao houver fila, libera os botoes.

No fim, ele agenda ele mesmo novamente:

```python
self.after(150, self._atualizar_log)
```

## Metodo `_registrar_log`

Escreve texto na area de acompanhamento.

Ele:

1. pega o horario atual;
2. insere a mensagem no `Text`;
3. rola ate o final com `see(tk.END)`.

Formato:

```text
[HH:MM:SS] mensagem
```

## Metodo `_marcar_rodando`

Ativa ou desativa botoes conforme o estado.

Quando `rodando=True`:

- bloqueia botoes dos robos;
- libera `Enviar ENTER`;
- libera `Parar robo`;
- muda o status para `Rodando: nome`.

Quando `rodando=False`:

- libera botoes dos robos;
- bloqueia `Enviar ENTER`;
- bloqueia `Parar robo`;
- muda o status para `Pronto para iniciar`.

## Metodo `_enviar_enter`

Envia uma quebra de linha para o processo atual.

Isso equivale a apertar ENTER no terminal.

Fluxo:

1. verifica se existe processo rodando;
2. escreve `\n` no `stdin`;
3. chama `flush`;
4. registra no log.

Se falhar, registra erro.

## Metodo `_parar_processo`

Acionado pelo botao `Parar robo`.

Ele:

1. verifica se existe processo rodando;
2. pergunta confirmacao;
3. limpa a fila do ciclo completo;
4. desativa o botao de parar;
5. registra aviso no log;
6. inicia uma thread para `_interromper_processo`.

## Metodo `_interromper_processo`

Tenta parar o robo de verdade.

No Windows:

1. tenta enviar `CTRL_BREAK_EVENT`;
2. aguarda ate 8 segundos;
3. se nao parar, executa `taskkill /PID ... /T /F`;
4. `/T` encerra tambem processos filhos;
5. `/F` forca encerramento.

Fora do Windows:

1. envia `SIGINT`;
2. aguarda ate 8 segundos;
3. se nao parar, usa `kill`.

Esse metodo roda fora da thread principal para a interface nao congelar.

## Metodo `_abrir_pasta`

Abre uma pasta no Explorador de Arquivos.

Ele:

1. cria a pasta se ela nao existir;
2. chama `os.startfile`;
3. registra no log que abriu.

Se der erro, mostra caixa de mensagem.

## Metodo `_ao_fechar`

Controla o fechamento da janela.

Se nao houver robo rodando:

- fecha normalmente.

Se houver robo rodando:

1. pergunta se voce quer fechar e parar o robo;
2. se responder nao, cancela o fechamento;
3. se responder sim, limpa a fila;
4. chama `_interromper_processo`;
5. fecha a janela.

## Bloco final

No fim do arquivo:

```python
if __name__ == "__main__":
    app = CicloPostagemApp()
    app.mainloop()
```

Isso significa:

1. se o arquivo foi executado diretamente, cria a janela;
2. `mainloop()` mantem a janela aberta e respondendo a cliques.

## Fluxo completo do app

Quando voce clica em um robo:

1. o botao chama `_executar_script`;
2. `_executar_script` localiza arquivo e pasta;
3. `_comando_para` monta o comando Python;
4. `_ambiente_para` prepara variaveis de ambiente;
5. `subprocess.Popen` inicia o robo;
6. `_ler_saida_processo` acompanha a saida;
7. `_atualizar_log` joga as mensagens na tela;
8. quando termina, o app libera os botoes;
9. se for ciclo completo e codigo for `0`, chama a proxima etapa.

## Como adicionar outro robo

Para adicionar outro robo, altere `SCRIPTS`.

Modelo:

```python
"nova_chave": {
    "titulo": "5. Nome do novo robo",
    "arquivo": ROOT / "pasta" / "novo_robo.py",
    "pasta": ROOT / "pasta",
    "descricao": "Descricao curta do que ele faz.",
},
```

Se quiser que ele entre no ciclo completo, tambem adicione a chave em:

```python
self.fila_execucao = [...]
```

## Como adicionar outra pasta

Para adicionar botao de pasta, altere `FOLDERS`.

Modelo:

```python
("Texto do botao", ROOT / "minha_pasta")
```

O app cria o botao automaticamente.

## Pontos importantes

- O app nao faz a logica dos robos; ele apenas executa os scripts.
- Cada robo continua tendo suas proprias regras.
- O app impede dois robos ao mesmo tempo.
- O ciclo completo para se uma etapa terminar com erro.
- O botao `Parar robo` tenta simular Ctrl+C e, se nao funcionar, mata o processo.
- A fila `log_queue` existe para evitar travamento da interface.

