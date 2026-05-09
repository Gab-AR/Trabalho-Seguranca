import argparse
import base64
import binascii
import os
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


AES_KEY_SIZE_BYTES = 16
AES_IV_SIZE_BYTES = 16
AES_BLOCK_SIZE_BITS = 128
SUPPORTED_RSA_SIZES = {1024, 2048}


class EnvelopeError(Exception):
    pass


def read_bytes(path: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise EnvelopeError(f"Nao foi possivel ler o arquivo '{path}': {exc}") from exc


def write_bytes(path: str, data: bytes) -> None:
    try:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
    except OSError as exc:
        raise EnvelopeError(f"Nao foi possivel gravar o arquivo '{path}': {exc}") from exc


def b64_encode(data: bytes) -> bytes:
    return base64.b64encode(data)


def b64_decode_file(path: str) -> bytes:
    raw = read_bytes(path).strip()
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EnvelopeError(f"O arquivo '{path}' nao contem Base64 valido.") from exc


def load_private_key(path: str):
    data = read_bytes(path)
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise EnvelopeError(f"Chave privada invalida em '{path}'.") from exc

    if not isinstance(key, rsa.RSAPrivateKey):
        raise EnvelopeError(f"A chave privada em '{path}' nao e uma chave RSA.")

    return key


def load_public_key(path: str):
    data = read_bytes(path)
    try:
        key = serialization.load_pem_public_key(data)
    except (ValueError, UnsupportedAlgorithm) as exc:
        raise EnvelopeError(f"Chave publica invalida em '{path}'.") from exc

    if not isinstance(key, rsa.RSAPublicKey):
        raise EnvelopeError(f"A chave publica em '{path}' nao e uma chave RSA.")

    return key


def generate_keys(args: argparse.Namespace) -> None:
    if args.tamanho not in SUPPORTED_RSA_SIZES:
        raise EnvelopeError("Tamanho invalido. Use 1024 ou 2048 bits.")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=args.tamanho,
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    write_bytes(args.privada, private_pem)
    write_bytes(args.publica, public_pem)

    print(f"Chave privada gerada: {args.privada}")
    print(f"Chave publica gerada: {args.publica}")


def aes_encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    padder = PKCS7(AES_BLOCK_SIZE_BITS).padder()
    padded = padder.update(plaintext) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def aes_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = PKCS7(AES_BLOCK_SIZE_BITS).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    except ValueError as exc:
        raise EnvelopeError(
            "Nao foi possivel decifrar a mensagem. Verifique a chave, IV e arquivo cifrado."
        ) from exc


def get_plaintext_from_input(input_str: str, encoding: str = "utf-8") -> bytes:
    """
    Obtem o texto em claro.
    Se input_str for um arquivo existente, le o conteudo.
    Caso contrario, trata input_str como o proprio texto.
    """
    path = Path(input_str)
    if path.is_file():
        print(f"Lendo mensagem do arquivo: {input_str}")
        return read_bytes(input_str)

    print("Usando texto do campo de entrada como mensagem.")
    return input_str.encode(encoding)


def create_envelope(args: argparse.Namespace) -> None:
    plaintext = get_plaintext_from_input(args.entrada)
    recipient_public_key = load_public_key(args.pub_dest)
    sender_private_key = load_private_key(args.priv_rem)

    aes_key = os.urandom(AES_KEY_SIZE_BYTES)
    iv = os.urandom(AES_IV_SIZE_BYTES)

    key_iv_hex = aes_key.hex() + iv.hex()
    try:
        encrypted_key_iv = recipient_public_key.encrypt(
            key_iv_hex.encode("ascii"),
            rsa_padding.PKCS1v15(),
        )
    except ValueError as exc:
        raise EnvelopeError(
            "Nao foi possivel cifrar a chave+IV com RSA. Verifique o tamanho da chave publica."
        ) from exc

    try:
        signature = sender_private_key.sign(
            plaintext,
            rsa_padding.PKCS1v15(),
            hashes.SHA512(),
        )
    except ValueError as exc:
        raise EnvelopeError("Nao foi possivel assinar a mensagem.") from exc

    encrypted_message = aes_encrypt(plaintext, aes_key, iv)

    write_bytes(args.saida_msg, b64_encode(encrypted_message))
    write_bytes(args.saida_chave, b64_encode(encrypted_key_iv))
    write_bytes(args.saida_assinatura, b64_encode(signature))

    print("Envelope criado com sucesso.")
    print(f"Chave AES (hex): {aes_key.hex()}")
    print(f"IV (hex): {iv.hex()}")
    print(f"Mensagem cifrada: {args.saida_msg}")
    print(f"Chave+IV cifrados: {args.saida_chave}")
    print(f"Assinatura digital: {args.saida_assinatura}")


def parse_key_iv_hex(key_iv_hex: str) -> tuple[bytes, bytes]:
    expected_len = (AES_KEY_SIZE_BYTES + AES_IV_SIZE_BYTES) * 2
    if len(key_iv_hex) != expected_len:
        raise EnvelopeError(
            f"Chave+IV decifrados possuem tamanho invalido: esperado {expected_len} "
            f"caracteres hexadecimais, obtido {len(key_iv_hex)}."
        )

    key_hex = key_iv_hex[: AES_KEY_SIZE_BYTES * 2]
    iv_hex = key_iv_hex[AES_KEY_SIZE_BYTES * 2 :]

    try:
        return bytes.fromhex(key_hex), bytes.fromhex(iv_hex)
    except ValueError as exc:
        raise EnvelopeError("Chave+IV decifrados nao estao em hexadecimal valido.") from exc


def printable_text(data: bytes, encoding: str) -> str:
    text = data.decode(encoding, errors="replace")
    stdout_encoding = sys.stdout.encoding or "utf-8"
    return text.encode(stdout_encoding, errors="replace").decode(
        stdout_encoding,
        errors="replace",
    )


def open_envelope(args: argparse.Namespace) -> None:
    encrypted_message = b64_decode_file(args.msg)
    encrypted_key_iv = b64_decode_file(args.chave)
    signature = b64_decode_file(args.assinatura)

    recipient_private_key = load_private_key(args.priv_dest)
    sender_public_key = load_public_key(args.pub_rem)

    try:
        key_iv_plain = recipient_private_key.decrypt(
            encrypted_key_iv,
            rsa_padding.PKCS1v15(),
        )
    except ValueError as exc:
        raise EnvelopeError(
            "Nao foi possivel decifrar a chave+IV. Verifique a chave privada do destinatario."
        ) from exc

    try:
        key_iv_hex = key_iv_plain.decode("ascii")
    except UnicodeDecodeError as exc:
        raise EnvelopeError("Chave+IV decifrados nao formam texto ASCII hexadecimal.") from exc

    aes_key, iv = parse_key_iv_hex(key_iv_hex)
    plaintext = aes_decrypt(encrypted_message, aes_key, iv)

    valid_signature = True
    try:
        sender_public_key.verify(
            signature,
            plaintext,
            rsa_padding.PKCS1v15(),
            hashes.SHA512(),
        )
    except InvalidSignature:
        valid_signature = False

    write_bytes(args.saida, plaintext)

    print("Envelope aberto com sucesso.")
    print(f"Chave AES (hex): {aes_key.hex()}")
    print(f"IV (hex): {iv.hex()}")
    print(f"Arquivo em claro gerado: {args.saida}")
    print(f"Assinatura valida: {'SIM' if valid_signature else 'NAO'}")
    print("Texto decifrado:")
    print(printable_text(plaintext, args.encoding))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Implementacao de Envelope Digital Assinado.",
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    gui_parser = subparsers.add_parser(
        "interface",
        help="Abre a interface grafica.",
    )
    gui_parser.set_defaults(func=open_interface)

    key_parser = subparsers.add_parser(
        "gerar-chaves",
        help="Gera par de chaves RSA em arquivos PEM.",
    )
    key_parser.add_argument("--tamanho", type=int, required=True, help="1024 ou 2048")
    key_parser.add_argument("--privada", required=True, help="Arquivo PEM da chave privada")
    key_parser.add_argument("--publica", required=True, help="Arquivo PEM da chave publica")
    key_parser.set_defaults(func=generate_keys)

    create_parser = subparsers.add_parser(
        "criar-envelope",
        help="Cifra a mensagem, cifra chave+IV e gera assinatura.",
    )
    create_parser.add_argument(
        "--entrada",
        required=True,
        help="Arquivo de texto em claro ou o proprio texto da mensagem",
    )
    create_parser.add_argument("--pub-dest", required=True, help="Chave publica do destinatario")
    create_parser.add_argument("--priv-rem", required=True, help="Chave privada do remetente")
    create_parser.add_argument("--saida-msg", required=True, help="Arquivo da mensagem cifrada")
    create_parser.add_argument("--saida-chave", required=True, help="Arquivo da chave+IV cifrados")
    create_parser.add_argument("--saida-assinatura", required=True, help="Arquivo da assinatura")
    create_parser.set_defaults(func=create_envelope)

    open_parser = subparsers.add_parser(
        "abrir-envelope",
        help="Decifra o envelope e verifica a assinatura.",
    )
    open_parser.add_argument("--msg", required=True, help="Arquivo da mensagem cifrada")
    open_parser.add_argument("--chave", required=True, help="Arquivo da chave+IV cifrados")
    open_parser.add_argument("--assinatura", required=True, help="Arquivo da assinatura")
    open_parser.add_argument("--priv-dest", required=True, help="Chave privada do destinatario")
    open_parser.add_argument("--pub-rem", required=True, help="Chave publica do remetente")
    open_parser.add_argument("--saida", required=True, help="Arquivo de texto em claro gerado")
    open_parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Codificacao usada apenas para exibir o texto no terminal. Padrao: utf-8",
    )
    open_parser.set_defaults(func=open_envelope)

    return parser


def open_interface(args: argparse.Namespace) -> None:
    try:
        from interface import run_gui
    except ImportError as exc:
        raise EnvelopeError(
            "Nao foi possivel carregar a interface grafica. Verifique se o Tkinter esta instalado."
        ) from exc

    run_gui()


def main() -> int:
    if len(sys.argv) == 1:
        try:
            open_interface(argparse.Namespace())
            return 0
        except EnvelopeError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
        return 0
    except EnvelopeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Operacao cancelada pelo usuario.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
