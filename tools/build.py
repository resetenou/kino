"""Baut index.html aus template.html + tools/program.json (+ tools/meta.json).

Aufruf: python3 -I tools/build.py
- legt doppelte Filme (gleicher Titel aus Cineman und Kino Cameo) zusammen
- hängt Filmlänge (Minuten) und Kinostart an jeden Film: f = [Titel, Genre, Plakat, Link, Minuten, Kinostart]
"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda *p: os.path.join(ROOT, *p)


def norm(t):
    t = unicodedata.normalize('NFKD', t.lower())
    t = re.split(r'\s[(–-]\s?', t)[0]
    return re.sub(r'[^a-z0-9]', '', t)


d = json.load(open(T('tools', 'program.json')))
meta = json.load(open(T('tools', 'meta.json'))) if os.path.exists(T('tools', 'meta.json')) else {}
films = d['f']
for i, f in enumerate(films):
    m = meta.get(str(i), [None, None])
    del f[4:]
    f += [m[0], m[1]]
# Doppelte zusammenlegen: Filme mit gleichem Haupttitel -> erster Eintrag gewinnt
first = {}
remap = {}
for i, f in enumerate(films):
    k = norm(f[0])
    if k in first:
        j = first[k]
        remap[i] = j
        for x in (2, 4, 5):
            if not films[j][x] and f[x]:
                films[j][x] = f[x]
    else:
        first[k] = i
for s in d['s']:
    s[0] = remap.get(s[0], s[0])
d['u'] = d.get('u') or '2026-11-14'
html = open(T('template.html')).read().replace('__DATA__', json.dumps(d, ensure_ascii=False))
head = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="apple-mobile-web-app-capable" content="yes"></head><body style="margin:0">')
open(T('index.html'), 'w').write(head + html + '</body></html>')
print('index.html gebaut:', len(films), 'Filme,', len(remap), 'Doppelte zusammengelegt,', len(d['s']), 'Vorstellungen')
