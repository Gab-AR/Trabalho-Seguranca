# Envelope Digital Assinado

## Escolha do formato

Os arquivos criptograficos gerados pelo programa usam Base64:

- mensagem cifrada;
- chave de sessao + IV cifrados;
- assinatura digital.

A mensagem de entrada (seja de um arquivo ou texto direto) e o arquivo decifrado sao tratados como texto em claro.

## Algoritmos e parametros

- AES de 128 bits no modo CBC.
- Padding PKCS7 para o AES.
- RSA com PKCS#1 v1.5, equivalente ao `RSA/ECB/PKCS1Padding` citado no enunciado.
- Assinatura digital com RSA, PKCS#1 v1.5 e SHA-512.
- Chave AES e IV possuem 16 bytes cada.
- Antes da cifragem RSA, a chave AES e o IV sao convertidos para hexadecimal e concatenados:

```text
chave_aes_hex + iv_hex
```

Como cada valor possui 16 bytes, cada parte tem 32 caracteres hexadecimais. A string concatenada possui 64 caracteres.

## Instalacao

Use Python 3.10 ou superior.

```bash
pip install -r requirements.txt
```

## Interface grafica

Para abrir a interface grafica:

```bash
python main.py
```

Tambem e possivel abrir explicitamente com:

```bash
python main.py interface
```

A janela possui tres abas:

- geracao de chaves;
- criacao do envelope;
- abertura do envelope.

## Geracao de chaves

Exemplo para gerar chaves do destinatario:

```bash
python main.py gerar-chaves --tamanho 2048 --privada dest_priv.pem --publica dest_pub.pem
```

Exemplo para gerar chaves do remetente:

```bash
python main.py gerar-chaves --tamanho 2048 --privada rem_priv.pem --publica rem_pub.pem
```

## Criacao do envelope

O campo `--entrada` pode ser tanto um arquivo de texto quanto a propria mensagem em texto claro, entre aspas.

Exemplo usando um arquivo de entrada:
```bash
python main.py criar-envelope ^
  --entrada mensagem.txt ^
  --pub-dest dest_pub.pem ^
  --priv-rem rem_priv.pem ^
  --saida-msg mensagem.cif ^
  --saida-chave chave.env ^
  --saida-assinatura assinatura.sig
```

Saidas:

- `mensagem.enc`: mensagem cifrada em Base64;
- `chave.enc`: chave AES + IV cifrados com RSA em Base64;
- `assinatura.sig`: assinatura digital em Base64.

## Abertura do envelope

```bash
python main.py abrir-envelope ^
  --msg mensagem.enc ^
  --chave chave.enc ^
  --assinatura assinatura.sig ^
  --priv-dest dest_priv.pem ^
  --pub-rem rem_pub.pem ^
  --saida mensagem_aberta.txt
```

Durante a abertura, o programa exibe:

- chave AES em hexadecimal;
- IV em hexadecimal;
- texto decifrado;
- resultado da verificacao da assinatura.

## Tratamento de erros

O programa trata erros comuns, como:

- arquivo inexistente;
- chave publica ou privada invalida;
- Base64 invalido;
- falha ao decifrar chave + IV;
- falha ao decifrar mensagem;
- assinatura invalida.
