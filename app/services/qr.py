import qrcode

def make_qr(url: str, path: str):
    img = qrcode.make(url)
    img.save(path)
