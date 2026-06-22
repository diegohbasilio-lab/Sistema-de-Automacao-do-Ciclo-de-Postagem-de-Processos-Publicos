# Tutorial simples do robo_sped

Este tutorial e para quem nunca teve contato com programacao.

## Para que serve

O `robo_sped` entra no sistema SPED, percorre os processos encaminhados e baixa os PDFs dos processos.

Depois de baixar cada PDF, ele analisa se existe Nota de Empenho dentro do arquivo.

Ele separa os arquivos assim:

- `Downloads`: processos em que o robo encontrou Nota de Empenho.
- `SEM_NOTA_DE_EMPENHO`: processos em que o robo nao encontrou Nota de Empenho.
- `PULADOS`: processos que falharam varias vezes e foram pulados.
- `TEMP`: pasta temporaria usada enquanto o robo analisa o PDF.

O robo tambem foi configurado para puxar somente processos de `2026`, quando o ano aparece na tela ou no documento.

## Onde fica o robo

O arquivo principal fica em:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\robo_sped.py`

Existe tambem um arquivo simples chamado:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped\codigo de start.txt`

Ele mostra o comando basico para iniciar:

```powershell
python robo_sped.py
```

## Atencao sobre as pastas de saida

No codigo atual, as pastas de saida estao configuradas para:

`C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped`

Ou seja: os PDFs baixados ficam dentro da propria pasta `robo_sped`, na pasta `Ciclo de postagem`.

## Como iniciar

1. Abra o PowerShell.
2. Entre na pasta do robo:

```powershell
cd "C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped"
```

3. Rode o robo:

```powershell
python robo_sped.py
```

Se o Windows nao reconhecer `python`, tente usar o Python do ambiente do robo:

```powershell
.\venv\Scripts\python.exe robo_sped.py
```

## O que fazer quando o navegador abrir

1. O robo abre o Chrome.
2. Faca login no SPED normalmente.
3. Va para a tela `Processos Encaminhados`.
4. Volte ao PowerShell.
5. Aperte `ENTER`.

A partir dai, o robo comeca a trabalhar sozinho.

## O que ele faz depois do ENTER

Para cada pagina da tabela de processos, ele:

1. Conta as linhas da tabela.
2. Verifica se o processo parece ser de `2026`.
3. Se for de outro ano, ignora.
4. Abre o processo.
5. Entra em `Documentos assinados`.
6. Pega o primeiro documento da lista.
7. Verifica se o documento parece ser de `2026`.
8. Verifica se esse PDF ja foi baixado antes.
9. Se ja existe em `Downloads`, ignora e nao baixa de novo.
10. Se ja existe em `SEM_NOTA_DE_EMPENHO`, baixa temporariamente so para conferir se agora tem NE.
11. Le o texto do PDF.
12. Procura Nota de Empenho.
13. Move o PDF para a pasta correta ou descarta o temporario.
14. Volta para a lista e passa para o proximo processo.

## Nova regra: quando o arquivo ja foi baixado

O SPED costuma mostrar primeiro os processos mais novos. Entao, quando o robo roda novamente, ele pode encontrar processos que ja baixou antes.

Agora ele funciona assim:

### Se o arquivo ja existe em `Downloads`

O robo entende que esse processo ja foi baixado com Nota de Empenho.

Nesse caso, ele:

- ignora o processo;
- nao baixa de novo;
- nao substitui o arquivo antigo.

Se tambem existir uma copia antiga em `SEM_NOTA_DE_EMPENHO`, ele apaga essa copia antiga, porque a versao correta ja esta em `Downloads`.

### Se o arquivo ja existe em `SEM_NOTA_DE_EMPENHO`

O robo entende que antes esse processo foi baixado, mas nao tinha Nota de Empenho.

Nesse caso, ele baixa de novo apenas para conferir.

Se continuar sem Nota de Empenho:

- descarta o download temporario;
- mantem o arquivo antigo;
- nao substitui nada.

Se agora tiver Nota de Empenho:

- salva o novo PDF em `Downloads`;
- remove o arquivo antigo de `SEM_NOTA_DE_EMPENHO`;
- conta como processo com Nota de Empenho.

## Como saber se deu certo

No final, o robo mostra um resumo parecido com:

```text
FINALIZADO
Total processado: ...
Processos com Nota de Empenho: ...
Processos sem Nota de Empenho: ...
Processos ignorados por ano diferente de 2026: ...
Processos ignorados por ja terem sido baixados: ...
Processos pulados apos falhas repetidas: ...
Erros: ...
```

## O que significa cada resultado

`Processos com Nota de Empenho`

O robo achou uma NE no PDF e colocou o arquivo na pasta `Downloads`.

`Processos sem Nota de Empenho`

O robo baixou o PDF, mas nao encontrou NE. O arquivo vai para `SEM_NOTA_DE_EMPENHO` para conferencia manual.

`Processos ignorados por ano diferente de 2026`

O robo viu que o processo/documento era de outro ano e nao baixou.

`Processos ignorados por ja terem sido baixados`

O robo viu que o arquivo ja estava em `Downloads`, ou que ja estava em `SEM_NOTA_DE_EMPENHO` e continuou sem Nota de Empenho. Nesse caso, ele nao substitui o arquivo antigo.

`Processos pulados apos falhas repetidas`

O robo tentou processar o mesmo PDF algumas vezes, nao conseguiu, registrou como `PULADO` e continuou.

## Quando o robo pula um processo

O limite atual e:

```text
3 tentativas por processo
```

Se falhar 3 vezes, ele cria um registro na pasta `PULADOS`.

Esse registro e um arquivo `.txt` com:

- nome iniciado por `PULADO`;
- pagina em que estava;
- numero do processo na pagina;
- motivo do erro;
- texto da linha, quando o robo consegue capturar.

## Cuidados importantes

Nao feche o navegador enquanto o robo estiver rodando.

Nao mexa na tela do SPED enquanto ele estiver processando, porque ele depende dos botoes e tabelas na posicao certa.

Se o robo parar pedindo ENTER no final, isso e normal: ele terminou e esta esperando voce fechar.

Se ele travar no login inicial, faca o login manualmente, va para `Processos Encaminhados` e aperte ENTER no PowerShell.

## Como mudar o ano

No arquivo `robo_sped.py`, existe esta linha:

```python
ANO_ALVO = "2026"
```

Para trocar o ano, altere o valor entre aspas. Exemplo:

```python
ANO_ALVO = "2027"
```

## Como mudar o numero de tentativas

No arquivo `robo_sped.py`, existe esta linha:

```python
MAX_TENTATIVAS_PROCESSO = 3
```

Para tentar mais vezes antes de pular, altere o numero. Exemplo:

```python
MAX_TENTATIVAS_PROCESSO = 5
```

## Resumo rapido

Use assim:

```powershell
cd "C:\Users\salcaux05\Desktop\Ciclo de postagem\robo_sped"
python robo_sped.py
```

Depois:

1. Faca login no SPED.
2. Va em `Processos Encaminhados`.
3. Aperte ENTER no PowerShell.
4. Espere o robo terminar.
