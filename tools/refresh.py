"""Kinoprogramm Winterthur neu laden – ein Befehl für alles.

Aufruf (im Repo-Ordner):  python3 -I tools/refresh.py [TAGE]   (Standard 30)
Danach: python3 -I tools/covers.py tools/program.json && python3 -I tools/build.py
        → index.html prüfen (posters/FEHLT.txt muss leer sein), committen, pushen.

Quellen:
- Kiwi Loge, Kiwi Center, Maxx: https://www.cineman.ch/kinoprogramm/winterthur/?date=JJJJ-MM-TT
- Kino Cameo: https://www.kinocameo.ch/spielplan (Zeiten in UTC, werden nach Zürich umgerechnet)
Schreibt tools/program.json im App-Format und tools/meta.json (Länge, Kinostart, Genres, Regie, Produktion, Erstaufführung).
"""
import json, os, re, sys, html, subprocess, unicodedata, urllib.parse
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh) Chrome/130"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TZ = ZoneInfo('Europe/Zurich')
CIN = ['Kiwi Center', 'Kiwi Loge', 'Maxx', 'Cameo']
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
MON = {'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
       'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12}


def get(url):
    return subprocess.run(['curl', '-sL', '-m', '30', '-A', UA, '-H', 'Accept-Language: de-CH', url],
                          capture_output=True).stdout.decode('utf8', 'ignore')


def norm(t):
    t = unicodedata.normalize('NFKD', t.lower())
    t = re.split(r'\s[(–-]\s?', t)[0]
    return re.sub(r'[^a-z0-9]', '', t)


def txt(x):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', x))).strip()


def cinema_index(name):
    n = name.lower()
    if 'loge' in n: return 1
    if 'maxx' in n: return 2
    if 'cameo' in n: return 3
    return 0


now = datetime.now(TZ)
end = (now + timedelta(days=DAYS)).date()
films, order, shows = {}, [], []


def film_id(key, title, url, genre, poster):
    if key not in films:
        films[key] = dict(i=len(order), title=title, url=url, genre=genre[:60], poster=poster)
        order.append(key)
    return films[key]['i']


# 1) Cineman: Kiwi Loge, Kiwi Center, Maxx
dates = [(now.date() + timedelta(days=k)).isoformat() for k in range(DAYS + 1)]
pages = dict(zip(dates, ThreadPoolExecutor(6).map(lambda d: get(f'https://www.cineman.ch/kinoprogramm/winterthur/?date={d}'), dates)))
for date, page in pages.items():
    soup = BeautifulSoup(page, 'html.parser')
    for h2 in soup.select('h2.headline'):
        a = h2.find('a', href=re.compile(r'/kinoprogramm/theatre/'))
        if not a: continue
        ci = cinema_index(a.get_text(strip=True))
        if ci == 3: continue  # Cameo kommt vom eigenen Spielplan
        cont = h2.find_next_sibling('div', class_='showtimes')
        if not cont: continue
        for mv in cont.select('div.showtimes-movie'):
            h4 = mv.select_one('h4 a')
            if not h4: continue
            title = h4.get_text(strip=True)
            url = 'https://www.cineman.ch' + h4['href']
            img = mv.select_one('img[data-src]')
            ps = h4.find_parent('div').find_all('p')
            fi = film_id(norm(title), title, url, ps[0].get_text(strip=True) if ps else '', img['data-src'] if img else '')
            for it in mv.select('div.showtimes-list-item'):
                p = it.find_all('p')
                info = re.sub(r'\s+', ' ', p[1].get_text(' ', strip=True)) if len(p) > 1 else ''
                parts = [x.strip() for x in info.split('–')]
                for t in re.findall(r'\d{1,2}:\d{2}', p[0].get_text(strip=True)):
                    shows.append([fi, ci, date, t.zfill(5), parts[1] if len(parts) > 1 else '', parts[0] if parts else '', ' '.join(parts[3:])])

# 2) Kino Cameo
soup = BeautifulSoup(get('https://www.kinocameo.ch/spielplan'), 'html.parser')
for tr in soup.select('tr.views-field-row'):
    a = tr.select_one('td.views-field-title a')
    tm = tr.select('time')
    if not a or len(tm) < 2: continue
    full = re.sub(r'\s+', ' ', a.get_text(' ', strip=True))
    title, _, extra = [x.strip() for x in full.partition(' / ')]
    dt = datetime.fromisoformat(tm[1]['datetime'].replace('Z', '+00:00')).astimezone(TZ)
    if dt.date() > end: continue
    fi = film_id(norm(title), title, 'https://www.kinocameo.ch' + a['href'], 'Programmkino', '')
    shows.append([fi, 3, dt.date().isoformat(), dt.strftime('%H:%M'), '', '', extra])

# nur kommende Vorstellungen, Datum als MM-TT
nowkey = now.strftime('%Y-%m-%d %H:%M')
shows = [s for s in shows if f'{s[2]} {s[3]}' >= nowkey]
shows.sort(key=lambda s: (s[2], s[3], s[1]))
for s in shows: s[2] = s[2][5:]
F = [[films[k]['title'], films[k]['genre'], films[k]['poster'], films[k]['url']] for k in order]
json.dump(dict(f=F, s=shows, u=now.date().isoformat()), open(os.path.join(ROOT, 'tools', 'program.json'), 'w'), ensure_ascii=False)
print(len(F), 'Filme,', len(shows), 'Vorstellungen bis', end)


# 3) Metadaten: Cineman-Filmseite (auch für Cameo-Filme per Suche) + TMDB-Erstaufführung
def cineman_page(f):
    if 'cineman.ch/movie' in f[3]: return f[3]
    h = get('https://www.cineman.ch/finder/?q=' + urllib.parse.quote(re.split(r'\s[(–/]', f[0])[0]))
    for p in list(dict.fromkeys(re.findall(r'href="(/movie/\d{4}/[^/"]+/)"', h)))[:6]:
        pg = get('https://www.cineman.ch' + p)
        t = re.search(r'<title>Film (.*?) - Cineman', pg)
        if t and norm(t.group(1)) == norm(f[0]): return 'https://www.cineman.ch' + p
    return None


def meta(i):
    f = F[i]; r = {}
    url = cineman_page(f); year = None
    if url:
        h = get(url)
        m = re.search(r'(\d{2,3})\s*min\.', h); r['rt'] = int(m.group(1)) if m else None
        m = re.search(r'Deutschschweiz:</strong>\s*(\d{1,2})\.\s*(\w+)\s+(\d{4})', h)
        if m and m.group(2) in MON: r['rel'] = f'{m.group(3)}-{MON[m.group(2)]:02d}-{int(m.group(1)):02d}'
        g = re.search(r'<h5 class="large">Genre</h5>(.*?)<hr>', h, re.S)
        if g: r['genres'] = [txt(x) for x in re.findall(r'label-genre">(.*?)</span>', g.group(1))]
        m = re.search(r'>\s*([^<>]{2,60}?)\s+(\d{4})\s+–\s+\d+\s*min\.', h)
        if m: r['land'] = m.group(1).strip().split('\n')[-1].strip(); year = r['year'] = m.group(2)
        for k, n in (('regie', 2), ('darsteller', 3)):
            m = re.search(r'id="linkcollection-' + k + r'">(.*?)<!-- linkcollection', h, re.S)
            if m: r['regie' if k == 'regie' else 'cast'] = list(dict.fromkeys(txt(x) for x in re.findall(r'<strong>(.*?)</strong>', m.group(1))))[:n]
    q = re.split(r'\s[(–/]', f[0])[0]
    sh = get('https://www.themoviedb.org/search/movie?query=' + urllib.parse.quote(q))
    for p in list(dict.fromkeys(re.findall(r'href="/movie/(\d+)[^"?]*"', sh)))[:4]:
        pg = get(f'https://www.themoviedb.org/movie/{p}?language=de-DE')
        t = re.search(r'<title>(.*?) \((\d{4})\)', pg)
        if not (t and norm(html.unescape(t.group(1))) == norm(f[0]) and (not year or abs(int(t.group(2)) - int(year)) <= 1)): continue
        rh = txt(get(f'https://www.themoviedb.org/movie/{p}/releases?language=de-DE').replace('<td', '| <td'))
        best = None
        for m in re.finditer(r'(\d{2})\.(\d{2})\.(\d{4})\s*\|([^|]*)\|\s*([^|]*?)\s*\|([^|]*)\|([^|]*)', rh):
            iso = f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
            if not best or iso < best[0]: best = (iso, (m.group(7).strip() or m.group(6).strip()))
        if best:
            note = best[1]
            fm = re.match(r'^(.*?(Festival|Filmtage|Fortnight|Festa del Cinema di Roma))', note)
            r['prem'], r['premnote'] = best[0], (fm.group(1) if fm else ('' if ('Datum' in note or 'URL' in note) else note[:40]))
        if not r.get('genres'):
            g = re.search(r'<span class="genres">(.*?)</span>', pg, re.S)
            if g: r['genres'] = [txt(x) for x in re.findall(r'<a[^>]*>(.*?)</a>', g.group(1))]
        r.setdefault('year', t.group(2))
        break
    return str(i), r


M = dict(ThreadPoolExecutor(8).map(meta, range(len(F))))
old = {}
mp = os.path.join(ROOT, 'tools', 'meta_manual.json')  # Handkorrekturen nach Titel, überschreiben alles
if os.path.exists(mp):
    man = json.load(open(mp))
    for i, f in enumerate(F):
        if f[0] in man: M[str(i)].update(man[f[0]])
json.dump(M, open(os.path.join(ROOT, 'tools', 'meta.json'), 'w'), ensure_ascii=False)
print('Metadaten für', sum(1 for v in M.values() if v), 'Filme')
