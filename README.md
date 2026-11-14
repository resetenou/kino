# Kino-Programm Winterthur

Live: https://resetenou.github.io/kino/

- `template.html` – die App (wird zu `index.html` gebaut)
- `tools/covers.py` – holt für jeden Film ein echtes Plakat (Hochformat-Prüfung) und legt es in `posters/`
- `tools/overrides.json` – von Hand geprüfte Plakat-Zuordnungen (Titel → Bild)
- `tools/build.py` – baut `index.html` (Filmlänge, Kinostart, Doppelte zusammenlegen)
- `posters/FEHLT.txt` – Filme ohne Plakat nach dem letzten Lauf (soll leer sein)
