# Kino-Programm Winterthur

Live: https://resetenou.github.io/kino/

## Programm erneuern (alles im Repo-Ordner)
1. `python3 -I tools/refresh.py 30` – lädt Kiwi Loge, Kiwi Center, Maxx (Cineman) und Kino Cameo für 30 Tage, schreibt `tools/program.json` und `tools/meta.json`
2. `python3 -I tools/covers.py tools/program.json` – holt für jeden Film ein echtes Plakat (nur Hochformat) nach `posters/`
3. `python3 -I tools/build.py` – baut `index.html` aus `template.html`
4. `posters/FEHLT.txt` muss leer sein, sonst Plakat suchen und in `tools/overrides.json` eintragen; dann committen und pushen

## Dateien
- `template.html` – die App
- `tools/overrides.json` – von Hand geprüfte Plakate (Titel → Bild)
- `tools/meta_manual.json` – von Hand korrigierte Filminfos (Titel → Genres, Land, Jahr, Regie, Erstaufführung)
- `img/` – Kinofotos, `docs/` – Vorschaubilder
