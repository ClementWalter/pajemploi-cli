# pajemploi-cli

**Visibility: public.**

**Extension: not shipped** as a Claude Desktop extension: it drives a dedicated debug Chrome window the user logs into by hand.

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

L'API exige **deux** en-têtes : `authorization: Bearer <…>` **et** `x-auth-token`
(~36c). Le `x-auth-token` est **glissant** (le serveur en renvoie un neuf à chaque
réponse). Un hook injecté dans la page capture les deux (`window.__pajeAuth` et
`window.__pajeXat`) depuis le trafic de l'app, et la CLI les rejoue. Une fois
l'onglet connecté, la CLI se débrouille seule — utile puisque le site fuit la
mémoire et **freeze au bout de ~3 min** : tu te connectes à la main, la CLI prend
le relais.

## Utilisation

Rien à lancer à la main. La première commande démarre au besoin un **Chrome
dédié** (profil persistant `~/.pajemploi-chrome`) et ouvre Pajemploi :

```bash
./bin/paje doctor        # ou directement ./bin/paje salaries
```

- **Pas connecté ?** Connecte-toi dans la fenêtre Chrome qui s'ouvre, puis
  relance. Le profil dédié **garde ta session** entre les runs (tu ne te
  reconnectes que quand elle expire) et coexiste avec ton Chrome habituel.
- Un `401/403` = session expirée → reconnecte-toi dans cette fenêtre.

Options : `--cdp-url` / `PAJE_CDP_URL` (autre port), `--no-launch` (ne pas
démarrer Chrome automatiquement), `--no-reload`.

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
uv run --script tests/test_paje.py
```
