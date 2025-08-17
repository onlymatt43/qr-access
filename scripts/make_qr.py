import os, sys, re, subprocess

def get_url():
    # 1) Arg CLI > 2) VAR d'env/Make > 3) seed.py
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        return sys.argv[1].strip()
    env_url = os.environ.get("QR_URL")
    if env_url:
        return env_url.strip()
    print("→ Aucune URL fournie, exécution de scripts/seed.py pour en obtenir une…")
    r = subprocess.run(["python3", "scripts/seed.py"], capture_output=True, text=True)
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    m = re.search(r"(https?://\S+)", out)
    if not m:
        print("❌ Impossible de trouver l’URL dans la sortie de seed.py :")
        print(out)
        sys.exit(1)
    return m.group(1)

def main():
    try:
        import qrcode
    except ImportError:
        print("Le module qrcode n'est pas installé. Lance :")
        print('  python3 -m pip install "qrcode[pil]"')
        sys.exit(1)

    url = get_url()
    print("URL utilisée :", url)
    img = qrcode.make(url)
    out = "qr.png"
    img.save(out)
    print("✅ QR généré →", out)

if __name__ == "__main__":
    main()