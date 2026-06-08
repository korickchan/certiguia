"""Geração de PIX copia e cola (BR Code estático)."""

import re


def _crc16(payload: str) -> str:
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _campo(id_: str, valor: str) -> str:
    valor = str(valor)
    return f"{id_}{len(valor):02d}{valor}"


def gerar_pix_copia_cola(chave: str, nome: str, cidade: str, valor: float | None = None, txid: str = "VETQR") -> str:
    """Gera payload PIX estático. valor=None → doação livre (sem valor fixo)."""
    chave = chave.strip()
    nome = re.sub(r"[^a-zA-Z0-9 ]", "", nome.upper())[:25] or "DOACAO VETQR"
    cidade = re.sub(r"[^a-zA-Z0-9 ]", "", cidade.upper())[:15] or "SALVADOR"
    txid = re.sub(r"[^a-zA-Z0-9]", "", txid.upper())[:25] or "VETQR"

    merchant = _campo("00", "01") + _campo("26", _campo("00", "br.gov.bcb.pix") + _campo("01", chave))
    payload = (
        merchant
        + _campo("52", "0000")
        + _campo("53", "986")
    )
    if valor is not None and valor > 0:
        payload += _campo("54", f"{valor:.2f}")
    payload += _campo("58", "BR") + _campo("59", nome) + _campo("60", cidade)
    payload += _campo("62", _campo("05", txid))
    payload += "6304"
    return payload + _crc16(payload)


def qr_code_base64(payload: str) -> str | None:
    try:
        import base64
        import io
        import qrcode
        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None
