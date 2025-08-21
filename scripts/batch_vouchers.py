#!/usr/bin/env python3
import os, sys, csv, io, base64, math
import argparse
import pathlib
import requests
from PIL import Image, ImageDraw, ImageFont

# Batch-generate QR vouchers by calling /admin/issue-qr
# Outputs: PNGs, CSV, and optional A4 PDF sheet with cards

def parse_args():
    p = argparse.ArgumentParser(description='Batch generate QR vouchers using the admin issuance API')
    p.add_argument('--base-url', default=os.environ.get('BASE_URL','http://localhost:5000'), help='Service base URL')
    p.add_argument('--admin-key', default=os.environ.get('ADMIN_API_KEY'), help='X-Admin-Key (env ADMIN_API_KEY)')
    p.add_argument('--merchant', type=int, default=int(os.environ.get('QR_MERCHANT_ID','1')), help='merchant_id')
    p.add_argument('--product', type=int, default=int(os.environ.get('QR_PRODUCT_ID','1')), help='product_id')
    p.add_argument('--duration', type=int, default=int(os.environ.get('QR_DURATION_MIN','15')), help='duration_min')
    p.add_argument('--count', type=int, default=int(os.environ.get('COUNT','10')), help='number of vouchers to issue')
    p.add_argument('--batch', default=os.environ.get('BATCH_ID') or 'batch', help='batch id/prefix for output folder')
    p.add_argument('--out', default='out', help='output directory root (default: out)')
    p.add_argument('--no-pdf', action='store_true', help='skip generating a combined A4 PDF sheet')
    return p.parse_args()


def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)


def issue_one(base_url: str, key: str, merchant_id: int, product_id: int, duration_min: int):
    url = f"{base_url.rstrip('/')}/admin/issue-qr"
    headers = {
        'X-Admin-Key': key,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    body = {
        'merchant_id': merchant_id,
        'product_id': product_id,
        'duration_min': duration_min,
    }
    r = requests.post(url, headers=headers, json=body, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"issue-qr failed {r.status_code}: {r.text[:200]}")
    data = r.json()
    code_id = data['code_id']
    redeem_url = data['redeem_url']
    png_b64 = data['qr_png_b64']
    png_bytes = base64.b64decode(png_b64)
    return code_id, redeem_url, png_bytes


def make_card(qr_png_bytes: bytes, title: str, subtitle: str, footer: str, card_px=(800, 1000)) -> Image.Image:
    # Compose a printable card PNG with QR and text
    W, H = card_px
    bg = Image.new('RGB', (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(bg)
    # Load QR
    qr = Image.open(io.BytesIO(qr_png_bytes)).convert('RGB')
    # Fit QR into square area
    qr_size = min(W - 120, int(H * 0.5))
    qr = qr.resize((qr_size, qr_size), Image.LANCZOS)
    qr_x = (W - qr_size) // 2
    qr_y = 180
    bg.paste(qr, (qr_x, qr_y))
    # Fonts (fallback to default)
    try:
        font_title = ImageFont.truetype('Arial.ttf', 42)
        font_sub = ImageFont.truetype('Arial.ttf', 28)
        font_foot = ImageFont.truetype('Arial.ttf', 24)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_foot = ImageFont.load_default()
    # Title
    tw, th = draw.textsize(title, font=font_title)
    draw.text(((W - tw) // 2, 30), title, fill=(0, 0, 0), font=font_title)
    # Subtitle
    sw, sh = draw.textsize(subtitle, font=font_sub)
    draw.text(((W - sw) // 2, 100), subtitle, fill=(30, 30, 30), font=font_sub)
    # Footer
    fw, fh = draw.textsize(footer, font=font_foot)
    draw.text(((W - fw) // 2, qr_y + qr_size + 40), footer, fill=(60, 60, 60), font=font_foot)
    return bg


def save_pdf_sheet(images: list[Image.Image], out_pdf: pathlib.Path, cols=2, rows=3, margin=50):
    if not images:
        return
    # A4 at 300 DPI ≈ 2480x3508 px
    page_w, page_h = 2480, 3508
    card_w = (page_w - margin * (cols + 1)) // cols
    card_h = (page_h - margin * (rows + 1)) // rows
    pages = []
    i = 0
    while i < len(images):
        page = Image.new('RGB', (page_w, page_h), color=(255, 255, 255))
        drawn = 0
        for r in range(rows):
            for c in range(cols):
                if i >= len(images):
                    break
                card = images[i].resize((card_w, card_h), Image.LANCZOS)
                x = margin + c * (card_w + margin)
                y = margin + r * (card_h + margin)
                page.paste(card, (x, y))
                i += 1
                drawn += 1
            if i >= len(images):
                break
        pages.append(page)
    # Save multipage PDF via PIL
    pages[0].save(out_pdf, save_all=True, append_images=pages[1:], resolution=300)


def main():
    args = parse_args()
    if not args.admin_key:
        print('ERROR: missing --admin-key or env ADMIN_API_KEY', file=sys.stderr)
        sys.exit(1)
    out_root = pathlib.Path(args.out) / f"{args.batch}"
    png_dir = out_root / 'png'
    ensure_dir(png_dir)

    csv_path = out_root / 'vouchers.csv'
    pdf_path = out_root / 'vouchers.pdf'

    rows = []
    cards = []

    print(f"→ Issuing {args.count} vouchers to {args.base_url} (merchant={args.merchant}, product={args.product}, duration={args.duration}m)…")
    for i in range(args.count):
        try:
            code_id, redeem_url, png_bytes = issue_one(args.base_url, args.admin_key, args.merchant, args.product, args.duration)
        except Exception as e:
            print(f"[{i+1}/{args.count}] ERROR: {e}", file=sys.stderr)
            sys.exit(2)
        png_path = png_dir / f"qr_{code_id}.png"
        with open(png_path, 'wb') as f:
            f.write(png_bytes)
        rows.append({'code_id': code_id, 'redeem_url': redeem_url, 'png': str(png_path.relative_to(out_root))})
        # Build printable card
        title = 'Accès QR — Scanner avec votre téléphone'
        subtitle = f"Code #{code_id} • {args.duration} min"
        footer = redeem_url
        card = make_card(png_bytes, title, subtitle, footer)
        cards.append(card)
        print(f"[{i+1}/{args.count}] code {code_id}")

    # Write CSV
    ensure_dir(out_root)
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['code_id','redeem_url','png'])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Write PDF sheet(s)
    if not args.no_pdf:
        save_pdf_sheet(cards, pdf_path)
        print(f"✅ Wrote PDF: {pdf_path}")

    print(f"✅ Done. CSV: {csv_path}\nPNG dir: {png_dir}")


if __name__ == '__main__':
    main()
