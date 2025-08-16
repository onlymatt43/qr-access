# qr-access — GitHub Repo Blueprint (avec fichiers prêts à copier)

## 1) Structure du dépôt
```
qr-access/
  README.md
  LICENSE
  SECURITY.md
  CODEOWNERS
  .gitignore
  .gitattributes
  .editorconfig
  .github/
    workflows/
      ci-preview.yml
      codeql.yml
    ISSUE_TEMPLATE.md
    PULL_REQUEST_TEMPLATE.md
  docs/
    SPEC.md
    CLOUD_DEV.md
  src/
    app/…
    migrations/
    workers/
    scripts/
      seed.py
  infra/
    render.yaml
    policies.md
  .env.example
  Makefile
```

## 2) Fichiers prêts à copier

### README.md
```markdown
# QR Access
MVP Flask pour accès temporisé via QR opaque + JWT + proxy HLS.

## Démarrage rapide
1. Copier `.env.example` vers `.env` et remplir les variables.
2. Voir docs/CLOUD_DEV.md pour setup Render + Preview.
3. Lancer `make dev` pour démarrer en local ou `make seed` pour générer un QR de test.
4. Scanner avec un mobile → valider `/content` ou `/hls`.

## Structure
Voir docs/SPEC.md et src/ pour les détails.
```

### .gitignore
```
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.env
*.key
jwt.key
jwt.pub
.DS_Store
.vscode/
.idea/
```

### CODEOWNERS
```
*  @ton-organisation/qr-access-maintainers
.github/  @ton-organisation/secops
infra/    @ton-organisation/devops
```

### SECURITY.md
```markdown
# Politique de sécurité
- Vulnérabilités : ouvrir un Security Advisory GitHub.
- Clés/Secrets : uniquement via GitHub Environments & Render (jamais dans Git).
- Protection `main` : PR obligatoire + review.
- Rotation clés JWT tous les 90 jours.
```

### .github/workflows/ci-preview.yml
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
      - run: pip install -r requirements.txt
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

### .github/workflows/codeql.yml
```yaml
name: CodeQL
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 1'

jobs:
  analyze:
    uses: github/codeql-action/.github/workflows/codeql.yml@v3
    with:
      languages: python
```

### .env.example
```
DATABASE_URL=postgresql://user:pass@host/dbname
REDIS_URL=redis://:pass@host:6379/0
JWT_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
MERCHANT_SALT=changeme
BASE_URL=https://qr-access-staging.onrender.com
```

### Makefile
```makefile
dev:
	flask --app app:create_app run --reload

seed:
	python scripts/seed.py

lint:
	flake8 src

ci: lint
	pytest
```

## 3) Étapes
1. Crée un repo privé `qr-access`.
2. Ajoute tous ces fichiers.
3. Configure GitHub Environments (staging, production) + secrets.
4. Connecte à Render.
5. Push → PR → preview auto + staging sur main.

