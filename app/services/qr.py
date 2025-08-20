import qrcode
import io

def make_qr(url: str, path: str):
    img = qrcode.make(url)
    img.save(path)

def make_qr_bytes(url: str) -> bytes:
    """Return QR PNG bytes for the provided URL."""
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
