/* generators.js — مولّدات الأسئلة وجلسات المراجعة المتباعدة (عربي فقط، بلا اعتماد على DOM) */
(function (root) {
  'use strict';
  const rnd = n => Math.floor(Math.random() * n);
  function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = rnd(i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; }

  /* تطبيع عربي موحّد للبحث والمقارنة */
  function norm(s) {
    return String(s || '').replace(/[ً-ٰٟـ]/g, '')
      .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه')
      .replace(/[^؀-ۿa-zA-Z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  }

  /* ---------- مراجعة متباعدة (صناديق لايتنر) ---------- */
  const DAY = 86400000;
  const BOX_DAYS = [0, 1, 2, 4, 8, 16, 32];
  function srsUpdate(rec, ok, now) {
    now = now || Date.now();
    let box = rec && rec.box ? rec.box : 1;
    box = ok ? Math.min(BOX_DAYS.length - 1, box + 1) : 1;
    return { box: box, next: now + BOX_DAYS[box] * DAY, last: now };
  }

  /* ---------- تطبيع سؤال بنك الأسئلة (خلط الخيارات مع حفظ الإجابة) ---------- */
  function normalizeMcq(q) {
    if (!q || !Array.isArray(q.options) || q.options.length < 2) return null;
    const tf = q.type === 'tf', all = q.options.map((_, i) => i), idx = tf ? all : shuffle(all);   // صح/خطأ: يبقى الترتيب ثابتًا
    return {
      id: q.id, type: tf ? 'tf' : 'mcq', text: q.text, principle: q.principle || '', explanation: q.explanation || '',
      options: idx.map(i => q.options[i]), correct: idx.indexOf(q.correct), path: q.path || null, paragraphIndex: q.paragraphIndex, anchor: q.anchor || null
    };
  }

  /* ---------- مولّد الفراغ (cloze) من فقرات الكتاب ---------- */
  const WORD = /[\u0621-\u064A]{5,}/g;
  /* خريطة التكرار + صيغة العرض الأصلية لكل كلمة مطبّعة (حتى لا تظهر المشتتات بإملاء مختلف عن الإجابة) */
  function freqMap(paras) {
    const f = Object.create(null), disp = Object.create(null);
    paras.forEach(p => {
      const plain = p.text.replace(/[\u064B-\u065F\u0670\u0640]/g, '');
      (plain.match(WORD) || []).forEach(w => { const n = norm(w); f[n] = (f[n] || 0) + 1; if (!disp[n]) disp[n] = w; });
    });
    Object.defineProperty(f, '__disp', { value: disp, enumerable: false });
    return f;
  }
  /* paras: [{key,text}] — يرجع سؤالًا أو null */
  function clozeQ(p, freq, pool) {
    const words = (p.text.match(/[ء-يً-ٟ]{5,}/g) || []);
    const okw = words.filter(w => { const n = norm(w); return n.length >= 5 && !/^(الذي|التي|الذين|بالنسبه|ويجوز|وذلك|حيث|كذلك|اللذان)/.test(n); });
    /* نفضّل الكلمات النادرة (أكثر دلالة)، وإن لم توجد نقبل أي كلمة مناسبة */
    const rare = okw.filter(w => freq[norm(w)] <= 6), cand = rare.length ? rare : okw;
    if (!cand.length) return null;
    const target = cand[rnd(cand.length)], tn = norm(target);
    const present = new Set(words.map(norm));
    /* المشتتات: كلمات من الكتاب غير موجودة في الفقرة، الأقرب طولًا للإجابة أولًا */
    const sim = w => Math.abs(w.length - tn.length) - (w.slice(0, 2) === tn.slice(0, 2) ? 1.5 : 0) - (w.slice(-2) === tn.slice(-2) ? 1.5 : 0) - (w.slice(0, 2) === 'ال' && tn.slice(0, 2) === 'ال' ? 1 : 0);
    const near = pool.filter(w => w !== tn && !present.has(w)).map(w => [sim(w) + Math.random() * 1.2, w]).sort((a, b) => a[0] - b[0]).slice(0, 10).map(x => x[1]);
    if (near.length < 3) return null;
    const d = shuffle(near).slice(0, 3);
    const opts = shuffle([tn].concat(d));
    const blank = p.text.replace(target, '＿＿＿＿＿');
    if (blank === p.text) return null;
    /* نعرض الخيارات بصيغتها الأصلية (غير المطبّعة) حين تتوفر */
    return { id: 'c:' + p.key + ':' + tn, type: 'cloze', text: 'أكمل الفراغ في العبارة التالية:\n«' + blank + '»', options: opts.map(o => o === tn ? target.replace(/[\u064B-\u065F\u0640]/g, '') : ((freq.__disp && freq.__disp[o]) || o)), correct: opts.indexOf(tn), principle: 'فراغ من نص الكتاب', explanation: 'الكلمة الصحيحة: «' + target + '».', key: p.key };
  }

  /* ---------- بناء جلسة ---------- */
  /* opts: {bank:[...], paras:[{key,text}], srs:{id:{box,next}}, answers:{id:{correct,at}}, n, mode} */
  function session(o) {
    const now = Date.now(), n = o.n || 10, mode = o.mode || 'mixed';
    const bank = (o.bank || []).filter(q => q && q.id);
    const srs = o.srs || {}, ans = o.answers || {};
    const due = bank.filter(q => srs[q.id] && srs[q.id].next <= now);
    const wrong = bank.filter(q => ans[q.id] && ans[q.id].correct === false);
    const fresh = bank.filter(q => !ans[q.id]);
    let pick = [];
    const add = list => shuffle(list).forEach(q => { if (pick.length < n && !pick.some(x => x.id === q.id)) pick.push(q); });
    if (mode === 'due') add(due);
    else if (mode === 'wrong') add(wrong);
    else { add(due); add(fresh); add(wrong); add(bank); }
    let out = pick.map(normalizeMcq).filter(Boolean);
    /* إكمال العدد بأسئلة فراغ مولَّدة من النص إن لم يكفِ البنك (وليس في وضع الأخطاء/المستحق) */
    if (out.length < n && mode === 'mixed' && o.paras && o.paras.length) {
      const freq = freqMap(o.paras), pool = Object.keys(freq);
      const ps = shuffle(o.paras.filter(p => p.text.length >= 70 && p.text.length <= 420));
      for (let i = 0; i < ps.length && out.length < n; i++) { const q = clozeQ(ps[i], freq, pool); if (q && !out.some(x => x.id === q.id)) out.push(q); }
    }
    return out;
  }

  root.GEN = { norm: norm, shuffle: shuffle, srsUpdate: srsUpdate, normalizeMcq: normalizeMcq, clozeQ: clozeQ, freqMap: freqMap, session: session, BOX_DAYS: BOX_DAYS };
})(typeof window !== 'undefined' ? window : globalThis);
