# pajemploi-cli

Piloter ton espace **employeur Pajemploi (URSSAF)** depuis le terminal —
salariés, fiches, documents, bulletins de salaire — en exécutant les appels de
l'API privée `https://api.urssaf.fr/paje/apaj/v1` **dans ton vrai Chrome**.

## Pourquoi ça passe par le navigateur

`api.urssaf.fr` est derrière un **WAF qui coupe la connexion** pour tout client
HTTP non-navigateur — `requests`, `curl`, et même l'impersonation Chrome de
`curl_cffi` reçoivent tous « connection reset », alors que Chrome passe. La CLI
s'attache donc à un vrai Chrome via le **DevTools Protocol (CDP)** et lance
chaque appel **dans un onglet Pajemploi connecté** : elle réutilise l'empreinte
navigateur (passe le WAF) et **la session vivante** (rien à coller).

Le jeton `x-auth-token` est **glissant** (le serveur en renvoie un neuf à chaque
réponse) ; un hook injecté garde le dernier dans `window.__pajeXat` et la CLL le
fait tourner elle-même. Une fois l'onglet connecté, la CLI continue seule — utile
puisque le site fuit la mémoire et **freeze au bout de ~3 min** : tu te connectes
à la main, la CLI prend le relais.

## Setup (une fois par session Chrome)

1. Lance Chrome avec le port DevTools et un profil dédié (macOS) :

   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --remote-debugging-port=9222 \
     --user-data-dir="$HOME/.pajemploi-chrome"
   ```

2. Dans ce Chrome, connecte-toi à https://pajemploi.urssaf.fr **à la main**.
3. Vérifie le pont :

   ```bash
   ./bin/paje doctor
   ```

Port différent ? `--cdp-url` ou `PAJE_CDP_URL`.

## Commandes

```bash
./bin/paje doctor                           # vérifie connexion + onglet + token
./bin/paje salaries                         # liste des salariés (--json possible)
./bin/paje salarie <idSalarie>              # fiche détaillée d'un salarié
./bin/paje documents --type BS --from 2024-01 --to 2026-12 --salarie <nom>
./bin/paje bulletin <idDeclaration> -o bulletin.pdf   # télécharge le PDF
```

Chaque commande de lecture accepte `--json`. Options globales : `--cdp-url`,
`--no-reload` (ne pas recharger l'onglet pour capturer un token).

## ⚠️ Le NIR (numéro de sécurité sociale) n'est pas récupérable

L'URSSAF masque le NIR côté employeur :

- `paje salarie <id>` → champ `numNir` **masqué** (`2***********XXX`) ;
- le **bulletin de salaire PDF** n'affiche que le **N° Salarié Pajemploi**, jamais le NIR.

## Tests

```bash
uv run --with pytest --with click --with websocket-client python -m pytest tests/ -q
```
