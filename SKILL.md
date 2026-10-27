---
name: pajemploi-cli
description: "Drive your own Pajemploi (URSSAF) employer space from the terminal via the bundled `paje` command — list salariés, read fiches, list declarations/documents, and download bulletins de salaire (PDF). Because api.urssaf.fr sits behind a WAF that resets non-browser HTTP clients (even curl_cffi Chrome impersonation), the CLI attaches over the Chrome DevTools Protocol to a REAL, already-logged-in Chrome tab and runs the API calls inside the page — reusing the browser's fingerprint (passes the WAF) and the live session (nothing to paste). The CLI auto-launches a dedicated debug Chrome (persistent profile) on demand and opens Pajemploi; the user just logs in by hand in that window when the session expires. Use when the user wants to list/read their Pajemploi salariés, fiches, declarations, or download bulletins de salaire. Note: the salarié NIR (numéro de sécurité sociale) is masked server-side and not recoverable via this API."
---

# pajemploi-cli

Drive your **own** Pajemploi (URSSAF) employer space from the terminal —
salariés, fiches, documents, bulletins de salaire — by running the private
`api.urssaf.fr/paje/apaj/v1` calls **inside your real Chrome**.

## How to invoke

Invoke it as **`paje`** — on `$PATH` via `claudine/scripts/link_clis.py`, which
links this repo's `bin/paje` into `~/.local/bin`, so it always runs the current
checkout: a `git pull`, or even an uncommitted edit, takes effect immediately
with nothing to reinstall.

```bash
paje salaries
```

If `paje` is not on `$PATH`, run `<skill-dir>/bin/paje` (a symlink to
`pajemploi_cli.py`, a PEP 723 script — `uv` resolves deps inline on first run).

## Authentication

Nothing to paste and no stored credential: the CLI reuses the live session of a
logged-in Pajemploi tab. The first command auto-starts a **dedicated debug
Chrome** (persistent profile `~/.pajemploi-chrome`, coexists with your normal
Chrome) and opens Pajemploi:

```bash
paje doctor
```

If you're not logged in, log in **by hand** in the Chrome window that opens, then
re-run — the dedicated profile keeps the session between runs, so you only log in
when it expires. A `401/403` later means the session expired; log in again there.

Options: `--cdp-url` / `PAJE_CDP_URL` (other port), `--no-launch` (don't auto-start
Chrome), `--no-reload` (don't reload the tab to capture a token — fail instead).

## Output conventions

- Default: one compact line per record, ids first (`idSalarie`, `idDeclaration`).
- `--json` on `salaries`, `salarie`, `documents`: the API's JSON as returned.
- stdout carries data only; diagnostics go to stderr through `logging`
  (`PAJE_LOG=DEBUG` for verbose).
- `bulletin` writes the PDF to disk and prints the saved path.

## Commands

```bash
# Read
paje doctor                                   # DevTools connection + Pajemploi tab + token capture
paje salaries [--json]                        # all salariés: id, nom, prénom, activité, actif, NIR certifié CNAV
paje salarie <idSalarie> [--json]             # fiche: civilité, naissance, lieu, adresse, email, numNir (masked)
paje documents [--type BS] [--from YYYY-MM] [--to YYYY-MM] [--salarie NAME] [--json]
                                              # documents over a period; --type BS = bulletin; rows carry idDeclaration
# Download
paje bulletin <idDeclaration> [-o PATH] [--rang N]   # bulletin de salaire PDF (base64 -> file)
```

`--salarie` is a client-side, case-insensitive substring filter on the nom.

## Recipes

```bash
# Every bulletin of 2025 for one salarié, as PDFs
paje documents --from 2025-01 --to 2025-12 --salarie dupont --json \
  | jq -r '.[].idDeclaration' \
  | while read -r id; do paje bulletin "$id" -o "BS_$id.pdf"; done

# Net salary paid per month
paje documents --from 2025-01 --to 2025-12 --json | jq -r '.[] | [.periode, .mntSalaireNetPaye] | @tsv'
```

## Gotchas

- **The NIR is NOT recoverable.** The URSSAF masks it everywhere on the employer
  side: `paje salarie` → `numNir` masked (`2***********XXX`); the bulletin PDF
  shows only the **N° Salarié Pajemploi**, never the NIR.
- The site leaks memory and freezes after a few minutes; the CLI keeps the
  session alive on its own once the tab has made one authenticated call.
- Never send `content-type` on a bodyless GET: the preflight is rejected
  ("Failed to fetch").
- `prompt=login` is forced by the OAuth client, hence repeated web logins when
  the session expires.

## Why it drives a browser (not plain HTTP)

`api.urssaf.fr` is behind a WAF that fingerprints the TLS/HTTP client and
**resets the connection for anything that isn't a real browser** — plain
`requests`, `curl`, and even `curl_cffi`'s Chrome impersonation all get
"connection reset", while Chrome itself succeeds. So the CLI attaches to a real
Chrome over the DevTools Protocol (CDP) and executes each API call from a
logged-in `pajemploi.urssaf.fr` tab. That reuses the page's genuine browser
fingerprint (passes the WAF) and its **live session token** (nothing to capture
or paste).

The API requires **two** headers: `authorization: Bearer <…>` and a rolling
`x-auth-token` (the server rotates the latter on every response). An injected
hook captures both from the app's own traffic (`window.__pajeAuth` /
`window.__pajeXat`) and the CLI replays them — so once the tab has made one
authenticated call, the CLI keeps the session alive on its own.

## API contract (for maintenance)

All on `https://api.urssaf.fr/paje/apaj/v1`, headers `authorization: Bearer <…>`
+ `x-auth-token` (the latter rotated in each response's `x-auth-token` header;
don't send `content-type` on a bodyless GET — the preflight is rejected):

- `POST /employeur/salaries/rechercher` — body `{"isActif":null,"typeActivite":"","idSalarie":"","ecranAgrement":"ECRAN_LISTE_SALARIES"}`
- `GET  /salarie?idSalarie=<id>` — fiche (numNir masked)
- `POST /documents/voletsSociaux/rechercher` — body `{"typeDocuments":["BS"],"periodeDeclarationDebut":"YYYY-MM","periodeDeclarationFin":"YYYY-MM"}`
- `POST /documents/generer` — body `{"codeParamDoc":"PAJE_BULLETIN_SALAIRE","criteresAggregation":[{"key":"refDoc","value":"<idDeclaration>"},{"key":"rangVSO","value":"0"}]}` → `{documentData: "<base64 PDF>"}`

OAuth login (browser only): `login.urssaf.fr/api/oauth/v1/token`, public PKCE
client `e08bc404-9af9-4f68-a73d-8732c435faff`, scope `openid sap.paje
offline_access ods.cedito`, `prompt=login` forced (hence the repeated web logins).

## Tests

```bash
uv run --script tests/test_paje.py
```

## Project layout

```
pajemploi-cli/
  SKILL.md            # this file
  README.md
  pajemploi_cli.py    # the CLI (PEP 723 script, CDP client)
  bin/paje            # symlink -> ../pajemploi_cli.py — invoke this
  tests/test_paje.py  # unit tests for the pure helpers
```
