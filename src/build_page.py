import re, json, os
D = '/tmp/claude-0/-home-claude/3e82b8c1-cb2a-5e89-b808-4bb52880589d/scratchpad/milan-data/'
# Built-in example places: (id, button label, file, name shown on the page)
def HEAT(stem):
    h = D + stem + '-heat.threadlands.json'
    return h if os.path.exists(h) else D + stem + '.threadlands.json'

PLACES = [
    ('milan', 'Milan, Italy', HEAT('milan-reg'), 'Milan'),
    ('bangkok', 'Bangkok, Thailand', HEAT('bkk-reg'), 'Bangkok'),
]
import os
if os.path.exists(D + 'sf-reg.threadlands.json'):
    PLACES.insert(1, ('san-francisco', 'San Francisco', HEAT('sf-reg'), 'San Francisco'))
ex = []
for pid, label, path, name in PLACES:
    d = json.load(open(path))
    if d.get('name') != name:
        d['local_name'] = d.get('name')
        d['name'] = name
    EXTRA = {'san-francisco': "Most of San Francisco's drinking water comes from Hetch Hetchy Reservoir in Yosemite, about 260 km east, outside this basin. The water thread shows local drainage to the Bay."}
    if pid in EXTRA and d.get('regional'):
        d['regional'].setdefault('notes', []).insert(0, EXTRA[pid])
    ex.append({'id': pid, 'label': label, 'data': d})
exs = json.dumps(ex, separators=(',', ':'), ensure_ascii=False)
t = open('template2.html').read(); m = open('model2.js').read(); demo = open('demo-place.json').read()
for s in (m, demo, exs):
    assert '</script' not in s.lower()
body = t.replace('/*MODEL*/', m).replace('/*DEMO*/', demo).replace('/*EXAMPLES*/', exs)
cut = body.index('</style>') + len('</style>')
doc = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}</style>\n'
       + body[:cut] + '\n</head>\n<body>\n' + body[cut:] + '\n</body>\n</html>\n')
open('index.html', 'w').write(doc)
for i, s in enumerate(re.findall(r'<script>(.*?)</script>', doc, re.S)): open(f'chk{i}.js', 'w').write(s)
print(len(doc) // 1024, 'KB;', ', '.join(p[1] for p in PLACES))
