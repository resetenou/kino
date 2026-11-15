"""Kinobande – Cover-Finder.

Aufruf:  python3 -I tools/covers.py tools/program.json
Ergebnis: jedes Cover liegt als posters/<nr>.jpg im Repo, program.json zeigt darauf.

Reihenfolge pro Film (erste Quelle, die ein HOCHFORMAT-Bild liefert, gewinnt):
  1. tools/overrides.json   – von Hand geprüfte Zuordnung (Titel -> Bild-URL oder posters/…)
  2. Bild aus dem Programm   – nur wenn es von Cineman stammt (Kino-Seiten liefern oft Standbilder)
  3. Cineman-Suche          – /finder/?q=Titel, gleicher Titel -> og:image der Filmseite
  4. TMDB-Suche             – gleicher Titel -> deutsches Plakat
  5. nichts                 – die App zeigt eine Titelkarte; der Film steht in posters/FEHLT.txt
Querformat (Breite >= Höhe / 1.2) wird immer verworfen: das sind Szenenbilder, keine Plakate.
"""
import json, os, re, subprocess, sys, unicodedata, urllib.parse, io, html
from PIL import Image

UA = "Mozilla/5.0 (Macintosh) Chrome/130"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'posters')


def get(url):
    r = subprocess.run(['curl', '-sL', '-m', '25', '-A', UA, '-H', 'Accept-Language: de-CH', url], capture_output=True)
    return r.stdout


def norm(t):
    t = unicodedata.normalize('NFKD', t.lower())
    t = re.split(r'\s[(–-]\s?', t)[0]
    return re.sub(r'[^a-z0-9]', '', t)


def poster_ok(data):
    try:
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        return h >= w * 1.2 and w >= 150, im
    except Exception:
        return False, None


def cineman(title):
    h = get('https://www.cineman.ch/finder/?q=' + urllib.parse.quote(re.split(r'\s[(–]', title)[0])).decode('utf8', 'ignore')
    for path in dict.fromkeys(re.findall(r'href="(/movie/\d{4}/[^/"]+/)"', h)):
        page = get('https://www.cineman.ch' + path).decode('utf8', 'ignore')
        t = re.search(r'<title>Film (.*?) - Cineman', page)
        m = re.search(r'og:image" content="([^"]+)', page)
        if t and m and norm(t.group(1)) == norm(title) and 'cinemanteaser' in m.group(1):
            yield m.group(1).replace('http://', 'https://')


def tmdb(title):
    h = get('https://www.themoviedb.org/search/movie?query=' + urllib.parse.quote(re.split(r'\s[(–]', title)[0])).decode('utf8', 'ignore')
    for path in list(dict.fromkeys(re.findall(r'href="(/movie/\d+[^"?]*)"', h)))[:4]:
        page = get('https://www.themoviedb.org' + path + '?language=de-DE').decode('utf8', 'ignore')
        en = get('https://www.themoviedb.org' + path + '?language=en-US').decode('utf8', 'ignore')
        names = [x.group(1) for x in (re.search(r'<title>(.*?) \(\d{4}\)', page), re.search(r'<title>(.*?) \(\d{4}\)', en)) if x]
        m = re.search(r'og:image" content="([^"]+/w500/[^"]+)', page)
        if m and any(norm(html.unescape(n)) == norm(title) for n in names):
            yield m.group(1).replace('/w500/', '/w342/')


def main(progf):
    d = json.load(open(progf))
    ov = json.load(open(os.path.join(ROOT, 'tools', 'overrides.json')))
    os.makedirs(OUT, exist_ok=True)
    missing = []
    for i, f in enumerate(d['f']):
        title, src = f[0], f[2]
        cands = []
        if title in ov: cands.append(ov[title])
        if src and 'cinergy' in src: cands.append(src)
        found = None
        for c in cands + [x for gen in (cineman(title), tmdb(title)) for x in gen]:
            data = open(os.path.join(ROOT, c), 'rb').read() if c.startswith('posters/') else get(c)
            ok, im = poster_ok(data)
            if ok:
                found = im
                break
        if found:
            im = found.convert('RGB')
            im.thumbnail((400, 600))
            im.save(os.path.join(OUT, f'{i}.jpg'), quality=85)
            f[2] = f'posters/{i}.jpg'
        else:
            f[2] = ''
            missing.append(title)
        print('OK ' if found else '-- ', i, title, flush=True)
    json.dump(d, open(progf, 'w'), ensure_ascii=False)
    open(os.path.join(OUT, 'FEHLT.txt'), 'w').write('\n'.join(missing))
    print(len(d['f']) - len(missing), 'von', len(d['f']), 'Covers;', 'fehlt:', missing)


if __name__ == '__main__':
    main(sys.argv[1])
