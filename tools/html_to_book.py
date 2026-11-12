# يحوّل ملف شرح HTML دلالي (h1/h2/h3/p/ul/ol/table/div.co) إلى كتاب JSON بكتل غنية.
# الاستخدام: python3 html_to_book.py input.html out_dir book-id "العنوان"
import re, sys, json
from html.parser import HTMLParser

VOID = {'br', 'img', 'hr', 'input', 'meta', 'link'}
class N:
    def __init__(s, tag, attrs, parent): s.tag, s.attrs, s.kids, s.parent = tag, dict(attrs), [], parent
    def cls(s): return (s.attrs.get('class') or '').split()
class P(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=True); s.root = N('root', [], None); s.cur = s.root
    def handle_starttag(s, tag, attrs):
        n = N(tag, attrs, s.cur); s.cur.kids.append(n)
        if tag not in VOID: s.cur = n
    def handle_endtag(s, tag):
        c = s.cur
        while c is not None and c.tag != tag: c = c.parent
        if c is not None and c.parent is not None: s.cur = c.parent
    def handle_data(s, d): s.cur.kids.append(d)

KEEP = {'b', 'strong', 'i', 'em', 'u', 'mark', 'br'}
def inline(n):
    out = []
    for k in n.kids:
        if isinstance(k, str): out.append(k.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        else:
            if k.tag == 'span' and 'sp' in k.cls(): continue          # فواصل مخفية للطباعة
            inner = inline(k)
            if k.tag in KEEP: out.append('<%s>%s</%s>' % (k.tag, inner, k.tag) if k.tag != 'br' else '<br>')
            else: out.append(inner)
    return re.sub(r'\s+', ' ', ''.join(out)).strip()
def text(h): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h)).strip()
def find(n, pred, out=None):
    out = [] if out is None else out
    for k in n.kids:
        if isinstance(k, N):
            if pred(k): out.append(k)
            find(k, pred, out)
    return out

src, outdir, bid, title = sys.argv[1:5]
raw = open(src, encoding='utf8', errors='replace').read()
raw = re.sub(r'data:[a-z/+\-]+;base64,[A-Za-z0-9+/=]+', 'data:', raw)
p = P(); p.feed(raw)
doc = find(p.root, lambda n: n.attrs.get('id') == 'doc')[0]
review = [k for k in doc.kids if isinstance(k, N) and 'review-appendix' in k.cls()]

part, chapter, subs, cur = '', None, [], None
def newsub(t): 
    global cur; cur = {'title': t, 'paragraphs': []}; subs.append(cur); return cur
newsub('مقدمة الفصل')
cnt = {'n': 0}
def add(b):
    cnt['n'] += 1; b['id'] = 'b%03d' % cnt['n']; cur['paragraphs'].append(b)

for n in doc.kids:
    if not isinstance(n, N) or n.tag in ('img', 'style', 'script') or n.attrs.get('id') == 'bar' or n in review: continue
    c = n.cls()
    if 'dt-k' in c: part = text(inline(n)); continue
    if 'h1w' in c:
        h = find(n, lambda x: x.tag == 'h1')[0]; t = text(inline(h))
        if 'doc-title' in h.cls(): chapter = t
        else: newsub(t)
        continue
    if n.tag == 'h2': add({'t': 'h2', 'h': inline(n)}); continue
    if n.tag in ('h3', 'h4'):
        add({'t': n.tag, 'h': inline(n)}); continue
    if n.tag == 'p': add({'t': 'p', 'h': inline(n)}); continue
    if n.tag in ('ul', 'ol'):
        items = [inline(li) for li in n.kids if isinstance(li, N) and li.tag == 'li']
        add({'t': n.tag, 'items': items}); continue
    if n.tag == 'table':
        rows = [[inline(td) for td in tr.kids if isinstance(td, N)] for tr in find(n, lambda x: x.tag == 'tr')]
        add({'t': 'table', 'head': rows[0], 'rows': rows[1:]}); continue
    if 'co' in c:
        kind = [x for x in c if x.startswith('co-')]
        lab = find(n, lambda x: 'co-h' in x.cls()); body = find(n, lambda x: 'co-b' in x.cls())
        add({'t': 'co', 'k': (kind[0][3:] if kind else 'note'), 'l': text(inline(lab[0])) if lab else '', 'h': inline(body[0]) if body else '', 'q': 'quote' in c}); continue
    print('تجاهلت عنصرًا:', n.tag, c, text(inline(n))[:50], file=sys.stderr)

subs = [s for s in subs if s['paragraphs']]
book = {'id': bid, 'title': title, 'subtitle': 'دفعة أولى: شرح مملوك', 'author': '', 'publisher': '', 'lang': 'ar', 'edition': 'تجريبي', 'version': 1,
        'structure': {'parts': [{'title': part, 'sections': [{'title': '', 'chapters': [{'title': chapter, 'subsections': subs}]}]}]}}
json.dump(book, open('%s/books/%s.json' % (outdir, bid), 'w', encoding='utf8'), ensure_ascii=False, indent=1)

qs = []
if review:
    for a in find(review[0], lambda x: x.tag == 'article'):
        qt = find(a, lambda x: 'review-question-text' in x.cls())[0]
        op = find(a, lambda x: 'review-options' in x.cls())[0]
        kind = op.attrs.get('data-kind', 'mcq')
        opts = []
        for ch in [x for x in op.kids if isinstance(x, N)]:
            lab = find(ch, lambda x: 'review-choice-label' in x.cls())
            opts.append(text(inline(ch)).replace(text(inline(lab[0])), '', 1).strip() if lab else text(inline(ch)))
        qs.append({'n': a.attrs.get('data-question'), 'kind': kind, 'text': text(inline(qt)), 'options': opts})
json.dump(qs, open('%s/tools/_raw_questions.json' % outdir, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('blocks', cnt['n'], 'subs', len(subs), 'questions', len(qs))
