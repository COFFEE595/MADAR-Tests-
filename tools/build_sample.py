# تحويل بيانات النموذج القديم (الجانب العربي فقط) إلى كتاب JSON تجريبي + 50 سؤالًا
import json, re, random, sys
src, outdir = sys.argv[1], sys.argv[2]
random.seed(7)
line = open(src, encoding='utf8').read().split('\n')[1372]
d = json.loads(line.split('=', 1)[1].strip().rstrip(';'))
HEAD = re.compile(r'^\s*(?:[IVX]+\.|[A-Z]\.|\d+\.|[أ-ي]\s*[-.])\s+\S')
def is_head(t):
    t = t.strip()
    if len(t) < 130 and HEAD.match(t) and not t.endswith(('.', '؛')): return True
    return len(t) < 20 and not re.search(r'[.،؛:!؟?]', t)   # سطر قصير بلا ترقيم = عنوان
chapters = []
for ci, c in enumerate(d['chapters']):
    subs, cur = [], {'title': 'مقدمة الفصل', 'paragraphs': []}
    for b in c['blocks']:
        if b['type'] != 'seq': continue
        for fr, ar in b['pairs']:
            if not ar: continue
            ar = ar.strip()
            if is_head(ar):
                if cur['paragraphs']: subs.append(cur)
                cur = {'title': ar, 'paragraphs': []}
            else: cur['paragraphs'].append(ar)
    if cur['paragraphs']: subs.append(cur)
    chapters.append({'title': 'الفصل %d: %s' % (ci + 1, c['tar']), 'subsections': subs})
book = {'id': 'intro-law-sample', 'title': 'مدخل لدراسة القانون', 'subtitle': 'نسخة تجريبية للقالب',
        'author': '', 'publisher': '', 'lang': 'ar', 'edition': 'تجريبي',
        'structure': {'parts': [{'title': 'الباب الأول: مدخل عام', 'sections': [{'title': 'القسم الأول: فروع القانون', 'chapters': chapters}]}]}}
json.dump(book, open(outdir + '/books/intro-law-sample.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
# أسئلة المصطلحات
terms = []
for g in d['glossarySections']:
    for t in g['terms']:
        if t.get('tar') and t.get('dar') and len(t['dar']) > 25: terms.append((g['tar'], t['tar'].strip(), t['dar'].strip()))
random.shuffle(terms)
qs = []
def short(s, n=150): return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'
for i, (sec, term, dfn) in enumerate(terms[:50]):
    pool = [t for t in terms if t[1] != term]
    if i % 2 == 0:
        opts = [term] + [t[1] for t in random.sample([t for t in pool if t[0] == sec] or pool, 3)]
        random.shuffle(opts)
        qs.append({'id': 'q-%03d' % (i + 1), 'type': 'mcq', 'principle': sec, 'text': 'المصطلح الذي يدل على: «%s»' % short(dfn), 'options': opts, 'correct': opts.index(term), 'explanation': 'التعريف المذكور هو تعريف «%s».' % term})
    else:
        opts = [short(dfn, 110)] + [short(t[2], 110) for t in random.sample([t for t in pool if t[0] == sec] or pool, 3)]
        random.shuffle(opts)
        qs.append({'id': 'q-%03d' % (i + 1), 'type': 'mcq', 'principle': sec, 'text': 'ما المقصود بمصطلح «%s»؟' % term, 'options': opts, 'correct': opts.index(short(dfn, 110)), 'explanation': dfn})
json.dump({'bookId': book['id'], 'questions': qs}, open(outdir + '/questions/intro-law-sample.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(len(chapters), sum(len(c['subsections']) for c in chapters), sum(len(s['paragraphs']) for c in chapters for s in c['subsections']), len(qs))
