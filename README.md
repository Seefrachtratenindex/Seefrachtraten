# Seefrachtraten-Dashboard (XSI-C)

Interaktives Dashboard der acht Routen des Xeneta Shipping Index by Compass (XSI-C).

- `index.html` – die Website
- `data/history.json` – Historie aus dem Compass-Datenexport (bis 24.11.2026)
- `data/updates.json` – neue Werte, die automatisch angehängt werden
- `scripts/update.py` – liest die 8 Indexseiten auf compassft.com aus
- `.github/workflows/update.yml` – Zeitplan (werktags 10:47 Uhr Winterzeit)

## Einrichtung

1. Alle Dateien in das Repository hochladen (auch die Ordner `.github` und `data`).
2. Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.
3. Settings → Pages → Source **Deploy from a branch**, Branch `main`, Ordner `/ (root)` → Save.
4. Reiter **Actions** → „Daten aktualisieren“ → **Run workflow** (Testlauf).

Die Website ist danach unter `https://<kontoname>.github.io/<repository>/` erreichbar.
Schlägt ein Lauf fehl, schickt GitHub eine E-Mail.

Hinweis: Laut Xeneta ist die kostenlose Nutzung der XSI-C-Daten nur für interne Ansichtszwecke vorgesehen.
