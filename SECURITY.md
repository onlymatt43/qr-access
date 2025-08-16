# Politique de sécurité

- Signalement vulnérabilités : ouvrir un Private Security Advisory sur GitHub.
- Clés/Secrets : jamais commités. Utiliser GitHub Environments et variables Render.
- Protection de branche : PR obligatoire vers `main`, 1 review mini, CodeQL requis.
- Rotation : clés JWT privées tous les 90 jours ; nettoyage des jti expirés.
- CSP stricte, pas d’URL publique pour les médias ; proxy obligatoire.
