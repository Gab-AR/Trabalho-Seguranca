import argparse
import contextlib
import io
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import main as envelope


class EnvelopeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Envelope Digital Assinado")
        self.geometry("900x640")
        self.minsize(820, 580)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self._build_keys_tab(notebook)
        self._build_create_tab(notebook)
        self._build_open_tab(notebook)

        output_frame = ttk.LabelFrame(self, text="Saida")
        output_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output = tk.Text(output_frame, height=9, wrap="word")
        self.output.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=8)
        self.output.configure(yscrollcommand=scrollbar.set)

    def _build_keys_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Gerar chaves")
        tab.columnconfigure(1, weight=1)

        size_var = tk.StringVar(value="2048")
        priv_var = tk.StringVar(value="privada.pem")
        pub_var = tk.StringVar(value="publica.pem")

        ttk.Label(tab, text="Tamanho RSA").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Combobox(
            tab,
            textvariable=size_var,
            values=("1024", "2048"),
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="w", pady=6)

        self._file_row(tab, 1, "Chave privada", priv_var, save=True, pem=True)
        self._file_row(tab, 2, "Chave publica", pub_var, save=True, pem=True)

        self.generate_keys_button = ttk.Button(
            tab,
            text="Gerar chaves",
            command=lambda: self._run_action(
                envelope.generate_keys,
                argparse.Namespace(
                    tamanho=int(size_var.get()),
                    privada=priv_var.get(),
                    publica=pub_var.get(),
                ),
                "Chaves geradas com sucesso.",
            ),
        )
        self.generate_keys_button.grid(row=3, column=1, sticky="e", pady=14)

    def _build_create_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Criar envelope")
        tab.columnconfigure(1, weight=1)

        entrada = tk.StringVar()
        pub_dest = tk.StringVar()
        priv_rem = tk.StringVar()
        saida_msg = tk.StringVar(value="mensagem.cif")
        saida_chave = tk.StringVar(value="chave.env")
        saida_assinatura = tk.StringVar(value="assinatura.sig")

        self._file_row(tab, 0, "Mensagem em claro", entrada)
        self._file_row(tab, 1, "Publica destinatario", pub_dest, pem=True)
        self._file_row(tab, 2, "Privada remetente", priv_rem, pem=True)
        self._file_row(tab, 3, "Saida mensagem", saida_msg, save=True)
        self._file_row(tab, 4, "Saida chave+IV", saida_chave, save=True)
        self._file_row(tab, 5, "Saida assinatura", saida_assinatura, save=True)

        self.create_envelope_button = ttk.Button(
            tab,
            text="Criar envelope",
            command=lambda: self._run_action(
                envelope.create_envelope,
                argparse.Namespace(
                    entrada=entrada.get(),
                    pub_dest=pub_dest.get(),
                    priv_rem=priv_rem.get(),
                    saida_msg=saida_msg.get(),
                    saida_chave=saida_chave.get(),
                    saida_assinatura=saida_assinatura.get(),
                ),
                "Envelope criado com sucesso.",
            ),
        )
        self.create_envelope_button.grid(row=6, column=1, sticky="e", pady=14)

    def _build_open_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Abrir envelope")
        tab.columnconfigure(1, weight=1)

        msg = tk.StringVar()
        chave = tk.StringVar()
        assinatura = tk.StringVar()
        priv_dest = tk.StringVar()
        pub_rem = tk.StringVar()
        saida = tk.StringVar(value="mensagem_aberta.txt")
        encoding = tk.StringVar(value="utf-8")

        self._file_row(tab, 0, "Mensagem cifrada", msg)
        self._file_row(tab, 1, "Chave+IV cifrados", chave)
        self._file_row(tab, 2, "Assinatura", assinatura)
        self._file_row(tab, 3, "Privada destinatario", priv_dest, pem=True)
        self._file_row(tab, 4, "Publica remetente", pub_rem, pem=True)
        self._file_row(tab, 5, "Saida texto claro", saida, save=True)

        ttk.Label(tab, text="Encoding exibicao").grid(row=6, column=0, sticky="w", pady=6)
        ttk.Entry(tab, textvariable=encoding).grid(row=6, column=1, sticky="ew", pady=6, padx=6)

        self.open_envelope_button = ttk.Button(
            tab,
            text="Abrir envelope",
            command=lambda: self._run_action(
                envelope.open_envelope,
                argparse.Namespace(
                    msg=msg.get(),
                    chave=chave.get(),
                    assinatura=assinatura.get(),
                    priv_dest=priv_dest.get(),
                    pub_rem=pub_rem.get(),
                    saida=saida.get(),
                    encoding=encoding.get(),
                ),
                "Envelope aberto com sucesso.",
            ),
        )
        self.open_envelope_button.grid(row=7, column=1, sticky="e", pady=14)

        status_frame = ttk.Frame(tab)
        status_frame.grid(row=8, column=0, columnspan=3, pady=10)
        self.signature_status_label = ttk.Label(status_frame, text="", font=("Helvetica", 16))
        self.signature_status_label.pack()

    def _file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        save: bool = False,
        pem: bool = False,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=6,
            padx=6,
        )
        ttk.Button(
            parent,
            text="Salvar..." if save else "Procurar...",
            command=lambda: self._choose_file(variable, save=save, pem=pem),
        ).grid(row=row, column=2, sticky="ew", pady=6)

    def _choose_file(self, variable: tk.StringVar, *, save: bool, pem: bool) -> None:
        filetypes = [("Arquivos PEM", "*.pem"), ("Todos os arquivos", "*.*")] if pem else [
            ("Todos os arquivos", "*.*")
        ]

        if save:
            selected = filedialog.asksaveasfilename(filetypes=filetypes)
        else:
            selected = filedialog.askopenfilename(filetypes=filetypes)

        if selected:
            if pem and not save and not selected.lower().endswith(".pem"):
                messagebox.showwarning(
                    "Extensão de Arquivo Incomum",
                    f"O arquivo selecionado '{Path(selected).name}' não termina com .pem.\n\n"
                    "Chaves criptográficas geralmente usam a extensão .pem. "
                    "Verifique se este é o arquivo correto.",
                )

            variable.set(selected)

    def _run_action(self, func, args: argparse.Namespace, success_message: str) -> None:
        self.signature_status_label.config(text="")
        if not self._validate_required(args):
            return

        self._set_buttons_state("disabled")
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
            self._set_buttons_state("normal")
            self._write_output(stdout.getvalue())

        if exc_info:
            title, msg = exc_info
            messagebox.showerror(title, msg)
            return

        # Se chegou aqui, nao houve erro
        if func is envelope.open_envelope:
            if result:  # Assinatura valida (True)
                self.signature_status_label.config(text="✅ Assinatura Válida", foreground="green")
                messagebox.showinfo(
                    "Sucesso", "Envelope aberto com sucesso e a assinatura foi verificada."
                )
            else:  # Assinatura invalida (False)
                self.signature_status_label.config(text="❌ Assinatura INVÁLIDA", foreground="red")
                messagebox.showwarning(
                    "Assinatura Inválida",
                    "AVISO: A assinatura digital é INVÁLIDA.\n\nO envelope foi aberto, mas o conteúdo pode ter sido alterado ou não se origina do remetente esperado. O arquivo de saída foi salvo, mas use-o com extrema cautela.",
                )
        else:
            messagebox.showinfo("Sucesso", success_message)

    def _set_buttons_state(self, state: str) -> None:
        """'normal' ou 'disabled'."""
        self.generate_keys_button.config(state=state)
        self.create_envelope_button.config(state=state)
        self.open_envelope_button.config(state=state)

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
        self.output.configure(state="normal")


def run_gui() -> None:
    app = EnvelopeApp()
    app.mainloop()
