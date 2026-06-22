import os
import signal
import subprocess
import sys
import threading
import queue
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parent
ROBO_SPED_DIR = ROOT / "robo_sped"
RACHURADOR_DIR = ROBO_SPED_DIR / "rachurador_pdf"
SEPARADOR_DIR = ROOT / "separador-postagem"


SCRIPTS = {
    "robo_sped": {
        "titulo": "1. Baixar processos do SPED",
        "arquivo": ROBO_SPED_DIR / "robo_sped.py",
        "pasta": ROBO_SPED_DIR,
        "descricao": "Baixa os processos novos e organiza os PDFs do SPED.",
    },
    "rachurador": {
        "titulo": "2. Rachurar PDFs",
        "arquivo": RACHURADOR_DIR / "rachurar_pdfs.py",
        "pasta": RACHURADOR_DIR,
        "descricao": "Rachura CPF, CNPJ e dados sensiveis dos PDFs colocados na entrada.",
    },
    "separador": {
        "titulo": "3. Separar PDFs",
        "arquivo": SEPARADOR_DIR / "separador_pdf.py",
        "pasta": SEPARADOR_DIR,
        "descricao": "Separa os PDFs rachurados nas pastas usadas pelo postador.",
    },
    "postador": {
        "titulo": "4. Postar no site",
        "arquivo": SEPARADOR_DIR / "postar.py",
        "pasta": SEPARADOR_DIR,
        "descricao": "Posta os PDFs pendentes no site de licitacoes.",
    },
}


FOLDERS = [
    ("Pasta geral do ciclo", ROOT),
    ("Abrir downloads sped", ROBO_SPED_DIR / "Downloads"),
    ("SPED - sem nota de empenho", ROBO_SPED_DIR / "SEM_NOTA_DE_EMPENHO"),
    ("SPED - pulados", ROBO_SPED_DIR / "PULADOS"),
    ("Abrir entrada rachurador", RACHURADOR_DIR / "entrada"),
    ("Abrir saida rachurador", RACHURADOR_DIR / "saida"),
    ("Abrir entrada separador pdf", SEPARADOR_DIR / "entrada"),
    ("Abrir pasta processos separados", SEPARADOR_DIR / "processos_separados"),
]


class CicloPostagemApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ciclo de Postagem")
        self.geometry("980x680")
        self.minsize(860, 560)

        self.log_queue = queue.Queue()
        self.processo_atual = None
        self.nome_processo_atual = None
        self.fila_execucao = []
        self.botoes_execucao = []

        self._configurar_estilo()
        self._montar_tela()
        self.after(150, self._atualizar_log)
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _configurar_estilo(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("Titulo.TLabel", background="#f4f6f8", foreground="#1f2937", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitulo.TLabel", background="#f4f6f8", foreground="#4b5563", font=("Segoe UI", 10))
        style.configure("Card.TLabelframe", background="#f4f6f8", foreground="#111827")
        style.configure("Card.TLabelframe.Label", background="#f4f6f8", foreground="#111827", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7))
        style.configure("Acao.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 8))
        style.configure("Perigo.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 8))
        style.configure("Status.TLabel", background="#e5e7eb", foreground="#111827", font=("Segoe UI", 10), padding=(10, 6))

    def _montar_tela(self):
        principal = ttk.Frame(self, padding=16)
        principal.pack(fill=tk.BOTH, expand=True)

        topo = ttk.Frame(principal)
        topo.pack(fill=tk.X)

        ttk.Label(topo, text="Ciclo de Postagem", style="Titulo.TLabel").pack(anchor=tk.W)
        ttk.Label(
            topo,
            text="Execute cada etapa e abra as pastas de trabalho sem precisar usar o terminal.",
            style="Subtitulo.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        corpo = ttk.Frame(principal)
        corpo.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        corpo.columnconfigure(0, weight=0)
        corpo.columnconfigure(1, weight=1)
        corpo.rowconfigure(0, weight=1)

        esquerda_container = ttk.Frame(corpo)
        esquerda_container.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        esquerda_container.rowconfigure(0, weight=1)
        esquerda_container.columnconfigure(0, weight=1)

        canvas_esquerda = tk.Canvas(
            esquerda_container,
            width=310,
            bg="#f4f6f8",
            highlightthickness=0,
            bd=0,
        )
        canvas_esquerda.grid(row=0, column=0, sticky="ns")

        rolagem_esquerda = ttk.Scrollbar(esquerda_container, orient=tk.VERTICAL, command=canvas_esquerda.yview)
        rolagem_esquerda.grid(row=0, column=1, sticky="ns")
        canvas_esquerda.configure(yscrollcommand=rolagem_esquerda.set)

        esquerda = ttk.Frame(canvas_esquerda)
        janela_esquerda = canvas_esquerda.create_window((0, 0), window=esquerda, anchor=tk.NW)

        def atualizar_rolagem(_evento=None):
            canvas_esquerda.configure(scrollregion=canvas_esquerda.bbox("all"))

        def ajustar_largura(evento):
            canvas_esquerda.itemconfigure(janela_esquerda, width=evento.width)

        def rolar_esquerda(evento):
            canvas_esquerda.yview_scroll(int(-1 * (evento.delta / 120)), "units")

        def ativar_rolagem_esquerda(_evento=None):
            self.bind_all("<MouseWheel>", rolar_esquerda)

        def desativar_rolagem_esquerda(_evento=None):
            self.unbind_all("<MouseWheel>")

        esquerda.bind("<Configure>", atualizar_rolagem)
        canvas_esquerda.bind("<Configure>", ajustar_largura)
        esquerda_container.bind("<Enter>", ativar_rolagem_esquerda)
        esquerda_container.bind("<Leave>", desativar_rolagem_esquerda)
        canvas_esquerda.bind("<Enter>", ativar_rolagem_esquerda)
        esquerda.bind("<Enter>", ativar_rolagem_esquerda)

        self._montar_painel_robos(esquerda)
        self._montar_painel_pastas(esquerda)

        direita = ttk.Frame(corpo)
        direita.grid(row=0, column=1, sticky="nsew")
        direita.rowconfigure(1, weight=1)
        direita.columnconfigure(0, weight=1)

        barra = ttk.Frame(direita)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        barra.columnconfigure(0, weight=1)

        self.status = ttk.Label(barra, text="Pronto para iniciar.", style="Status.TLabel")
        self.status.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.botao_enter = ttk.Button(barra, text="Enviar ENTER", command=self._enviar_enter, state=tk.DISABLED)
        self.botao_enter.grid(row=0, column=1, padx=(0, 8))

        self.botao_parar = ttk.Button(barra, text="Parar robo", command=self._parar_processo, state=tk.DISABLED)
        self.botao_parar.grid(row=0, column=2)

        quadro_log = ttk.LabelFrame(direita, text="Acompanhamento")
        quadro_log.grid(row=1, column=0, sticky="nsew")
        quadro_log.rowconfigure(0, weight=1)
        quadro_log.columnconfigure(0, weight=1)

        self.log = tk.Text(
            quadro_log,
            wrap=tk.WORD,
            height=20,
            bg="#0f172a",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief=tk.FLAT,
            font=("Consolas", 10),
        )
        self.log.grid(row=0, column=0, sticky="nsew")

        rolagem = ttk.Scrollbar(quadro_log, command=self.log.yview)
        rolagem.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=rolagem.set)

        self._registrar_log("Aplicacao aberta. Escolha uma etapa para executar.")

    def _montar_painel_robos(self, pai):
        painel = ttk.LabelFrame(pai, text="Robos")
        painel.pack(fill=tk.X)

        bloco_ciclo = ttk.Frame(painel, padding=(8, 8))
        bloco_ciclo.pack(fill=tk.X)

        botao_ciclo = ttk.Button(
            bloco_ciclo,
            text="Executar ciclo completo",
            style="Acao.TButton",
            command=self._executar_ciclo_completo,
        )
        botao_ciclo.pack(fill=tk.X)
        self.botoes_execucao.append(botao_ciclo)

        ttk.Label(
            bloco_ciclo,
            text="Roda as quatro etapas em sequencia, uma depois da outra.",
            style="Subtitulo.TLabel",
            wraplength=285,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

        for chave, dados in SCRIPTS.items():
            bloco = ttk.Frame(painel, padding=(8, 8))
            bloco.pack(fill=tk.X)

            botao = ttk.Button(
                bloco,
                text=dados["titulo"],
                style="Acao.TButton",
                command=lambda c=chave: self._executar_script(c),
            )
            botao.pack(fill=tk.X)
            self.botoes_execucao.append(botao)

            ttk.Label(
                bloco,
                text=dados["descricao"],
                style="Subtitulo.TLabel",
                wraplength=285,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(4, 0))

    def _montar_painel_pastas(self, pai):
        painel = ttk.LabelFrame(pai, text="Pastas")
        painel.pack(fill=tk.X, pady=(14, 0))

        for texto, caminho in FOLDERS:
            ttk.Button(
                painel,
                text=texto,
                command=lambda p=caminho: self._abrir_pasta(p),
            ).pack(fill=tk.X, padx=8, pady=4)

    def _executar_ciclo_completo(self):
        if self.processo_atual and self.processo_atual.poll() is None:
            messagebox.showinfo("Robo em execucao", "Ja existe um robo rodando. Aguarde terminar ou pare o processo atual.")
            return

        self.fila_execucao = ["robo_sped", "rachurador", "separador", "postador"]
        self._registrar_log("")
        self._registrar_log("[CICLO] Ciclo completo iniciado.")
        self._executar_proxima_etapa()

    def _executar_proxima_etapa(self):
        if not self.fila_execucao:
            self._registrar_log("[CICLO] Ciclo completo finalizado.")
            return
        proxima = self.fila_execucao.pop(0)
        self._executar_script(proxima, pela_fila=True)

    def _executar_script(self, chave, pela_fila=False):
        if self.processo_atual and self.processo_atual.poll() is None:
            messagebox.showinfo("Robo em execucao", "Ja existe um robo rodando. Aguarde terminar ou pare o processo atual.")
            return

        if not pela_fila:
            self.fila_execucao = []

        dados = SCRIPTS[chave]
        arquivo = dados["arquivo"]
        pasta = dados["pasta"]

        if not arquivo.exists():
            messagebox.showerror("Arquivo nao encontrado", f"Nao encontrei o arquivo:\n{arquivo}")
            return

        pasta.mkdir(parents=True, exist_ok=True)
        ambiente = self._ambiente_para(pasta)
        comando = self._comando_para(arquivo)

        self._registrar_log("")
        self._registrar_log("=" * 70)
        self._registrar_log(f"Iniciando: {dados['titulo']}")
        self._registrar_log(f"Pasta de trabalho: {pasta}")
        self._registrar_log("=" * 70)

        try:
            self.processo_atual = subprocess.Popen(
                comando,
                cwd=str(pasta),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=ambiente,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )
        except Exception as erro:
            self.processo_atual = None
            messagebox.showerror("Nao consegui iniciar", str(erro))
            self._registrar_log(f"[ERRO] Nao consegui iniciar: {erro}")
            return

        self.nome_processo_atual = dados["titulo"]
        self._marcar_rodando(True)

        thread = threading.Thread(target=self._ler_saida_processo, args=(self.processo_atual, dados["titulo"]), daemon=True)
        thread.start()

    def _comando_para(self, arquivo):
        if os.name == "nt":
            script = str(arquivo).replace("'", "''")
            venv_python = str((arquivo.parent / "venv" / "Scripts" / "python.exe")).replace("'", "''")
            venv_python_pai = str((arquivo.parent.parent / "venv" / "Scripts" / "python.exe")).replace("'", "''")
            venv_python_sped = str((ROBO_SPED_DIR / "venv" / "Scripts" / "python.exe")).replace("'", "''")
            comando = (
                "$env:PYTHONPATH=''; "
                "if (Get-Command python -ErrorAction SilentlyContinue) { "
                f"& python -u '{script}'; exit $LASTEXITCODE "
                "} "
                "elseif (Get-Command py -ErrorAction SilentlyContinue) { "
                f"& py -3 -u '{script}'; exit $LASTEXITCODE "
                "} "
                f"elseif (Test-Path '{venv_python}') {{ "
                f"& '{venv_python}' -u '{script}'; exit $LASTEXITCODE "
                "} "
                f"elseif (Test-Path '{venv_python_pai}') {{ "
                f"& '{venv_python_pai}' -u '{script}'; exit $LASTEXITCODE "
                "} "
                f"elseif (Test-Path '{venv_python_sped}') {{ "
                f"& '{venv_python_sped}' -u '{script}'; exit $LASTEXITCODE "
                "} "
                "else { Write-Error 'Python nao encontrado para executar este robo.'; exit 1 }"
            )
            return [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                comando,
            ]
        return ["python", "-u", str(arquivo)]

    def _ambiente_para(self, pasta):
        ambiente = os.environ.copy()
        ambiente["PYTHONUNBUFFERED"] = "1"
        ambiente["PYTHONIOENCODING"] = "utf-8"
        ambiente.pop("PYTHONPATH", None)
        return ambiente

    def _ler_saida_processo(self, processo, titulo):
        try:
            if processo.stdout:
                for linha in processo.stdout:
                    self.log_queue.put(("log", linha.rstrip("\n")))
            codigo = processo.wait()
            self.log_queue.put(("fim", titulo, codigo))
        except Exception as erro:
            self.log_queue.put(("log", f"[ERRO] Falha ao acompanhar o robo: {erro}"))
            self.log_queue.put(("fim", titulo, -1))

    def _atualizar_log(self):
        while True:
            try:
                evento = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if evento[0] == "log":
                self._registrar_log(evento[1])
            elif evento[0] == "fim":
                _, titulo, codigo = evento
                self._registrar_log("")
                self._registrar_log(f"[FIM] {titulo} terminou com codigo {codigo}.")
                self.processo_atual = None
                self.nome_processo_atual = None
                if self.fila_execucao and codigo == 0:
                    self._registrar_log("[CICLO] Iniciando proxima etapa automaticamente.")
                    self._executar_proxima_etapa()
                elif self.fila_execucao:
                    self._registrar_log("[CICLO] O ciclo foi interrompido porque uma etapa terminou com erro.")
                    self.fila_execucao = []
                    self._marcar_rodando(False)
                else:
                    self._marcar_rodando(False)

        self.after(150, self._atualizar_log)

    def _registrar_log(self, texto):
        horario = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{horario}] {texto}\n")
        self.log.see(tk.END)

    def _marcar_rodando(self, rodando):
        estado_execucao = tk.DISABLED if rodando else tk.NORMAL
        for botao in self.botoes_execucao:
            botao.configure(state=estado_execucao)

        self.botao_enter.configure(state=tk.NORMAL if rodando else tk.DISABLED)
        self.botao_parar.configure(state=tk.NORMAL if rodando else tk.DISABLED)

        if rodando:
            self.status.configure(text=f"Rodando: {self.nome_processo_atual}")
        else:
            self.status.configure(text="Pronto para iniciar.")

    def _enviar_enter(self):
        if not self.processo_atual or self.processo_atual.poll() is not None:
            return
        try:
            self.processo_atual.stdin.write("\n")
            self.processo_atual.stdin.flush()
            self._registrar_log("[INFO] ENTER enviado ao robo.")
        except Exception as erro:
            self._registrar_log(f"[ERRO] Nao consegui enviar ENTER: {erro}")

    def _parar_processo(self):
        if not self.processo_atual or self.processo_atual.poll() is not None:
            return

        confirmar = messagebox.askyesno("Parar robo", "Deseja parar o robo que esta rodando agora?")
        if not confirmar:
            return

        self.fila_execucao = []
        processo = self.processo_atual
        self.botao_parar.configure(state=tk.DISABLED)
        self._registrar_log("[AVISO] Enviando interrupcao ao robo, como Ctrl+C...")
        threading.Thread(target=self._interromper_processo, args=(processo,), daemon=True).start()

    def _interromper_processo(self, processo):
        if not processo or processo.poll() is not None:
            return

        try:
            if os.name == "nt":
                try:
                    os.kill(processo.pid, signal.CTRL_BREAK_EVENT)
                    self.log_queue.put(("log", "[INFO] Interrupcao enviada. Aguardando o robo encerrar..."))
                except Exception as erro:
                    self.log_queue.put(("log", f"[AVISO] Nao consegui enviar Ctrl+C/Ctrl+Break: {erro}"))

                try:
                    processo.wait(timeout=8)
                    return
                except subprocess.TimeoutExpired:
                    self.log_queue.put(("log", "[AVISO] O robo nao parou com a interrupcao. Encerrando a arvore do processo..."))
                    subprocess.run(
                        ["taskkill", "/PID", str(processo.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
            else:
                processo.send_signal(signal.SIGINT)
                try:
                    processo.wait(timeout=8)
                    return
                except subprocess.TimeoutExpired:
                    processo.kill()
        except Exception as erro:
            self.log_queue.put(("log", f"[ERRO] Nao consegui parar o robo: {erro}"))

    def _abrir_pasta(self, caminho):
        caminho.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(caminho))
            self._registrar_log(f"Pasta aberta: {caminho}")
        except Exception as erro:
            messagebox.showerror("Nao consegui abrir a pasta", str(erro))

    def _ao_fechar(self):
        if self.processo_atual and self.processo_atual.poll() is None:
            confirmar = messagebox.askyesno(
                "Robo em execucao",
                "Existe um robo rodando agora. Deseja fechar a aplicacao e parar esse robo?",
            )
            if not confirmar:
                return
            self.fila_execucao = []
            self._interromper_processo(self.processo_atual)
        self.destroy()


if __name__ == "__main__":
    app = CicloPostagemApp()
    app.mainloop()
