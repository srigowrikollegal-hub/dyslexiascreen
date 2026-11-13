/* DyslexiaScreen single-page app: routing and views. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const view = () => $('#view');
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pct = (x, d = 1) => x == null ? '–' : (100 * x).toFixed(d) + '%';
  const fmtDate = s => new Date(s + (s.endsWith('Z') ? '' : 'Z')).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  let USER = null;
  const MODNAME = { game: 'Gamified test', handwriting: 'Handwriting', eye: 'Eye tracking' };
  const MODICON = { game: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="6" width="18" height="12" rx="4"/><path d="M8 10v4M6 12h4"/><circle cx="15.5" cy="11" r=".6"/><circle cx="17.5" cy="13" r=".6"/></svg>', handwriting: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15.5 4.5l4 4L9 19H5v-4z"/><path d="M13.5 6.5l4 4"/></svg>', eye: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>' };

  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = msg; t.className = 'toast show' + (bad ? ' bad' : '');
    clearTimeout(t._h); t._h = setTimeout(() => t.className = 'toast', 3200);
  }
  function busy(btn, on, label) { if (!btn) return; if (on) { btn._t = btn.textContent; btn.disabled = true; btn.textContent = label || 'Working…'; } else { btn.disabled = false; btn.textContent = btn._t; } }
  function riskBadge(r, mod) {
    if (r == null) return '<span class="badge muted">Not tested</span>';
    const cut = mod === 'game' ? 0.11 : 0.5;
    const cls = r >= cut ? (r >= Math.min(cut * 2.5, 0.75) ? 'high' : 'mid') : 'low';
    return `<span class="badge ${cls}">${pct(r)}</span>`;
  }
  function gauge(v) {
    const a = Math.max(0, Math.min(1, v)); const ang = -90 + 180 * a;
    return `<svg viewBox="0 0 200 118" class="gauge"><defs><linearGradient id="gg" x1="0" x2="1"><stop offset="0" stop-color="var(--ok)"/><stop offset=".5" stop-color="var(--warn)"/><stop offset="1" stop-color="var(--bad)"/></linearGradient></defs>
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="var(--line)" stroke-width="16" stroke-linecap="round"/>
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="url(#gg)" stroke-width="16" stroke-linecap="round" stroke-dasharray="${251.3 * a} 999"/>
      <g transform="rotate(${ang} 100 100)"><line x1="100" y1="100" x2="100" y2="34" stroke="var(--ink)" stroke-width="4" stroke-linecap="round"/></g><circle cx="100" cy="100" r="7" fill="var(--ink)"/>
      </svg>`;
  }

  // ---------------------------------------------------------------- auth views
  const BOOK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 7c-2-1.6-5-2.1-8.5-1.6v12.4c3.5-.5 6.5 0 8.5 1.6 2-1.6 5-2.1 8.5-1.6V5.4C17 4.9 14 5.4 12 7z"/><path d="M12 7v12.4"/><path d="M12 2.2v1.6M9.6 3l.6 1.1M14.4 3l-.6 1.1"/></svg>';
  function authView(mode) {
    document.body.classList.add('bare');
    view().innerHTML = `
    <section class="landing">
      <div class="emblem">${BOOK}</div><div class="l-stem"></div>
      <div class="l-content"><h1>DyslexiaScreen</h1>
        <p>Early dyslexia risk screening with a reading game, handwriting analysis and webcam eye tracking, combined into one Reading Difficulty Index</p></div>
      <div class="l-stem"></div>
      <nav class="l-nav"><button data-open="login">Log in</button><button data-open="register">Create account</button><button data-open="about">About</button></nav>
      <p class="l-foot">Capstone project · Information Science and Engineering · DSATM Bengaluru</p>
    </section>
    <div class="article-wrap" id="artWrap"><article class="article" id="art"></article></div>`;
    const forms = {
      login: () => `<h2 class="major">Log in</h2><form id="authForm">
        <label>Email<input name="email" type="email" required autocomplete="email"></label>
        <label>Password<input name="password" type="password" required minlength="6" autocomplete="current-password"></label>
        <p class="err" id="authErr"></p><button class="btn wide" type="submit">Log in</button>
        <p class="muted center small">New here? <a href="#" data-open="register">Create an account</a></p></form>`,
      register: () => `<h2 class="major">Create account</h2><form id="authForm">
        <label>Full name<input name="name" required minlength="2" autocomplete="name"></label>
        <label>Role<select name="role"><option value="teacher">Teacher</option><option value="parent">Parent</option><option value="clinician">Clinician</option><option value="researcher">Researcher / developer</option></select></label>
        <label>Email<input name="email" type="email" required autocomplete="email"></label>
        <label>Password<input name="password" type="password" required minlength="6" autocomplete="new-password"></label>
        <p class="err" id="authErr"></p><button class="btn wide" type="submit">Create account</button>
        <p class="muted center small">Already have an account? <a href="#" data-open="login">Log in</a></p></form>`,
      about: () => `<h2 class="major">About</h2>
        <p>DyslexiaScreen helps teachers and parents spot children who may have dyslexia early, so they can be referred to a psychologist for a full assessment.</p>
        <ul><li><b>Reading game:</b> short letter, sound and word exercises scored by an XGBoost and Extra Trees ensemble.</li>
        <li><b>Handwriting:</b> a convolutional neural network checks letters for reversals such as b and d.</li>
        <li><b>Eye tracking:</b> the laptop webcam follows the eyes while the child reads three short texts.</li></ul>
        <p>Each result comes with its reasons, and the three combine into one Reading Difficulty Index.</p>
        <p class="small">K R Srigowri and Rajshree Gupta, guided by Dr. Vanajaroselin Chirchi.</p>`,
    };
    const open = k => {
      $('#art').innerHTML = `<button class="close" aria-label="Close">×</button>${forms[k]()}`;
      document.body.classList.add('article-open');
      $('#art .close').onclick = close; $('#art').querySelectorAll('[data-open]').forEach(a => a.onclick = e => { e.preventDefault(); open(a.dataset.open); });
      const f = $('#authForm'); if (!f) return;
      f.querySelector('input').focus();
      f.onsubmit = async e => {
        e.preventDefault(); const fd = Object.fromEntries(new FormData(f)); const b = f.querySelector('button[type=submit]');
        busy(b, true, k === 'login' ? 'Logging in…' : 'Creating…');
        try { const r = await API.post(`/api/auth/${k}`, fd); API.setToken(r.token); USER = r.user; document.body.classList.remove('article-open'); location.hash = '#/'; }
        catch (err) { $('#authErr').textContent = err.message; } finally { busy(b, false); }
      };
    };
    const close = () => document.body.classList.remove('article-open');
    view().querySelectorAll('.l-nav [data-open]').forEach(b => b.onclick = () => open(b.dataset.open));
    $('#artWrap').onclick = e => { if (e.target.id === 'artWrap') close(); };
    document.onkeydown = e => { if (e.key === 'Escape') close(); };
    if (mode === 'register') open('register');
  }

  // ---------------------------------------------------------------- dashboard
  async function dashboard() {
    const d = await API.get('/api/dashboard');
    view().innerHTML = `
      <header class="page-head"><div><h1>Hello, ${esc(USER.name.split(' ')[0])}</h1><p class="muted">Here is your screening overview.</p></div>
        <a class="btn" href="#/children/new">Add a child</a></header>
      <div class="stats">
        <div class="stat"><b>${d.children}</b><span>Children</span></div>
        <div class="stat"><b>${d.assessments}</b><span>Assessments</span></div>
        <div class="stat warn"><b>${d.referred}</b><span>Referred for assessment</span></div>
        <div class="stat"><b>${(d.by_module.game || 0)}/${(d.by_module.handwriting || 0)}/${(d.by_module.eye || 0)}</b><span>Game / Writing / Eye</span></div>
      </div>
      <div class="grid2">
        <section class="card"><h2>Recent children</h2>${d.recent.length ? `<table class="tbl"><thead><tr><th>Name</th><th>Age</th><th>RDI</th><th></th></tr></thead><tbody>
          ${d.recent.map(c => `<tr><td>${esc(c.name)}</td><td>${c.age}</td><td>${c.rdi ? `<span class="badge ${c.rdi.refer ? 'high' : 'low'}">${pct(c.rdi.rdi, 0)}</span>` : '<span class="badge muted">–</span>'}</td><td><a href="#/child/${c.id}">Open</a></td></tr>`).join('')}</tbody></table>`
          : '<p class="muted">No children yet. Add a child to start a screening.</p>'}</section>
        <section class="card how"><h2>How a screening works</h2><ol class="steps">
          <li><b>Gamified test</b><span>10 short letter, sound and word exercises (about 2 minutes), or the full 32.</span></li>
          <li><b>Handwriting</b><span>The child writes dictated letters, or you upload a photo of their writing.</span></li>
          <li><b>Eye tracking</b><span>The webcam follows the eyes while the child reads three short texts.</span></li>
          <li><b>Report</b><span>All results combine into the Reading Difficulty Index (RDI).</span></li></ol></section>
      </div>`;
  }

  // ---------------------------------------------------------------- children
  async function children() {
    const kids = await API.get('/api/children');
    view().innerHTML = `<header class="page-head"><div><h1>Children</h1><p class="muted">${kids.length} profile${kids.length === 1 ? '' : 's'}</p></div><a class="btn" href="#/children/new">Add a child</a></header>
      <div class="kid-grid">${kids.map(c => `<a class="card kid" href="#/child/${c.id}"><div class="avatar">${esc(c.name[0] || '?')}</div><div><b>${esc(c.name)}</b><span class="muted">Age ${c.age}${c.school ? ' · ' + esc(c.school) : ''}</span></div>
        <div class="kid-mods">${['game', 'handwriting', 'eye'].map(m => `<span title="${MODNAME[m]}" class="${c.latest[m] ? 'on' : ''}">${MODICON[m]}</span>`).join('')}</div>
        ${c.rdi ? `<span class="badge ${c.rdi.refer ? 'high' : 'low'}">RDI ${pct(c.rdi.rdi, 0)}</span>` : ''}</a>`).join('') || '<p class="muted">No children yet.</p>'}</div>`;
  }
  function newChild() {
    view().innerHTML = `<header class="page-head"><h1>Add a child</h1></header>
      <form class="card form" id="kidForm">
        <label>Child's name<input name="name" required></label>
        <div class="row2"><label>Age<input name="age" type="number" min="5" max="17" value="9" required></label>
        <label>Gender <span class="muted small">(used by the game model only)</span><select name="gender"><option value="female">Female</option><option value="male">Male</option></select></label></div>
        <label>School (optional)<input name="school"></label>
        <label class="check"><input type="checkbox" name="native_speaker" checked> The test language is the child's first language</label>
        <label class="check"><input type="checkbox" name="other_language"> The child speaks another language</label>
        <p class="err" id="kidErr"></p><button class="btn">Save profile</button></form>`;
    $('#kidForm').onsubmit = async e => {
      e.preventDefault(); const f = e.target; const b = f.querySelector('button'); busy(b, true, 'Saving…');
      try { const c = await API.post('/api/children', { name: f.name.value, age: +f.age.value, gender: f.gender.value, school: f.school.value, native_speaker: f.native_speaker.checked, other_language: f.other_language.checked });
        toast('Profile saved'); location.hash = `#/child/${c.id}`; }
      catch (err) { $('#kidErr').textContent = err.message; busy(b, false); }
    };
  }
  async function child(id) {
    const r = await API.get(`/api/children/${id}/report`); const c = r.child;
    const mcard = m => { const x = r.modules[m];
      return `<div class="card mod"><div class="mod-top"><span class="mod-ic">${MODICON[m]}</span><h3>${MODNAME[m]}</h3>${riskBadge(x && x.risk, m)}</div>
        <p class="muted">${x ? `${esc(x.label)} · ${fmtDate(x.date)}` : 'Not done yet'}</p>
        <a class="btn ${x ? 'ghost' : ''}" href="#/child/${id}/${m}">${x ? 'Repeat' : 'Start'}</a></div>`; };
    view().innerHTML = `<header class="page-head"><div><a class="back" href="#/children">← Children</a><h1>${esc(c.name)}</h1>
      <p class="muted">Age ${c.age} · ${c.gender}${c.school ? ' · ' + esc(c.school) : ''}</p></div>
      <div class="actions"><a class="btn" href="#/child/${id}/report">View report</a><button class="btn ghost danger" id="delKid">Delete</button></div></header>
      <div class="grid-rdi"><section class="card rdi">${r.rdi ? `<h2>Reading Difficulty Index</h2>${gauge(r.rdi.rdi)}<p class="rdi-band ${r.rdi.refer ? 'bad' : 'ok'}">${r.rdi.band} · ${r.rdi.refer ? 'Refer for a full assessment' : 'No referral needed now'}</p><p class="muted small">Based on ${Object.keys(r.rdi.contributions).length} of 3 modules</p>`
        : '<h2>Reading Difficulty Index</h2><p class="muted">Complete at least one module to see the index.</p>'}</section>
        <div class="mods">${['game', 'handwriting', 'eye'].map(mcard).join('')}</div></div>
      <section class="card"><h2>History</h2>${r.history.length ? `<table class="tbl"><thead><tr><th>Date</th><th>Module</th><th>Result</th><th>Risk</th></tr></thead><tbody>${r.history.slice().reverse().map(h => `<tr><td>${fmtDate(h.date)}</td><td>${MODNAME[h.module]}</td><td>${esc(h.label)}</td><td>${riskBadge(h.risk, h.module)}</td></tr>`).join('')}</tbody></table>` : '<p class="muted">No assessments yet.</p>'}</section>`;
    $('#delKid').onclick = async () => { if (!confirm(`Delete ${c.name} and all results?`)) return; await API.del(`/api/children/${id}`); toast('Profile deleted'); location.hash = '#/children'; };
  }

  // ---------------------------------------------------------------- module 1: game
  function reasonsList(rs) {
    if (!rs || !rs.length) return '';
    const mx = Math.max(...rs.map(r => Math.abs(r.effect)));
    return `<ul class="reasons">${rs.map(r => `<li><span class="r-name">${esc(r.label || r.feature)}</span><span class="r-bar"><i class="${r.effect > 0 ? 'up' : 'down'}" style="width:${(45 * Math.abs(r.effect) / mx).toFixed(1)}%;${r.effect > 0 ? 'left:50%' : `right:50%`}"></i></span><span class="r-val ${r.effect > 0 ? 'up' : 'down'}">${r.effect > 0 ? 'raises' : 'lowers'} risk</span></li>`).join('')}</ul>`;
  }
  async function gameView(id) {
    const c = await API.get(`/api/children/${id}`);
    view().innerHTML = `<header class="page-head"><div><a class="back" href="#/child/${id}">← ${esc(c.name)}</a><h1>Gamified test</h1><p class="muted">Letter, sound, word and spelling exercises. The short test takes about 2 minutes.</p></div></header>
      <section class="card game-intro" id="gIntro"><h2>Before you start</h2><ul class="ticks"><li>Turn the sound on; many exercises speak a letter or word.</li><li>Let the child use the mouse or touch screen on their own.</li><li>Each exercise has a short timer; “Next exercise” moves on.</li></ul>
      <label class="inline">Test <select id="gForm"><option value="short" selected>Short: 10 exercises (about 2 minutes)</option><option value="full">Full: all 32 exercises (about 8 minutes)</option></select></label>
      <label class="inline">Seconds per timed exercise <select id="gSecs"><option value="8">8 (quick)</option><option value="12" selected>12 (standard)</option><option value="16">16 (younger children)</option></select></label>
      <button class="btn" id="gStart">Start the test</button></section>
      <section class="card game-card hidden" id="gCard"><div class="g-progress"><i id="gBar"></i></div><div id="gRoot"></div></section>
      <section id="gResult"></section>`;
    $('#gStart').onclick = () => {
      $('#gIntro').classList.add('hidden'); $('#gCard').classList.remove('hidden');
      const g = new ScreeningGame.Game($('#gRoot'), { seconds: +$('#gSecs').value, only: $('#gForm').value === 'short' ? ScreeningGame.QUICK : null,
        onProgress: (i, n) => $('#gBar').style.width = (100 * i / n) + '%',
        onDone: async (items, secs) => {
          $('#gBar').style.width = '100%'; $('#gRoot').innerHTML = '<div class="loading">Scoring the test…</div>';
          try { const r = await API.post('/api/game/predict', { child_id: +id, items, duration_s: secs, seconds: +$('#gSecs').value }); $('#gCard').classList.add('hidden'); gameResult($('#gResult'), r, id); }
          catch (err) { $('#gRoot').innerHTML = `<p class="err">${esc(err.message)}</p>`; }
        } });
      g.start();
    };
  }
  function gameResult(root, r, id, truth) {
    root.innerHTML = `<div class="grid-res"><section class="card center"><h2>Game risk</h2>${gauge(r.risk / 0.22 > 1 ? 1 : r.risk / 0.22)}
      <p class="big-num">${pct(r.risk)}</p><p class="rdi-band ${r.refer ? 'bad' : 'ok'}">${esc(r.label)}</p>
      <p class="muted small">Referral cut-off ${pct(r.cutoff, 0)} · ${esc(r.model)}</p>${truth != null ? `<p class="truth ${truth == (r.refer ? 1 : 0) ? 'ok' : 'bad'}">Actual diagnosis in dataset: <b>${truth ? 'Dyslexia' : 'No dyslexia'}</b></p>` : ''}</section>
      <section class="card"><h2>Why this result (SHAP)</h2><p class="muted small">The measures that moved this child's risk the most.</p>${reasonsList(r.reasons)}
      ${r.summary ? `<div class="mini-stats">${Object.entries(r.summary).map(([k, v]) => `<div><b>${v}</b><span>${esc(k)}</span></div>`).join('')}</div>` : ''}</section></div>
      ${id ? `<p class="center"><a class="btn" href="#/child/${id}">Back to profile</a> <a class="btn ghost" href="#/child/${id}/report">View report</a></p>` : ''}`;
  }
  async function datasetView() {
    view().innerHTML = `<header class="page-head"><div><h1>Dataset mode</h1><p class="muted">Run the trained models on real children from the research datasets that the models never saw during training, and compare with their actual diagnosis.</p></div></header>
      <div class="tabs"><button class="tab on" data-t="game">Gamified test (Dytective)</button><button class="tab" data-t="eye">Eye tracking (ETDD70)</button></div>
      <section class="card row-actions"><button class="btn" data-k="1">Child with dyslexia</button><button class="btn" data-k="0">Child without dyslexia</button><button class="btn ghost" data-k="">Random child</button></section><section id="dsRes"></section>`;
    let mode = 'game';
    view().querySelectorAll('.tab').forEach(t => t.onclick = () => { mode = t.dataset.t; view().querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === t)); $('#dsRes').innerHTML = ''; });
    view().querySelectorAll('[data-k]').forEach(b => b.onclick = async () => {
      busy(b, true, 'Loading…');
      const q = b.dataset.k !== '' ? `?dyslexia=${b.dataset.k}` : '';
      try {
        if (mode === 'game') {
          const r = await API.get('/api/game/sample' + q);
          gameResult($('#dsRes'), r, null, r.truth); $('#dsRes').insertAdjacentHTML('afterbegin', `<p class="muted">Dytective record #${r.record} · age ${r.age} · ${r.gender}</p>`);
        } else {
          const r = await API.get('/api/eye/sample' + q);
          const ok = (r.risk >= 0.5 ? 1 : 0) === r.y;
          $('#dsRes').innerHTML = `<p class="muted">ETDD70 child #${r.sid} · recorded with a 250 Hz eye tracker</p>
            <div class="grid-res"><section class="card center"><h2>Eye-movement risk</h2>${gauge(r.risk)}<p class="big-num">${pct(r.risk)}</p>
            <p class="rdi-band ${r.risk >= 0.5 ? 'bad' : 'ok'}">${esc(r.label)}</p><p class="truth ${ok ? 'ok' : 'bad'}">Actual diagnosis in dataset: <b>${r.y ? 'Dyslexia' : 'No dyslexia'}</b></p>
            <p class="muted small">${esc(r.model)}</p></section>
            <section class="card"><h2>Reading summary</h2><div class="mini-stats">${r.tasks.map(t => `<div><b>${t.reading_s} s</b><span>${t.name}</span></div>`).join('')}<div><b>${r.tasks.reduce((a, t) => a + t.fix.length, 0)}</b><span>fixations</span></div></div>
            <p class="muted small">Circles are fixations (bigger means longer); lines show the order the eyes moved.</p></section></div>
            ${r.tasks.map((t, i) => `<section class="card"><h2>${t.name}</h2><canvas class="gaze-canvas" id="ds_${i}"></canvas></section>`).join('')}`;
          r.tasks.forEach((t, i) => drawStim($(`#ds_${i}`), t));
        }
      } catch (err) { toast(err.message, true); } finally { busy(b, false); }
    });
  }
  function drawStim(canvas, t) {
    const img = new Image(); img.onload = () => {
      const W = canvas.clientWidth, s = W / t.w; canvas.width = W * devicePixelRatio; canvas.height = t.h * s * devicePixelRatio; canvas.style.height = (t.h * s) + 'px';
      const g = canvas.getContext('2d'); g.setTransform(s * devicePixelRatio, 0, 0, s * devicePixelRatio, 0, 0); g.drawImage(img, 0, 0, t.w, t.h);
      g.strokeStyle = 'rgba(31,122,107,.55)'; g.lineWidth = 1.6; g.beginPath(); t.fix.forEach((f, i) => i ? g.lineTo(f[0], f[1]) : g.moveTo(f[0], f[1])); g.stroke();
      t.fix.forEach(f => { g.fillStyle = 'rgba(210,80,74,.38)'; g.beginPath(); g.arc(f[0], f[1], 4 + Math.min(f[2], 900) / 45, 0, 7); g.fill(); });
    }; img.src = t.img;
  }

  // ---------------------------------------------------------------- module 2: handwriting
  async function hwView(id) {
    const c = await API.get(`/api/children/${id}`);
    view().innerHTML = `<header class="page-head"><div><a class="back" href="#/child/${id}">← ${esc(c.name)}</a><h1>Handwriting</h1><p class="muted">The CNN checks each letter for reversals (b/d, p/q and mirrored letters).</p></div></header>
      <div class="tabs"><button class="tab on" data-t="draw">Write letters</button><button class="tab" data-t="sheet">Photo of a page</button><button class="tab" data-t="files">Letter images</button></div>
      <section class="card" id="hwPane"></section><section id="hwRes"></section>`;
    const panes = {
      draw: () => { $('#hwPane').innerHTML = `<p>Press 🔊 in each box to hear the letter, then let the child write it in the box.</p><div class="hw-grid" id="pad"></div><button class="btn" id="hwGo">Analyse handwriting</button>`;
        const P = HW.pad($('#pad')); $('#hwGo').onclick = async e => { const blobs = await P.blobs(); if (!blobs.length) return toast('Write at least one letter first.', true); send(blobs, e.target); }; },
      sheet: () => { $('#hwPane').innerHTML = `<p>Upload a clear photo or scan of the child's handwriting (dark pen on light paper works best).</p><input type="file" accept="image/*" id="sheetIn"><img id="sheetPrev" class="sheet-prev hidden"><button class="btn" id="hwGo">Analyse page</button>`;
        $('#sheetIn').onchange = e => { const f = e.target.files[0]; if (f) { $('#sheetPrev').src = URL.createObjectURL(f); $('#sheetPrev').classList.remove('hidden'); } };
        $('#hwGo').onclick = async e => { const f = $('#sheetIn').files[0]; if (!f) return toast('Choose a photo first.', true);
          const fd = new FormData(); fd.append('child_id', id); fd.append('image', f); busy(e.target, true, 'Analysing…');
          try { const r = await API.form('/api/handwriting/sheet', fd); showHW(r, URL.createObjectURL(f)); } catch (err) { toast(err.message, true); } finally { busy(e.target, false); } }; },
      files: () => { $('#hwPane').innerHTML = `<p>Upload one or more images, each with a single letter.</p><input type="file" accept="image/*" multiple id="filesIn"><button class="btn" id="hwGo">Analyse letters</button>`;
        $('#hwGo').onclick = e => { const fs = [...$('#filesIn').files]; if (!fs.length) return toast('Choose images first.', true); send(fs, e.target); }; },
    };
    async function send(blobs, btn) {
      const fd = new FormData(); fd.append('child_id', id); blobs.forEach((b, i) => fd.append('images', b, `letter${i}.png`));
      busy(btn, true, 'Analysing…'); try { showHW(await API.form('/api/handwriting/predict', fd)); } catch (err) { toast(err.message, true); } finally { busy(btn, false); }
    }
    function showHW(r, sheetUrl) {
      $('#hwRes').innerHTML = `<div class="grid-res"><section class="card center"><h2>Handwriting score</h2>${gauge(r.risk || 0)}<p class="big-num">${pct(r.risk)}</p>
        <p class="rdi-band ${r.risk >= 0.5 ? 'bad' : 'ok'}">${esc(r.label)}</p><p class="muted small">${r.n_letters} letters · ${r.n_reversal} reversal · ${r.n_corrected} corrected</p></section>
        <section class="card"><h2>Each letter (Grad-CAM)</h2><p class="muted small">Bright areas show the strokes the network used.</p><div class="letters">${r.letters.map(l => `<figure class="lt ${l.pred.toLowerCase()}"><img src="${l.cam}"><figcaption><b>${l.pred}</b> ${pct(l.probs[l.pred], 0)}</figcaption></figure>`).join('')}</div></section></div>
        ${sheetUrl ? `<section class="card"><h2>Letters found on the page</h2><div class="sheet-wrap"><img src="${sheetUrl}">${r.letters.map(l => l.box ? `<span class="sbox ${l.pred.toLowerCase()}" style="left:${100 * l.box.x}%;top:${100 * l.box.y}%;width:${100 * l.box.w}%;height:${100 * l.box.h}%"></span>` : '').join('')}</div></section>` : ''}
        <p class="center"><a class="btn" href="#/child/${id}">Back to profile</a></p>`;
      $('#hwRes').scrollIntoView({ behavior: 'smooth' });
    }
    view().querySelectorAll('.tab').forEach(t => t.onclick = () => { view().querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === t)); panes[t.dataset.t](); });
    panes.draw();
  }

  // ---------------------------------------------------------------- module 3: eye tracking
  async function eyeView(id) {
    const c = await API.get(`/api/children/${id}`);
    view().innerHTML = `<header class="page-head"><div><a class="back" href="#/child/${id}">← ${esc(c.name)}</a><h1>Eye tracking</h1><p class="muted">The webcam follows the eyes while the child reads three short texts.</p></div></header>
      <section class="card" id="eyeSetup"><h2>Set up</h2><ul class="ticks"><li>Sit about an arm's length from the screen with a light in front of you.</li><li>Keep your head still while reading.</li><li>Use Chrome or Edge and allow the camera when asked.</li></ul>
        <label class="inline">Camera <select id="camSel"><option>Detecting cameras…</option></select></label><button class="btn" id="eyeStart">Start calibration</button></section>
      <div id="eyeLayer" class="eye-layer hidden"></div><section id="eyeRes"></section>`;
    const cams = await EyeTest.cameras();
    $('#camSel').innerHTML = cams.length ? cams.map((d, i) => `<option value="${d.deviceId}">${esc(d.label || 'Camera ' + (i + 1))}</option>`).join('') : '<option value="">No camera found</option>';
    const ext = cams.findIndex(d => !/integrated|built-in|hp truevision|hd camera|facetime/i.test(d.label)); if (ext > 0) $('#camSel').selectedIndex = ext;
    $('#eyeStart').onclick = async e => {
      const camId = $('#camSel').value, camLabel = $('#camSel').selectedOptions[0]?.textContent;
      busy(e.target, true, 'Starting camera…');
      try { await EyeTest.startGazer(camId); } catch (err) { busy(e.target, false); return toast('Could not start the camera: ' + err.message, true); }
      $('#eyeSetup').classList.add('hidden'); const L = $('#eyeLayer'); L.classList.remove('hidden'); document.body.classList.add('eye-mode');
      const err = await EyeTest.calibrate(L);
      const tasks = {}, snaps = {};
      for (const k of EyeTest.ORDER) { const t = await EyeTest.readTask(L, k); tasks[k] = { samples: t.samples, boxes: t.boxes }; snaps[k] = t; }
      EyeTest.stopGazer(); L.classList.add('hidden'); document.body.classList.remove('eye-mode');
      $('#eyeRes').innerHTML = '<div class="card loading">Analysing eye movements…</div>';
      try {
        const r = await API.post('/api/eye/analyze', { child_id: +id, tasks, camera: camLabel, calibration_error_px: err });
        const LBL = { aoi_dwell_mean: 'looking time per word', time_per_word: 'reading speed (time per word)', aoi_nfix_mean: 'fixations per word', aoi_skip_rate: 'words skipped', aoi_first_fix_dur_mean: 'first look per word', aoi_revisits_mean: 'returns to a word', aoi_reread_mean: 're-reading time', mean_fix_dur: 'mean fixation', fix_dur_median: 'median fixation', ratio_progress_regress: 'forward/backward ratio', regress_per_fix: 'backward jumps' };
        const TN = { Syl: 'Syllables', Mean: 'Story', Pseudo: 'Made-up words' };
        r.reasons.forEach(x => { const [t, ...rest] = x.feature.split('_'); x.label = `${TN[t]}: ${LBL[rest.join('_')] || rest.join(' ')}`; });
        $('#eyeRes').innerHTML = `<div class="grid-res"><section class="card center"><h2>Eye-movement risk</h2>${gauge(r.risk)}<p class="big-num">${pct(r.risk)}</p><p class="rdi-band ${r.risk >= 0.5 ? 'bad' : 'ok'}">${esc(r.label)}</p>
          <p class="muted small">${err ? `Calibration error about ${Math.round(err)} px · ` : ''}${esc(camLabel || '')}</p></section>
          <section class="card"><h2>Why this result</h2>${reasonsList(r.reasons)}</section></div>
          ${EyeTest.ORDER.map(k => { const s = r.tasks[k].summary; return `<section class="card"><h2>${EyeTest.TEXTS[k].title.replace('Read', '').replace('aloud', '').trim().replace(/^the /, '').replace(/^./, m => m.toUpperCase())}</h2>
            <div class="mini-stats"><div><b>${(s.reading_time_ms / 1000).toFixed(1)} s</b><span>reading time</span></div><div><b>${s.fixations}</b><span>fixations</span></div><div><b>${s.regressions}</b><span>regressions</span></div><div><b>${s.words_fixated}/${s.words}</b><span>words looked at</span></div></div>
            <canvas class="gaze-canvas" id="gc_${k}"></canvas></section>`; }).join('')}
          <p class="center"><a class="btn" href="#/child/${id}">Back to profile</a></p>`;
        EyeTest.ORDER.forEach(k => EyeTest.drawResult($(`#gc_${k}`), snaps[k], r.tasks[k].fixations));
      } catch (er) { $('#eyeRes').innerHTML = `<p class="err">${esc(er.message)}</p>`; }
    };
  }

  // ---------------------------------------------------------------- report
  async function reportView(id) {
    const r = await API.get(`/api/children/${id}/report`); const c = r.child, R = r.rdi;
    view().innerHTML = `<header class="page-head noprint"><div><a class="back" href="#/child/${id}">← ${esc(c.name)}</a><h1>Screening report</h1></div><button class="btn" onclick="window.print()">Download PDF</button></header>
      <article class="report card">
        <div class="rep-head"><div class="brand"><span class="logo">${BOOK}</span>DyslexiaScreen</div><div class="muted small">Generated ${fmtDate(r.generated_at)} by ${esc(r.screener)}</div></div>
        <h2>${esc(c.name)} <span class="muted">· age ${c.age} · ${c.gender}</span></h2>
        ${R ? `<div class="rep-rdi">${gauge(R.rdi)}<div><p class="big-num">RDI ${pct(R.rdi, 0)}</p><p class="rdi-band ${R.refer ? 'bad' : 'ok'}">${R.band}: ${R.refer ? 'refer for a full assessment by a psychologist' : 'no referral needed now; re-screen next term'}</p>
          <table class="tbl"><thead><tr><th>Module</th><th>Risk</th><th>Cut-off</th><th>Share of RDI (log-odds)</th></tr></thead><tbody>${Object.entries(R.contributions).map(([k, v]) => `<tr><td>${v.name}</td><td>${pct(v.risk)}</td><td>${pct(R.cutoffs[k], 0)}</td><td class="${v.log_odds > 0 ? 'up' : 'down'}">${v.log_odds > 0 ? '+' : ''}${v.log_odds.toFixed(2)}</td></tr>`).join('')}</tbody></table></div></div>` : '<p>No modules completed yet.</p>'}
        ${['game', 'handwriting', 'eye'].map(m => { const x = r.modules[m]; if (!x) return `<section class="rep-mod"><h3>${MODICON[m]} ${MODNAME[m]}</h3><p class="muted">Not done.</p></section>`;
          const res = x.result || {}; return `<section class="rep-mod"><h3>${MODICON[m]} ${MODNAME[m]} <span class="muted small">${fmtDate(x.date)}</span></h3><p><b>${esc(x.label)}</b> · risk ${pct(x.risk)}</p>
          ${m === 'handwriting' && res.letters ? `<div class="letters small">${res.letters.slice(0, 16).map(l => `<figure class="lt ${l.pred.toLowerCase()}"><img src="${l.cam}"><figcaption>${l.pred}</figcaption></figure>`).join('')}</div>` : ''}
          ${res.reasons ? reasonsList(res.reasons.slice(0, 5)) : ''}</section>`; }).join('')}
        <p class="muted small rep-foot">This is a screening tool. A diagnosis of dyslexia is made by a qualified professional.</p>
      </article>`;
  }

  // ---------------------------------------------------------------- model lab
  let charts = [];
  async function lab() {
    const L = await API.get('/api/lab'); charts.forEach(c => c.destroy()); charts = [];
    const tabs = [['game', 'Gamified test'], ['handwriting', 'Handwriting'], ['eye', 'Eye tracking']].filter(([k]) => L[k]);
    view().innerHTML = `<header class="page-head"><div><h1>Model Lab</h1><p class="muted">Every algorithm trained and tested on the same data split. The proposed model is highlighted.</p></div></header>
      <div class="tabs">${tabs.map(([k, n], i) => `<button class="tab ${i ? '' : 'on'}" data-k="${k}">${n}</button>`).join('')}</div><div id="labPane"></div>`;
    const show = k => {
      charts.forEach(c => c.destroy()); charts = [];
      const d = L[k], ms = Object.entries(d.models).sort((a, b) => (b[1].roc_auc || 0) - (a[1].roc_auc || 0));
      const prop = ms.find(([n]) => /proposed/i.test(n)) || ms[0];
      const others = ms.filter(m => m !== prop);
      const hc = d.heldout && d.heldout.cutoffs['0.11'];
      const bestOther = Math.max(...others.map(m => m[1].roc_auc || 0)), meanOther = others.reduce((s, m) => s + (m[1].accuracy || 0), 0) / others.length;
      $('#labPane').innerHTML = `<p class="muted">${esc(d.dataset)}${d.cv ? ' · ' + esc(d.cv) : ''}</p>
        <div class="stats"><div class="stat hl"><b>${pct(prop[1].accuracy)}</b><span>Accuracy (proposed)</span></div><div class="stat hl"><b>${(prop[1].roc_auc).toFixed(3)}</b><span>ROC-AUC (proposed)</span></div>
          ${hc ? `<div class="stat"><b>${pct(hc.sensitivity)}</b><span>Children with dyslexia caught at the screening cut-off (${d.heldout.n} held-out children)</span></div>` : `<div class="stat"><b>${(prop[1].f1 ?? prop[1].macro_f1).toFixed(3)}</b><span>F1 score</span></div>`}<div class="stat"><b>+${(100 * (prop[1].accuracy - meanOther)).toFixed(1)} pts</b><span>Accuracy over the average of ${others.length} other algorithms</span></div></div>
        ${d.short_form ? `<section class="card"><h2>Short form used in the app (10 exercises, about 2 minutes)</h2><p class="muted">The same ensemble trained on 10 of the 32 exercises, chosen for how well each one separates the two groups. Same 5-fold cross-validation.</p>
          <div class="kv"><div><b>${pct(d.short_form.cv.accuracy)}</b><span>Accuracy</span></div><div><b>${d.short_form.cv.roc_auc.toFixed(3)}</b><span>ROC-AUC</span></div><div><b>${pct(d.short_form.heldout.sensitivity)}</b><span>Dyslexia caught at cut-off (held-out)</span></div><div><b>${pct(d.short_form.heldout.specificity)}</b><span>Typical readers cleared</span></div></div></section>` : ''}
        ${d.webcam_model && d.webcam_model.note ? `<section class="card"><h2>Live webcam model</h2><p class="muted">The research data was recorded with a 250 Hz eye tracker. For the live app we degraded every recording to webcam quality (30 Hz, calibration offset, drift and jitter), ran it through the same fixation code as the website, and trained on that. Children are the unit of cross-validation.</p>
          <div class="kv"><div><b>${pct(d.webcam_model.accuracy)}</b><span>Accuracy</span></div><div><b>${d.webcam_model.roc_auc.toFixed(3)}</b><span>ROC-AUC</span></div><div><b>${d.webcam_model.n_features}</b><span>Reading measures</span></div></div></section>` : ''}
        <section class="card"><h2>All algorithms</h2><div class="tbl-wrap"><table class="tbl lab"><thead><tr><th>Algorithm</th><th>Accuracy</th><th>ROC-AUC</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead><tbody>
          ${ms.map(([n, m]) => `<tr class="${m === prop[1] ? 'prop' : ''}"><td>${esc(n)}</td><td>${pct(m.accuracy)}</td><td>${m.roc_auc.toFixed(3)}</td><td>${(m.precision).toFixed(3)}</td><td>${(m.recall).toFixed(3)}</td><td>${(m.f1 ?? m.macro_f1).toFixed(3)}</td></tr>`).join('')}</tbody></table></div></section>
        <div class="grid2"><section class="card"><h2>Accuracy and ROC-AUC</h2><div class="chart-box tall"><canvas id="chBar"></canvas></div></section>
          <section class="card"><h2>${prop[1].roc ? 'ROC curves' : 'Confusion matrix (proposed)'}</h2><div class="chart-box tall">${prop[1].roc ? '<canvas id="chRoc"></canvas>' : confusion(prop[1].confusion, d.classes)}</div></section></div>
        ${hc ? `<section class="card"><h2>Screening on ${d.heldout.n} held-out children (cut-off 0.11, as used in the app)</h2><p class="muted">Sensitivity ${pct(hc.sensitivity)} · specificity ${pct(hc.specificity)} · ROC-AUC ${d.heldout.roc_auc.toFixed(3)}. These children were never used for training.</p>${confusion(hc.confusion, ['No dyslexia', 'Dyslexia'])}</section>` : ''}
        ${prop[1].roc ? `<section class="card"><h2>Confusion matrix (proposed, threshold ${prop[1].threshold})</h2>${confusion(prop[1].confusion, ['No dyslexia', 'Dyslexia'])}</section>` : ''}`;
      const css = getComputedStyle(document.documentElement), C1 = css.getPropertyValue('--accent').trim() || '#3b5bdb', C2 = css.getPropertyValue('--accent2').trim() || '#f08c00', MUTE = css.getPropertyValue('--mute').trim() || '#999';
      Chart.defaults.font.family = getComputedStyle(document.body).fontFamily; Chart.defaults.color = 'rgba(255,255,255,.8)'; Chart.defaults.borderColor = 'rgba(255,255,255,.12)';
      charts.push(new Chart($('#chBar'), { type: 'bar', data: { labels: ms.map(m => m[0].replace(' (proposed)', ' ★')), datasets: [
        { label: 'Accuracy', data: ms.map(m => +(100 * m[1].accuracy).toFixed(1)), backgroundColor: ms.map(m => m === prop ? C1 : C1 + '66') },
        { label: 'ROC-AUC × 100', data: ms.map(m => +(100 * m[1].roc_auc).toFixed(1)), backgroundColor: ms.map(m => m === prop ? C2 : C2 + '66') }] },
        options: { indexAxis: 'y', maintainAspectRatio: false, scales: { x: { min: 40, max: 100 } }, plugins: { legend: { position: 'bottom' } } } }));
      if (prop[1].roc) charts.push(new Chart($('#chRoc'), { type: 'scatter', data: { datasets: ms.slice(0, 7).map(([n, m]) => ({ label: n.replace(' (proposed)', ' ★'), showLine: true, pointRadius: 0,
        borderWidth: m === prop[1] ? 3 : 1.2, borderColor: m === prop[1] ? '#FFD58A' : (n.length % 2 ? 'rgba(255,255,255,.55)' : 'rgba(200,182,255,.45)'), data: m.roc.fpr.map((x, i) => ({ x, y: m.roc.tpr[i] })) })) },
        options: { maintainAspectRatio: false, scales: { x: { min: 0, max: 1, title: { display: true, text: 'False positive rate' } }, y: { min: 0, max: 1, title: { display: true, text: 'True positive rate' } } }, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } } }));
    };
    view().querySelectorAll('.tab').forEach(t => t.onclick = () => { view().querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === t)); show(t.dataset.k); });
    if (tabs.length) show(tabs[0][0]);
  }
  function confusion(M, labels) {
    labels = labels || M.map((_, i) => 'Class ' + i); const rs = M.map(r => r.reduce((a, b) => a + b, 0));
    return `<table class="cm"><thead><tr><th>True \\ Predicted</th>${labels.map(l => `<th>${esc(l)}</th>`).join('')}</tr></thead><tbody>${M.map((r, i) => `<tr><th>${esc(labels[i])}</th>${r.map((v, j) => `<td style="--a:${(v / rs[i]).toFixed(3)}" class="${v / rs[i] > 0.45 ? 'dark' : ''}"><b>${v.toLocaleString()}</b><span>${pct(v / rs[i])}</span></td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }

  // ---------------------------------------------------------------- about
  function about() {
    view().innerHTML = `<header class="page-head"><h1>About the project</h1></header>
      <section class="card prose"><h2>DyslexiaScreen</h2><p>A web platform that screens children for dyslexia risk with three independent machine learning modules and combines them into one Reading Difficulty Index (RDI).</p>
      <h3>Modules</h3><ul><li><b>Gamified test:</b> 32 exercises; XGBoost and Extra Trees ensemble with Platt calibration and TreeSHAP explanations (Dytective dataset).</li>
      <li><b>Handwriting:</b> convolutional neural network that labels letters normal, reversal or corrected, with Grad-CAM maps.</li>
      <li><b>Eye tracking:</b> webcam gaze (WebGazer) with fixation and regression analysis and a logistic model trained on ETDD70.</li>
      <li><b>Fusion:</b> each module's calibrated risk is centred at its referral cut-off and averaged in log-odds to give the RDI.</li></ul>
      <h3>Team</h3><p>K R Srigowri (1DT23IS064) and Rajshree Gupta (1DT23IS117), Department of Information Science and Engineering, Dayananda Sagar Academy of Technology and Management, Bengaluru. Guide: Dr. Vanajaroselin Chirchi.</p>
      <h3>Technology</h3><p>Python, FastAPI, SQLAlchemy and PostgreSQL; scikit-learn, XGBoost, LightGBM, TensorFlow and ONNX Runtime; JavaScript, WebGazer and Chart.js.</p></section>`;
  }

  // ---------------------------------------------------------------- router
  const routes = [
    [/^#\/login$/, () => authView('login'), true], [/^#\/register$/, () => authView('register'), true],
    [/^#\/?$/, dashboard], [/^#\/children$/, children], [/^#\/children\/new$/, newChild],
    [/^#\/child\/(\d+)$/, m => child(m[1])], [/^#\/child\/(\d+)\/game$/, m => gameView(m[1])],
    [/^#\/child\/(\d+)\/handwriting$/, m => hwView(m[1])], [/^#\/child\/(\d+)\/eye$/, m => eyeView(m[1])],
    [/^#\/child\/(\d+)\/report$/, m => reportView(m[1])], [/^#\/dataset$/, datasetView], [/^#\/lab$/, lab], [/^#\/about$/, about],
  ];
  async function route() {
    const h = location.hash || '#/';
    if (window.webgazer && !h.includes('/eye')) { try { EyeTest.stopGazer(); } catch (e) {} document.body.classList.remove('eye-mode'); }
    const r = routes.find(([re]) => re.test(h)) || routes[2];
    const isPublic = r[2];
    if (!isPublic && !API.getToken()) { location.hash = '#/login'; return; }
    if (!isPublic && !USER) { try { USER = await API.get('/api/auth/me'); } catch (e) { return; } }
    document.body.classList.toggle('bare', !!isPublic); document.body.classList.remove('article-open'); document.onkeydown = null;
    if (USER) { $('#who').textContent = USER.name; }
    document.querySelectorAll('.nav a').forEach(a => a.classList.toggle('on', h === a.getAttribute('href') || (a.getAttribute('href') !== '#/' && h.startsWith(a.getAttribute('href')))));
    view().innerHTML = '<div class="loading">Loading…</div>';
    try { await r[1](h.match(r[0])); } catch (e) { view().innerHTML = `<section class="card"><p class="err">${esc(e.message)}</p></section>`; }
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  document.addEventListener('DOMContentLoaded', () => {
    $('#logout').onclick = () => { API.setToken(null); USER = null; location.hash = '#/login'; };
    const mb = $('#menuBtn'); if (mb) mb.onclick = () => document.body.classList.toggle('nav-open');
    route();
  });
})();
