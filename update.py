"""Holt die neuesten XSI-C-Werte von den Compass-Indexseiten und haengt sie an data/updates.json an.

Laeuft automatisch ueber GitHub Actions (.github/workflows/update.yml).
Nur Python-Standardbibliothek, keine Zusatzpakete noetig.
"""
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history.json"
UPD = ROOT / "data" / "updates.json"

TICKERS = {
    "XSICFENE": "Far East to North Europe",
    "XSICNEFE": "North Europe to Far East",
    "XSICFEUW": "Far East to US West Coast",
    "XSICUWFE": "US West Coast to Far East",
    "XSICFESE": "Far East to South America East Coast",
    "XSICNEUE": "North Europe to US East Coast",
    "XSICUENE": "US East Coast to North Europe",
    "XSICNESE": "North Europe to South America East Coast",
}
URL = "https://www.compassft.com/indice/{}/"
MAX_JUMP = 0.25  # groessere Spruenge werden nur nach zweitem identischem Abruf uebernommen


def fetch(ticker):
    req = urllib.request.Request(
        URL.format(ticker.lower()),
        headers={"User-Agent": "Mozilla/5.0 (frachtraten-dashboard; GitHub Actions)",
                 "Accept-Language": "en"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def to_text(page):
    page = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(page))


def num(s):
    s = s.replace(",", "").replace("\u00a0", "").strip()
    return float(s)


def parse(page, ticker):
    """Liefert (datum, wert) oder wirft ValueError. Mehrere Muster, weil das Seitenlayout unbekannt ist."""
    text = to_text(page)
    if ticker.lower() not in page.lower() and TICKERS[ticker].lower() not in text.lower():
        raise ValueError("Seite passt nicht zum Index")
    # Muster 1: Beschriftete Felder "Date ... 2026-11-25 ... Last Value ... 3364"
    d = re.search(r"\bDate\b\s*:?\s*(\d{4}-\d{2}-\d{2})", text)
    v = re.search(r"\bLast Value\b\s*:?\s*([\d][\d,\.]*)", text, re.I)
    if d and v:
        return d.group(1), num(v.group(1))
    # Muster 2: Reihenfolge vertauscht "Last Value 3364 ... Date 2026-11-25"
    m = re.search(r"Last Value\s*:?\s*([\d][\d,\.]*).{0,80}?(\d{4}-\d{2}-\d{2})", text, re.I)
    if m:
        return m.group(2), num(m.group(1))
    # Muster 3: Zeitreihe im Seitenquelltext, z. B. ["2026-11-25",3364] oder {"date":"2026-11-25","value":3364}
    pairs = re.findall(r'["\'](\d{4}-\d{2}-\d{2})(?:T[\d:\.]+Z?)?["\']\s*[,:]\s*\[?\s*([\d]+(?:\.\d+)?)', page)
    pairs += [(a, b) for a, b in re.findall(
        r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2})[^"]*"\s*,\s*"(?:value|close|level)"\s*:\s*([\d\.]+)', page, re.I)]
    if pairs:
        d, v = max(pairs, key=lambda p: p[0])
        return d, float(v)
    raise ValueError("Wert/Datum nicht gefunden (Seite laedt Daten evtl. per JavaScript)")


def clean(v):
    return int(v) if float(v).is_integer() else round(v, 2)


def main():
    hist = json.loads(HIST.read_text())
    upd = json.loads(UPD.read_text())
    upd.setdefault("v", {})
    last_hist = hist["d"][-1]
    ok, errors, added = 0, [], []

    for t in TICKERS:
        series = upd["v"].setdefault(t, [])
        known = {d for d, _ in series}
        # letzter bekannter Wert (Updates, sonst Historie)
        prev = series[-1][1] if series else next(
            (x for x in reversed(hist["v"].get(t, [])) if x is not None), None)
        try:
            d, v = parse(fetch(t), t)
            dt.date.fromisoformat(d)
            if v <= 0:
                raise ValueError(f"unplausibler Wert {v}")
            if prev and abs(v / prev - 1) > MAX_JUMP:
                time.sleep(5)
                d2, v2 = parse(fetch(t), t)
                if (d2, v2) != (d, v):
                    raise ValueError(f"Sprung {prev}->{v} nicht bestaetigt")
            ok += 1
            if d > last_hist and d not in known:
                series.append([d, clean(v)])
                series.sort(key=lambda p: p[0])
                added.append(f"{t} {d} {clean(v)}")
        except Exception as e:  # einzelne Indizes duerfen fehlschlagen
            errors.append(f"{t}: {e}")
        time.sleep(1)

    upd["v"] = {k: v for k, v in upd["v"].items() if v}
    if ok:
        upd["lastCheck"] = dt.datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
    UPD.write_text(json.dumps(upd, separators=(",", ":")) + "\n")

    print("Neu:", ", ".join(added) if added else "nichts Neues")
    for e in errors:
        print("Fehler:", e)
    # Lauf als fehlgeschlagen markieren (GitHub schickt dann eine E-Mail), wenn kein einziger Index lesbar war
    if ok == 0:
        sys.exit("Kein Index konnte gelesen werden.")


if __name__ == "__main__":
    main()
