/* Module 1: gamified screening test. 32 short exercises adapted to English from the
   Dytective design (letters, syllables, words, pseudo-words, visual search, spelling,
   grammar, anagrams, segmentation, visual memory and dictation). Each exercise logs
   clicks, hits and misses; the server derives score, accuracy and miss rate. */
(function () {
  const SAY = (t, rate = 0.8) => new Promise(res => {
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(t);
      u.rate = rate; u.lang = 'en-IN';
      const v = speechSynthesis.getVoices().find(v => /en[-_](IN|GB|US)/i.test(v.lang));
      if (v) u.voice = v;
      u.onend = res; u.onerror = res; speechSynthesis.speak(u);
      setTimeout(res, 2500);
    } catch (e) { res(); }
  });
  const shuffle = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };

  const ITEMS = [
    ...[['e', ['a', 'c', 'o', 'u']], ['g', ['q', 'p', 'j', 'y']], ['b', ['d', 'p', 'q', 'h']], ['d', ['b', 'p', 'q', 'a']]]
      .map(([t, d], i) => ({ q: i + 1, type: 'mole', group: 'Letter sounds', say: t, target: t, distract: d, title: 'Tap every mole that shows the letter you hear' })),
    ...[['ba', ['da', 'pa', 'ab', 'bo', 'qa']], ['gar', ['gra', 'jar', 'gap', 'car', 'rag']], ['pla', ['pal', 'bla', 'lap', 'pra', 'qla']],
        ['bla', ['bal', 'dla', 'pla', 'lab', 'bra']], ['glis', ['gils', 'glys', 'clis', 'slig', 'gris']]]
      .map(([t, d], i) => ({ q: i + 5, type: 'tiles', group: 'Syllables', say: t, target: t, distract: d, title: 'Tap every card that matches the syllable you hear' })),
    ...[['bird', ['brid', 'drib', 'dird', 'berd']], ['play', ['paly', 'pley', 'plya', 'blay']], ['dog', ['god', 'bog', 'dgo', 'dop']], ['clap', ['calp', 'clip', 'lcap', 'clab']]]
      .map(([t, d], i) => ({ q: i + 10, type: 'tiles', group: 'Words', say: t, target: t, distract: d, title: 'Tap every card that matches the word you hear' })),
    ...[['F', 'E'], ['b', 'd'], ['p', 'q'], ['m', 'n']]
      .map(([t, d], i) => ({ q: i + 14, type: 'search', group: 'Visual search', target: t, distract: d, title: `Find every “${t}” hidden among the “${d}”` })),
    ...[['pamata', ['pamada', 'bamata', 'papata', 'pamta']], ['tefo', ['tefa', 'defo', 'tafo', 'tefe']], ['lumbis', ['lumpis', 'lumbes', 'lubmis', 'lunbis']], ['drasket', ['draskit', 'trasket', 'drakset', 'dresket']]]
      .map(([t, d], i) => ({ q: i + 18, type: 'tiles', group: 'Made-up words', say: t, target: t, distract: d, title: 'Tap every card that matches the made-up word you hear' })),
    { q: 22, type: 'fill', group: 'Spelling', title: 'Choose the missing letter', words: [['c_t', 'a', ['a', 'o', 'e', 'u']], ['sh_p', 'i', ['i', 'o', 'e', 'a']], ['b_d', 'e', ['e', 'a', 'i', 'o']], ['fr_g', 'o', ['o', 'a', 'i', 'u']]] },
    { q: 23, type: 'extra', group: 'Spelling', title: 'Tap the extra letter that should not be there', words: [['frriend', [1, 2]], ['schoool', [3, 4, 5]], ['housue', [4]], ['tabble', [2, 3]]] },
    { q: 24, type: 'wrong', group: 'Meaning', title: 'Tap the word that makes the sentence wrong', sents: [['The cat drank the warm mile', 5], ['She wore a warm coot today', 4], ['We went to the bark to play', 4]] },
    { q: 25, type: 'wrong', group: 'Grammar', title: 'Tap the small word that is wrong', sents: [['The book is in an table', 4], ['I am going for the market', 3], ['He sat on a garden', 2]] },
    { q: 26, type: 'extra', group: 'Spelling', title: 'Tap the wrong letter in each word', words: [['dook', [0]], ['jlass', [0]], ['sumny', [2]], ['penci1', [5]]] },
    { q: 27, type: 'anagram', group: 'Word building', title: 'Tap the letters in order to make a word', words: ['cat', 'sun', 'frog', 'seven'] },
    { q: 28, type: 'anagram', group: 'Word building', title: 'Tap the syllables in order to make a word', words: [['ta', 'ble'], ['mon', 'ster'], ['but', 'ter', 'fly'], ['ba', 'na', 'na']] },
    { q: 29, type: 'segment', group: 'Word building', title: 'Tap between letters to split the words', strings: ['thecatisbig', 'iliketoread'] },
    { q: 30, type: 'memory', group: 'Memory', title: 'Remember the letters, then tap them in the same order', seqs: ['bdp', 'qpdb', 'mnwu'] },
    { q: 31, type: 'dictation', group: 'Dictation', title: 'Listen and type the word', words: ['friend', 'because', 'little', 'school'] },
    { q: 32, type: 'dictation', group: 'Dictation', title: 'Listen and type the made-up word', words: ['danama', 'plint', 'brosk', 'tefim'] },
  ];

  class Game {
    constructor(root, opts) {
      this.root = root; this.secs = opts.seconds || 12; this.onDone = opts.onDone; this.onProgress = opts.onProgress || (() => {});
      this.items = opts.only ? ITEMS.filter(it => opts.only.includes(it.q)) : ITEMS;   // short form: a subset of exercises
      this.results = []; this.i = 0; this.t0 = Date.now();
    }
    start() { this.next(); }
    next() {
      if (this.i >= this.items.length) { this.onDone(this.results, (Date.now() - this.t0) / 1000); return; }
      const it = this.items[this.i];
      this.onProgress(this.i, this.items.length, it);
      this.cur = { q: it.q, clicks: 0, hits: 0, misses: 0 };
      this.root.innerHTML = '';
      const head = el('div', 'g-head');
      head.append(el('span', 'g-group', it.group), el('h3', 'g-title', it.title));
      const stage = el('div', 'g-stage'); const foot = el('div', 'g-foot');
      this.timerEl = el('div', 'g-timer'); foot.append(this.timerEl);
      if (it.say) { const b = el('button', 'btn ghost small', '🔊 Hear again'); b.onclick = () => SAY(it.say); foot.append(b); }
      const skip = el('button', 'btn ghost small', 'Next exercise'); skip.onclick = () => this.finish(); foot.append(skip);
      this.root.append(head, stage, foot);
      this[it.type](it, stage);
    }
    hit() { this.cur.clicks++; this.cur.hits++; }
    miss() { this.cur.clicks++; this.cur.misses++; }
    finish() {
      if (this.done) return; this.done = true;
      clearInterval(this.iv); clearTimeout(this.to); clearInterval(this.spawn);
      this.results.push(this.cur); this.i++;
      setTimeout(() => { this.done = false; this.next(); }, 250);
    }
    countdown(secs) {
      let left = secs; this.timerEl.textContent = `${left}s`;
      this.iv = setInterval(() => { left--; this.timerEl.textContent = `${Math.max(left, 0)}s`; if (left <= 0) this.finish(); }, 1000);
    }
    async mole(it, stage) {
      const grid = el('div', 'g-moles');
      const holes = [...Array(9)].map(() => { const h = el('button', 'mole'); grid.append(h); return h; });
      stage.append(grid); await SAY(it.say);
      holes.forEach(h => h.onclick = () => {
        if (!h.dataset.l) return;
        if (h.dataset.l === it.target) { this.hit(); h.classList.add('ok'); } else { this.miss(); h.classList.add('bad'); }
        h.dataset.l = ''; setTimeout(() => { h.textContent = ''; h.className = 'mole'; }, 220);
      });
      this.spawn = setInterval(() => {
        const free = holes.filter(h => !h.dataset.l); if (!free.length) return;
        const h = free[Math.floor(Math.random() * free.length)];
        const l = Math.random() < 0.4 ? it.target : it.distract[Math.floor(Math.random() * it.distract.length)];
        h.dataset.l = l; h.textContent = l; h.className = 'mole up';
        setTimeout(() => { if (h.dataset.l === l) { h.dataset.l = ''; h.textContent = ''; h.className = 'mole'; } }, 1300);
      }, 650);
      this.countdown(this.secs);
    }
    async tiles(it, stage) {
      const opts = shuffle([it.target, it.target, it.target, it.target, ...it.distract, ...shuffle(it.distract).slice(0, 3)]);
      const grid = el('div', 'g-tiles');
      opts.forEach(o => {
        const b = el('button', 'tile', o);
        b.onclick = () => { if (b.disabled) return; if (o === it.target) { this.hit(); b.classList.add('ok'); b.disabled = true; } else { this.miss(); b.classList.add('bad'); setTimeout(() => b.classList.remove('bad'), 300); }
          if (grid.querySelectorAll('.ok').length === 4) this.finish(); };
        grid.append(b);
      });
      stage.append(grid); await SAY(it.say); this.countdown(this.secs);
    }
    search(it, stage) {
      const n = 42, k = 5, pos = new Set(shuffle([...Array(n).keys()]).slice(0, k));
      const grid = el('div', 'g-search');
      for (let i = 0; i < n; i++) {
        const isT = pos.has(i); const b = el('button', 'cell', isT ? it.target : it.distract);
        b.onclick = () => { if (b.disabled) return; if (isT) { this.hit(); b.classList.add('ok'); b.disabled = true; } else { this.miss(); b.classList.add('bad'); setTimeout(() => b.classList.remove('bad'), 300); }
          if (grid.querySelectorAll('.ok').length === k) this.finish(); };
        grid.append(b);
      }
      stage.append(grid); this.countdown(this.secs + 6);
    }
    fill(it, stage) {
      let w = 0; const box = el('div', 'g-fill');
      const show = () => {
        if (w >= it.words.length) return this.finish();
        const [pat, ans, opts] = it.words[w]; box.innerHTML = '';
        box.append(el('div', 'g-word', pat.replace('_', ' _ ')));
        const row = el('div', 'g-row');
        shuffle(opts).forEach(o => { const b = el('button', 'tile', o); b.onclick = () => { if (o === ans) { this.hit(); w++; show(); } else { this.miss(); b.classList.add('bad'); } }; row.append(b); });
        box.append(row);
      };
      stage.append(box); show(); this.countdown(this.secs * 3);
    }
    extra(it, stage) {
      let w = 0; const box = el('div', 'g-fill');
      const show = () => {
        if (w >= it.words.length) return this.finish();
        const [word, good] = it.words[w]; box.innerHTML = ''; const row = el('div', 'g-letters');
        [...word].forEach((ch, i) => { const b = el('button', 'letter', ch); b.onclick = () => { if (good.includes(i)) { this.hit(); w++; show(); } else { this.miss(); b.classList.add('bad'); } }; row.append(b); });
        box.append(row);
      };
      stage.append(box); show(); this.countdown(this.secs * 3);
    }
    wrong(it, stage) {
      let s = 0; const box = el('div', 'g-fill');
      const show = () => {
        if (s >= it.sents.length) return this.finish();
        const [sent, bad] = it.sents[s]; box.innerHTML = ''; const row = el('div', 'g-sentence');
        sent.split(' ').forEach((wd, i) => { const b = el('button', 'wordbtn', wd); b.onclick = () => { if (i === bad) { this.hit(); s++; show(); } else { this.miss(); b.classList.add('bad'); } }; row.append(b); });
        box.append(row);
      };
      stage.append(box); show(); this.countdown(this.secs * 3);
    }
    anagram(it, stage) {
      let w = 0; const box = el('div', 'g-fill');
      const show = () => {
        if (w >= it.words.length) return this.finish();
        const parts = Array.isArray(it.words[w]) ? it.words[w] : [...it.words[w]];
        let k = 0; box.innerHTML = ''; const out = el('div', 'g-word', '…'); const row = el('div', 'g-row');
        shuffle(parts.map((p, i) => [p, i])).forEach(([p, i]) => {
          const b = el('button', 'tile', p);
          b.onclick = () => { if (b.disabled) return; if (p === parts[k]) { this.hit(); k++; b.disabled = true; b.classList.add('ok'); out.textContent = parts.slice(0, k).join(''); if (k === parts.length) { w++; setTimeout(show, 300); } } else { this.miss(); b.classList.add('bad'); setTimeout(() => b.classList.remove('bad'), 300); } };
          row.append(b);
        });
        box.append(out, row);
      };
      stage.append(box); show(); this.countdown(this.secs * 3);
    }
    segment(it, stage) {
      const answers = { thecatisbig: [3, 6, 8], iliketoread: [1, 5, 7] };
      let s = 0; const box = el('div', 'g-fill');
      const show = () => {
        if (s >= it.strings.length) return this.finish();
        const str = it.strings[s], good = answers[str]; let found = 0; box.innerHTML = ''; const row = el('div', 'g-letters seg');
        [...str].forEach((ch, i) => {
          row.append(el('span', 'segch', ch));
          if (i < str.length - 1) { const g = el('button', 'gap', ''); g.onclick = () => { if (g.disabled) return; if (good.includes(i + 1)) { this.hit(); g.disabled = true; g.classList.add('ok'); found++; if (found === good.length) { s++; setTimeout(show, 300); } } else { this.miss(); g.classList.add('bad'); setTimeout(() => g.classList.remove('bad'), 300); } }; row.append(g); }
        });
        box.append(row);
      };
      stage.append(box); show(); this.countdown(this.secs * 3);
    }
    memory(it, stage) {
      let r = 0; const box = el('div', 'g-fill');
      const show = () => {
        if (r >= it.seqs.length) return this.finish();
        const seq = [...it.seqs[r]]; box.innerHTML = ''; box.append(el('div', 'g-word big', seq.join(' ')));
        setTimeout(() => {
          box.innerHTML = ''; let k = 0; const out = el('div', 'g-word', '…'); const row = el('div', 'g-row');
          const pool = shuffle([...new Set([...seq, ...'bdpqmnwu'.split('')])]).slice(0, 8);
          seq.forEach(c => { if (!pool.includes(c)) pool[Math.floor(Math.random() * pool.length)] = c; });
          shuffle([...new Set(pool.concat(seq))]).forEach(c => { const b = el('button', 'tile', c); b.onclick = () => { if (c === seq[k]) { this.hit(); k++; out.textContent = seq.slice(0, k).join(' '); if (k === seq.length) { r++; setTimeout(show, 300); } } else { this.miss(); b.classList.add('bad'); setTimeout(() => b.classList.remove('bad'), 300); } }; row.append(b); });
          box.append(out, row);
        }, 3000);
      };
      stage.append(box); show(); this.countdown(this.secs * 4);
    }
    dictation(it, stage) {
      let w = 0; const box = el('div', 'g-fill');
      const show = async () => {
        if (w >= it.words.length) return this.finish();
        box.innerHTML = ''; const inp = el('input', 'g-input'); inp.autocomplete = 'off'; inp.spellcheck = false;
        const ok = el('button', 'btn small', 'Check'); const again = el('button', 'btn ghost small', '🔊 Hear word');
        const word = it.words[w]; again.onclick = () => SAY(word, 0.7);
        const submit = () => { const v = inp.value.trim().toLowerCase(); if (!v) return; if (v === word) this.cur.hits++; else this.cur.misses++; w++; show(); };
        ok.onclick = submit; inp.onkeydown = e => { if (e.key === 'Enter') return submit(); if (e.key.length === 1 || e.key === 'Backspace') this.cur.clicks++; };
        const row = el('div', 'g-row'); row.append(inp, ok, again); box.append(row); inp.focus(); await SAY(word, 0.7);
      };
      stage.append(box); show(); this.countdown(this.secs * 4);
    }
  }
  const QUICK = [4, 9, 11, 19, 20, 22, 24, 25, 26, 28];   // same 10 exercises as the short-form model
  window.ScreeningGame = { Game, ITEMS, SAY, QUICK };
})();
