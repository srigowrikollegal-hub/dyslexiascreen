/* Module 2 helpers: a dictation drawing pad (one box per letter) that exports
   each box as a PNG blob for the CNN. */
(function () {
  const DICTATE = ['b', 'd', 'p', 'q'];   // the letters most often reversed
  function pad(root, letters = DICTATE) {
    root.innerHTML = ''; const boxes = [];
    letters.forEach((L, i) => {
      const cell = document.createElement('div'); cell.className = 'hw-cell';
      const lab = document.createElement('div'); lab.className = 'hw-label'; lab.innerHTML = `<span>${i + 1}</span>`;
      const say = document.createElement('button'); say.className = 'btn ghost tiny'; say.textContent = '🔊';
      say.title = 'Hear the letter'; say.onclick = () => window.ScreeningGame.SAY(`letter ${L}`, 0.75);
      lab.append(say);
      const c = document.createElement('canvas'); c.width = 220; c.height = 220; c.className = 'hw-canvas';
      const g = c.getContext('2d');   // transparent: the writing lines are a CSS background, not part of the image
      g.lineCap = 'round'; g.lineJoin = 'round'; g.strokeStyle = '#111'; g.lineWidth = 11;
      let drawing = false, last = null, inked = false;
      const pos = e => { const r = c.getBoundingClientRect(); const t = e.touches ? e.touches[0] : e; return [(t.clientX - r.left) * 220 / r.width, (t.clientY - r.top) * 220 / r.height]; };
      const down = e => { e.preventDefault(); drawing = true; last = pos(e); };
      const move = e => { if (!drawing) return; e.preventDefault(); const p = pos(e); g.beginPath(); g.moveTo(...last); g.lineTo(...p); g.stroke(); last = p; inked = true; };
      const up = () => { drawing = false; };
      c.addEventListener('mousedown', down); c.addEventListener('mousemove', move); window.addEventListener('mouseup', up);
      c.addEventListener('touchstart', down, { passive: false }); c.addEventListener('touchmove', move, { passive: false }); c.addEventListener('touchend', up);
      const clr = document.createElement('button'); clr.className = 'btn ghost tiny'; clr.textContent = 'Clear';
      clr.onclick = () => { g.clearRect(0, 0, 220, 220); inked = false; };
      lab.append(clr);
      cell.append(lab, c); root.append(cell);
      boxes.push({ letter: L, canvas: c, isInked: () => inked });
    });
    return {
      boxes,
      letters: () => boxes.filter(b => b.isInked()).map(b => b.letter),
      blobs: () => Promise.all(boxes.filter(b => b.isInked()).map(b => new Promise(r => {
        const o = document.createElement('canvas'); o.width = o.height = 220; const og = o.getContext('2d');
        og.fillStyle = '#fff'; og.fillRect(0, 0, 220, 220); og.drawImage(b.canvas, 0, 0); o.toBlob(r, 'image/png');   // ink on white, no lines
      }))),
    };
  }
  window.HW = { pad, DICTATE };
})();
