import argparse
import contextlib
import io
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import main as envelope

# ── Paleta ──────────────────────────────────────────────────────────────────────
BG         = "#0d0f14"
BG_CARD    = "#13161e"
BG_INPUT   = "#1a1d27"
BORDER     = "#252836"
ACCENT     = "#00e5ff"
ACCENT2    = "#7c3aed"
SUCCESS    = "#22c55e"
DANGER     = "#ef4444"
TEXT       = "#e2e8f0"
TEXT_DIM   = "#64748b"
TEXT_LABEL = "#94a3b8"

FONT_MONO   = ("Courier New", 10)
FONT_TITLE  = ("Courier New", 20, "bold")
FONT_TAB    = ("Courier New", 10, "bold")
FONT_LABEL  = ("Courier New", 10)
FONT_BTN    = ("Courier New", 10, "bold")
FONT_OUTPUT = ("Courier New", 10)


# ── Helpers ──────────────────────────────────────────────────────────────────────

def make_button(parent: tk.Widget, text: str, command, color: str = ACCENT,
                width: int = 16) -> tk.Button:
    """tk.Button estilizado com hover via bind."""
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=FONT_BTN,
        fg=color,
        bg=BG_CARD,
        activeforeground=BG,
        activebackground=color,
        relief="flat",
        bd=0,
        highlightthickness=2,
        highlightbackground=color,
        highlightcolor=color,
        cursor="hand2",
        width=width,
        pady=7,
    )
    btn.bind("<Enter>", lambda _: btn.config(bg=color, fg=BG))
    btn.bind("<Leave>", lambda _: btn.config(bg=BG_CARD, fg=color))
    return btn


def make_section(parent: tk.Widget, text: str, color: str = ACCENT) -> tk.Frame:
    """Label de secao com linha decorativa."""
    frame = tk.Frame(parent, bg=BG_CARD)
    tk.Label(frame, text=text, font=("Courier New", 9, "bold"),
             fg=color, bg=BG_CARD).pack(side="left", padx=(0, 8))
    tk.Frame(frame, bg=color, height=1).pack(side="left", fill="x", expand=True)
    return frame


def make_file_row(parent: tk.Widget, label: str, variable: tk.StringVar,
                  save: bool = False, pem: bool = False) -> tk.Frame:
    """Linha label + entry + botao de arquivo."""
    row = tk.Frame(parent, bg=BG_CARD)
    row.columnconfigure(1, weight=1)

    tk.Label(row, text=label, font=FONT_LABEL, fg=TEXT_LABEL,
             bg=BG_CARD, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 12))

    ef = tk.Frame(row, bg=BORDER, padx=1, pady=1)
    ef.grid(row=0, column=1, sticky="ew", padx=(0, 8))
    tk.Entry(ef, textvariable=variable, font=FONT_MONO,
             fg=ACCENT, bg=BG_INPUT, insertbackground=ACCENT,
             relief="flat", bd=0).pack(fill="x", ipady=6, ipadx=6)

    def pick():
        ft = ([("PEM", "*.pem"), ("Todos", "*.*")] if pem
              else [("Todos os arquivos", "*.*")])
        sel = (filedialog.asksaveasfilename(filetypes=ft) if save
               else filedialog.askopenfilename(filetypes=ft))
        if sel:
            if pem and not save and not sel.lower().endswith(".pem"):
                messagebox.showwarning(
                    "Extensao incomum",
                    f"'{Path(sel).name}' nao termina com .pem.\n"
                    "Verifique se este e o arquivo correto.",
                )
            variable.set(sel)

    btn_text = "salvar >" if save else "buscar >"
    make_button(row, btn_text, pick, color=ACCENT2, width=9).grid(
        row=0, column=2, sticky="e")

    return row


# ── App principal ────────────────────────────────────────────────────────────────

class EnvelopeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Envelope Digital Assinado")
        self.geometry("960x740")
        self.minsize(860, 640)
        self.configure(bg=BG)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_output()
        self._animate_cursor()

    # ── Header ───────────────────────────────────────────────────────────────────
    def _build_header(self) -> None:
        hdr = tk.Frame(self, bg=BG)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.columnconfigure(1, weight=1)

        tk.Label(hdr, text="[*]", font=("Courier New", 22, "bold"),
                 fg=ACCENT, bg=BG).grid(row=0, column=0, rowspan=2, padx=(0, 14))

        tk.Label(hdr, text="ENVELOPE DIGITAL ASSINADO",
                 font=FONT_TITLE, fg=TEXT, bg=BG,
                 anchor="w").grid(row=0, column=1, sticky="w")

        self._cursor_var = tk.StringVar(value="")
        sub = tk.Frame(hdr, bg=BG)
        sub.grid(row=1, column=1, sticky="w")
        tk.Label(sub, text="AES-128-CBC  *  RSA/PKCS1v15  *  SHA-512",
                 font=("Courier New", 9), fg=TEXT_DIM, bg=BG).pack(side="left")
        tk.Label(sub, textvariable=self._cursor_var,
                 font=("Courier New", 9), fg=ACCENT, bg=BG).pack(side="left")

        tk.Frame(self, bg=ACCENT, height=1).grid(
            row=0, column=0, sticky="sew", padx=20, pady=(72, 0))

    # ── Tabs ─────────────────────────────────────────────────────────────────────
    def _build_tabs(self) -> None:
        wrapper = tk.Frame(self, bg=BG)
        wrapper.grid(row=1, column=0, sticky="nsew", padx=20, pady=(12, 0))
        wrapper.columnconfigure(0, weight=1)
        wrapper.rowconfigure(1, weight=1)

        tab_bar = tk.Frame(wrapper, bg=BG)
        tab_bar.grid(row=0, column=0, sticky="ew")

        self._tab_frames: dict[str, tk.Frame] = {}
        self._tab_btns:   dict[str, tk.Label] = {}

        tabs = [
            ("keys",   "[ GERAR CHAVES ]"),
            ("create", "[ CRIAR ENVELOPE ]"),
            ("open",   "[ ABRIR ENVELOPE ]"),
        ]
        for key, label in tabs:
            frame = tk.Frame(wrapper, bg=BG_CARD, padx=20, pady=16)
            frame.grid(row=1, column=0, sticky="nsew")
            self._tab_frames[key] = frame

            lbl = tk.Label(tab_bar, text=label, font=FONT_TAB,
                           fg=TEXT_DIM, bg=BG, cursor="hand2", padx=14, pady=8)
            lbl.pack(side="left")
            self._tab_btns[key] = lbl
            lbl.bind("<Button-1>", lambda e, k=key: self._show_tab(k))

        self._build_keys_tab(self._tab_frames["keys"])
        self._build_create_tab(self._tab_frames["create"])
        self._build_open_tab(self._tab_frames["open"])
        self._show_tab("keys")

    def _show_tab(self, key: str) -> None:
        for k, f in self._tab_frames.items():
            f.grid_remove()
        for k, b in self._tab_btns.items():
            b.config(fg=ACCENT if k == key else TEXT_DIM,
                     bg=BG_CARD if k == key else BG)
        self._tab_frames[key].grid()

    # ── Aba: Gerar Chaves ─────────────────────────────────────────────────────────
    def _build_keys_tab(self, tab: tk.Frame) -> None:
        tab.columnconfigure(0, weight=1)

        make_section(tab, "CONFIGURACAO RSA", ACCENT).grid(
            row=0, column=0, sticky="ew", pady=(0, 12))

        size_row = tk.Frame(tab, bg=BG_CARD)
        size_row.grid(row=1, column=0, sticky="w", pady=4)
        tk.Label(size_row, text="Tamanho da chave", font=FONT_LABEL,
                 fg=TEXT_LABEL, bg=BG_CARD, anchor="w").pack(side="left", padx=(0, 12))

        self._size_var = tk.StringVar(value="2048")
        for val in ("1024", "2048"):
            rb = tk.Radiobutton(
                size_row, text=val + " bits", variable=self._size_var, value=val,
                font=FONT_LABEL, fg=TEXT, bg=BG_CARD, selectcolor=BG_INPUT,
                activebackground=BG_CARD, activeforeground=ACCENT,
                indicatoron=False, padx=10, pady=4,
                relief="flat", bd=0, cursor="hand2",
                highlightthickness=1, highlightbackground=BORDER,
            )
            rb.pack(side="left", padx=(0, 6))

        make_section(tab, "ARQUIVOS DE SAIDA", ACCENT2).grid(
            row=2, column=0, sticky="ew", pady=(18, 8))

        self._priv_var = tk.StringVar(value="privada.pem")
        self._pub_var  = tk.StringVar(value="publica.pem")
        make_file_row(tab, "Chave privada (.pem)", self._priv_var,
                      save=True, pem=True).grid(row=3, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Chave publica (.pem)", self._pub_var,
                      save=True, pem=True).grid(row=4, column=0, sticky="ew", pady=4)

        bf = tk.Frame(tab, bg=BG_CARD)
        bf.grid(row=5, column=0, sticky="e", pady=(20, 0))
        self._btn_keys = make_button(
            bf, "GERAR CHAVES",
            command=lambda: self._run_action(
                envelope.generate_keys,
                argparse.Namespace(
                    tamanho=int(self._size_var.get()),
                    privada=self._priv_var.get(),
                    publica=self._pub_var.get(),
                ),
                "Chaves geradas com sucesso.",
            ),
            color=ACCENT, width=16,
        )
        self._btn_keys.pack()

    # ── Aba: Criar Envelope ───────────────────────────────────────────────────────
    def _build_create_tab(self, tab: tk.Frame) -> None:
        tab.columnconfigure(0, weight=1)

        self._c_entrada     = tk.StringVar()
        self._c_pub_dest    = tk.StringVar()
        self._c_priv_rem    = tk.StringVar()
        self._c_saida_msg   = tk.StringVar(value="mensagem.cif")
        self._c_saida_chave = tk.StringVar(value="chave.env")
        self._c_saida_sig   = tk.StringVar(value="assinatura.sig")

        make_section(tab, "ARQUIVOS DE ENTRADA", ACCENT).grid(
            row=0, column=0, sticky="ew", pady=(0, 8))
        make_file_row(tab, "Mensagem em claro", self._c_entrada).grid(
            row=1, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Chave publica destinatario", self._c_pub_dest, pem=True).grid(
            row=2, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Chave privada remetente", self._c_priv_rem, pem=True).grid(
            row=3, column=0, sticky="ew", pady=4)

        make_section(tab, "ARQUIVOS DE SAIDA", ACCENT2).grid(
            row=4, column=0, sticky="ew", pady=(18, 8))
        make_file_row(tab, "Mensagem cifrada", self._c_saida_msg, save=True).grid(
            row=5, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Chave + IV cifrados", self._c_saida_chave, save=True).grid(
            row=6, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Assinatura digital", self._c_saida_sig, save=True).grid(
            row=7, column=0, sticky="ew", pady=4)

        bf = tk.Frame(tab, bg=BG_CARD)
        bf.grid(row=8, column=0, sticky="e", pady=(20, 0))
        self._btn_create = make_button(
            bf, "CRIAR ENVELOPE",
            command=lambda: self._run_action(
                envelope.create_envelope,
                argparse.Namespace(
                    entrada=self._c_entrada.get(),
                    pub_dest=self._c_pub_dest.get(),
                    priv_rem=self._c_priv_rem.get(),
                    saida_msg=self._c_saida_msg.get(),
                    saida_chave=self._c_saida_chave.get(),
                    saida_assinatura=self._c_saida_sig.get(),
                ),
                "Envelope criado com sucesso.",
            ),
            color=ACCENT, width=18,
        )
        self._btn_create.pack()

    # ── Aba: Abrir Envelope ───────────────────────────────────────────────────────
    def _build_open_tab(self, tab: tk.Frame) -> None:
        tab.columnconfigure(0, weight=1)

        self._o_msg        = tk.StringVar()
        self._o_chave      = tk.StringVar()
        self._o_assinatura = tk.StringVar()
        self._o_priv_dest  = tk.StringVar()
        self._o_pub_rem    = tk.StringVar()
        self._o_saida      = tk.StringVar(value="mensagem_aberta.txt")
        self._o_encoding   = tk.StringVar(value="utf-8")

        make_section(tab, "ARQUIVOS DE ENTRADA", ACCENT).grid(
            row=0, column=0, sticky="ew", pady=(0, 8))
        make_file_row(tab, "Mensagem cifrada", self._o_msg).grid(
            row=1, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Chave + IV cifrados", self._o_chave).grid(
            row=2, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Assinatura digital", self._o_assinatura).grid(
            row=3, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Chave privada destinatario", self._o_priv_dest, pem=True).grid(
            row=4, column=0, sticky="ew", pady=4)
        make_file_row(tab, "Chave publica remetente", self._o_pub_rem, pem=True).grid(
            row=5, column=0, sticky="ew", pady=4)

        make_section(tab, "SAIDA", ACCENT2).grid(
            row=6, column=0, sticky="ew", pady=(18, 8))
        make_file_row(tab, "Arquivo em claro", self._o_saida, save=True).grid(
            row=7, column=0, sticky="ew", pady=4)

        enc_row = tk.Frame(tab, bg=BG_CARD)
        enc_row.grid(row=8, column=0, sticky="w", pady=4)
        tk.Label(enc_row, text="Encoding exibicao", font=FONT_LABEL,
                 fg=TEXT_LABEL, bg=BG_CARD, anchor="w").pack(side="left", padx=(0, 12))
        ef = tk.Frame(enc_row, bg=BORDER, padx=1, pady=1)
        ef.pack(side="left")
        tk.Entry(ef, textvariable=self._o_encoding, font=FONT_MONO,
                 fg=ACCENT, bg=BG_INPUT, insertbackground=ACCENT,
                 relief="flat", bd=0, width=14).pack(ipady=6, ipadx=6)

        bottom = tk.Frame(tab, bg=BG_CARD)
        bottom.grid(row=9, column=0, sticky="ew", pady=(20, 0))
        bottom.columnconfigure(0, weight=1)

        self.signature_status_label = tk.Label(
            bottom, text="", font=("Courier New", 12, "bold"),
            fg=SUCCESS, bg=BG_CARD)
        self.signature_status_label.grid(row=0, column=0, sticky="w")

        self._btn_open = make_button(
            bottom, "ABRIR ENVELOPE",
            command=lambda: self._run_action(
                envelope.open_envelope,
                argparse.Namespace(
                    msg=self._o_msg.get(),
                    chave=self._o_chave.get(),
                    assinatura=self._o_assinatura.get(),
                    priv_dest=self._o_priv_dest.get(),
                    pub_rem=self._o_pub_rem.get(),
                    saida=self._o_saida.get(),
                    encoding=self._o_encoding.get(),
                ),
                "Envelope aberto com sucesso.",
            ),
            color=ACCENT, width=18,
        )
        self._btn_open.grid(row=0, column=1, sticky="e")

    # ── Output / Log ─────────────────────────────────────────────────────────────
    def _build_output(self) -> None:
        outer = tk.Frame(self, bg=BG, padx=20, pady=10)
        outer.grid(row=2, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        make_section(outer, "LOG", TEXT_DIM).grid(
            row=0, column=0, sticky="ew", pady=(0, 6))

        ob = tk.Frame(outer, bg=BORDER, padx=1, pady=1)
        ob.grid(row=1, column=0, sticky="nsew")
        ob.columnconfigure(0, weight=1)
        ob.rowconfigure(0, weight=1)

        self.output = tk.Text(
            ob, height=8, wrap="word",
            font=FONT_OUTPUT, fg=ACCENT, bg=BG,
            insertbackground=ACCENT, relief="flat",
            bd=0, state="disabled",
            selectbackground=ACCENT2, selectforeground=TEXT,
        )
        self.output.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        sb = ttk.Scrollbar(ob, orient="vertical", command=self.output.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=sb.set)

    # ── Cursor piscante ───────────────────────────────────────────────────────────
    def _animate_cursor(self) -> None:
        self._cursor_var.set("" if self._cursor_var.get() else " _")
        self.after(600, self._animate_cursor)

    # ── Logica de acao ────────────────────────────────────────────────────────────
    def _all_buttons(self) -> list:
        return [self._btn_keys, self._btn_create, self._btn_open]

    def _run_action(self, func, args: argparse.Namespace,
                    success_message: str) -> None:
        self.signature_status_label.config(text="")
        if not self._validate_required(args):
            return

        for btn in self._all_buttons():
            btn.config(state="disabled", bg=BG_CARD,
                       fg=TEXT_DIM, highlightbackground=TEXT_DIM)
        self.update_idletasks()

        result = None
        stdout = io.StringIO()
        exc_info = None

        try:
            with contextlib.redirect_stdout(stdout):
                result = func(args)
        except envelope.EnvelopeError as exc:
            exc_info = ("Erro", str(exc))
        except Exception as exc:
            exc_info = ("Erro Inesperado", str(exc))
        finally:
            for btn in self._all_buttons():
                btn.config(state="normal", bg=BG_CARD,
                           fg=ACCENT, highlightbackground=ACCENT)
            self._write_output(stdout.getvalue())

        if exc_info:
            messagebox.showerror(*exc_info)
            return

        if func is envelope.open_envelope:
            if result:
                self.signature_status_label.config(
                    text="[OK] ASSINATURA VALIDA", fg=SUCCESS)
                messagebox.showinfo("Sucesso",
                    "Envelope aberto com sucesso.\nAssinatura verificada e valida.")
            else:
                self.signature_status_label.config(
                    text="[!!] ASSINATURA INVALIDA", fg=DANGER)
                messagebox.showwarning(
                    "Assinatura Invalida",
                    "AVISO: A assinatura digital e INVALIDA.\n\n"
                    "O arquivo foi salvo, mas o conteudo pode ter sido\n"
                    "alterado ou nao vem do remetente esperado.",
                )
        else:
            messagebox.showinfo("Sucesso", success_message)

    def _validate_required(self, args: argparse.Namespace) -> bool:
        missing = [
            name.replace("_", "-")
            for name, value in vars(args).items()
            if isinstance(value, str) and not value.strip()
        ]
        if missing:
            messagebox.showwarning(
                "Campos obrigatorios",
                "Preencha os campos: " + ", ".join(missing),
            )
            return False
        return True

    def _write_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")


def run_gui() -> None:
    app = EnvelopeApp()
    app.mainloop()