# qr-access — Repo Files (copy‑paste pack)

> Copie/colle ces fichiers directement dans ton repo GitHub **privé** `qr-access`. Remplace les valeurs `YOUR_ORG_OR_USER` et secrets selon ton setup.

---

## README.md

````md
# QR Access

MVP Flask pour accès temporisé via QR opaque (HMAC) → JWT RS256 → proxy (HTML/Fragments/Images/HLS pré‑généré).

## Démarrage rapide
1. Installe : `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. Exporte les variables (voir `.env.example` si présent) et lance :
   ```bash
   export FLASK_APP=app:create_app
   flask run
````

3. Voir `docs/CLOUD_DEV.md` pour le flux **preview PR** + **staging** sur Render.
4. `python scripts/seed.py` génère une URL **QR** à scanner.

## Architecture

- QR opaque (HMAC/HKDF) → `/api/redeem` → JWT RS256 minute‑précis (pinné RS256) → `/content|/fragment|/media|/hls` (proxy + contrôle d’accès à chaque requête).
- Binding **appareil** via **fingerprint minimal maison** (UA+timezone+platform+entropy+cookie).
- Sessions/jti/rate‑limit en **Redis**. Référentiels en **PostgreSQL**.

## Sécurité

- **Aucun code lisible** : QR‑only.
- **Pas de saisie manuelle**.
- **CSP** stricte, `no-store` pour les ressources protégées, pas d’URL directe de bucket.
- **Clés privées** uniquement sur Render ; clé publique JWT en secret GitHub.

## Dossiers

- `src/` : application Flask (blueprints + services)
- `infra/render.yaml` : déploiement Render (preview/staging)
- `docs/` : SPEC & cloud‑dev

````

---

## .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/

# Environnement / secrets locaux
.env
*.key
jwt.key
jwt.pub

# OS/IDE
.DS_Store
.vscode/
.idea/
````

---

## CODEOWNERS

```text
# Remplace par ton équipe/org
*  @YOUR_ORG_OR_USER/qr-access-maintainers
.github/  @YOUR_ORG_OR_USER/secops
infra/    @YOUR_ORG_OR_USER/devops
```

---

## SECURITY.md

```md
# Politique de sécurité

- **Signalement vulnérabilités** : ouvrir un *Private Security Advisory* sur GitHub.
- **Clés/Secrets** : jamais commitées. Utiliser **GitHub Environments** et variables Render.
- **Protection de branche** : PR obligatoire vers `main`, 1 review mini, CodeQL requis.
- **Rotation** : clés JWT privées tous les 90 jours ; nettoyage des `jti` expirés.
- **CSP** stricte, pas d’URL publique pour les médias ; proxy obligatoire.
```

---

## .github/workflows/ci-preview\.yml

```yaml
name: CI & Render Previews
on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: python -m pip install -r requirements.txt
      - run: python -m compileall .

  render-preview:
    if: github.event_name == 'pull_request'
    needs: ci
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create/Update Render Preview
        uses: render-oss/action@v1
        with:
          serviceId: ${{ secrets.RENDER_SERVICE_ID }}
          apiKey: ${{ secrets.RENDER_API_KEY }}
          branch: ${{ github.head_ref }}
          pr: ${{ github.event.number }}
          envVars: |
            BRANCH=${{ github.head_ref }}
            IS_PREVIEW=true

  render-staging:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: ci
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Render Staging
        uses: render-oss/action@v1
        with:
          serviceId: ${{ secrets.RENDER_SERVICE_ID_STAGING }}
          apiKey: ${{ secrets.RENDER_API_KEY }}
          branch: main
```

---

## .github/workflows/codeql.yml

```yaml
name: CodeQL
on:
  push: { branches: [ main ] }
  pull_request: { branches: [ main ] }

jobs:
  analyze:
    uses: github/codeql-action/.github/workflows/codeql.yml@v3
    with:
      languages: python
```

---

## infra/render.yaml

```yaml
services:
- type: web
  name: qr-access-${BRANCH:-staging}
  env: python
  plan: starter
  buildCommand: pip install -r requirements.txt
  startCommand: gunicorn 'app:create_app()'
  envVars:
  - key: DATABASE_URL
    fromDatabase: { name: qr-access-db-${BRANCH:-staging}, property: connectionString }
  - key: REDIS_URL
    fromService: { name: qr-access-redis-${BRANCH:-staging}, type: redis }
  - key: JWT_PRIVATE_KEY
    sync: false
  - key: JWT_PUBLIC_KEY
    sync: false
  - key: MERCHANT_SALT
    sync: false
  - key: BASE_URL
    value: https://qr-access-${BRANCH:-staging}.onrender.com

databases:
- name: qr-access-db-${BRANCH:-staging}

redis:
- name: qr-access-redis-${BRANCH:-staging}
  plan: starter
```

---

## docs/SPEC.md (placeholder)

```md
# SPEC-1 — Accès QR temporisé (A → B → C)
Voir la version à jour dans le canvas, ou colle ici la dernière révision.
```

---

## docs/CLOUD\_DEV.md (placeholder)

```md
# Cloud-dev (GitHub + Render)
Préviews PR + Staging + Validation JWT + Proxy HLS minimal. Voir le doc dédié dans le canvas et reporter ici la version adoptée.
```

---

## Hints (où mettre quoi)

- **src/** : copie le contenu du *qr-access-flask-mvp-skeleton* (canvas) ici.
- **docs/** : copie les 2 documents de design du canvas.
- **Secrets** : définis `RENDER_API_KEY`, `RENDER_SERVICE_ID(_STAGING)`, `JWT_PUBLIC_KEY` côté **GitHub** ; `JWT_PRIVATE_KEY` et `MERCHANT_SALT` côté **Render**.

```
```
