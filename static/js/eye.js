/* Module 3: webcam eye tracking with WebGazer. Calibration, three reading tasks
   (syllables, a passage, made-up words), gaze capture and result drawing. */
(function () {
  const TEXTS = {
    syllables: { title: 'Read the syllables aloud, line by line', lines: ['ba po ki lu me da', 'ro fi tu se no ga', 'pi le mo ru di ka', 'so ne bu ta li fo'] },
    passage: { title: 'Read the story aloud', lines: ['Tom has a small brown dog called Max.', 'Every morning they walk to the park', 'near the river. Max likes to chase', 'the ducks, but he never catches one.'] },
    pseudo: { title: 'Read the made-up words aloud', lines: ['blim fotter crask wunt prell', 'snob dorn tamish fole grint', 'moffle splunk vosh trapen gliss'] },
  };
  const ORDER = ['syllables', 'passage', 'pseudo'];
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  async function cameras() {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: true }); s.getTracks().forEach(t => t.stop());
      return (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput');
    } catch (e) { return []; }
  }

  async function startGazer(deviceId) {
    const wg = window.webgazer;
    wg.params.faceMeshSolutionPath = '/vendor/webgazer/mediapipe/face_mesh';
    wg.params.showVideoPreview = true;
    wg.params.videoViewerWidth = 240; wg.params.videoViewerHeight = 180;   // small preview, placed between the dots by CSS
    if (deviceId) wg.setCameraConstraints({ video: { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } } });
    wg.saveDataAcrossSessions(false);
    await wg.setRegression('ridge').begin();
    wg.showVideoPreview(true).showPredictionPoints(true).applyKalmanFilter(true);
    return wg;
  }

  function stopGazer() {
    try { window.webgazer.end(); } catch (e) {}
    document.querySelectorAll('#webgazerVideoContainer, #webgazerGazeDot').forEach(n => n.remove());
  }

  /* 9-point calibration: each dot needs 5 clicks while looking at it. Then a
     3-second accuracy check on the centre dot. Resolves with error in pixels. */
  function calibrate(layer) {
    return new Promise(resolve => {
      layer.innerHTML = ''; layer.classList.add('calib');
      const pts = [[10, 10], [50, 10], [90, 10], [10, 50], [50, 50], [90, 50], [10, 90], [50, 90], [90, 90]];
      let left = pts.length;
      const tip = document.createElement('div'); tip.className = 'calib-tip';
      const msg = document.createElement('p'); msg.textContent = 'Look at each dot and click it 5 times. Keep your head still.';
      const prog = document.createElement('p'); prog.className = 'calib-prog'; prog.textContent = `0 of ${pts.length} dots done`;
      const skip = document.createElement('button'); skip.className = 'btn ghost small calib-skip'; skip.textContent = 'Continue'; skip.hidden = true;
      skip.onclick = () => { if (left) { left = 0; check(); } };
      tip.append(msg, prog, skip); layer.append(tip);
      pts.forEach(([x, y]) => {
        const d = document.createElement('button'); d.className = 'calib-dot'; d.style.left = x + '%'; d.style.top = y + '%';
        let n = 0; d.onclick = () => {
          n++; d.style.setProperty('--fill', n / 5);
          if (n >= 5) {
            d.disabled = true; d.classList.add('done'); left--;
            prog.textContent = `${pts.length - left} of ${pts.length} dots done`;
            if (pts.length - left >= 7) skip.hidden = false;   // safety: allow moving on if a dot cannot be reached
            if (!left) check();
          }
        };
        layer.append(d);
      });
      async function check() {
        layer.querySelectorAll('.calib-dot').forEach(d => d.remove());
        msg.textContent = 'Now stare at the centre dot for 3 seconds.'; prog.remove(); skip.remove();
        const c = document.createElement('div'); c.className = 'calib-dot target'; c.style.left = '50%'; c.style.top = '50%'; layer.append(c);
        await sleep(600);
        const r = c.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2, errs = [];
        const t0 = performance.now();
        while (performance.now() - t0 < 3000) {
          const p = await Promise.race([window.webgazer.getCurrentPrediction(), sleep(500).then(() => null)]);   // never wait on a lost face
          if (p) errs.push(Math.hypot(p.x - cx, p.y - cy));
          await sleep(60);
        }
        errs.sort((a, b) => a - b);
        const med = errs.length ? errs[Math.floor(errs.length / 2)] : null;
        layer.classList.remove('calib'); layer.innerHTML = '';
        resolve(med);
      }
    });
  }

  /* Shows one text, records gaze until the child presses Done (or Space). */
  function readTask(layer, key) {
    return new Promise(resolve => {
      const T = TEXTS[key]; layer.innerHTML = '';
      const wrap = document.createElement('div'); wrap.className = 'read-wrap';
      const h = document.createElement('div'); h.className = 'read-title'; h.textContent = T.title;
      const text = document.createElement('div'); text.className = 'read-text';
      T.lines.forEach((ln, li) => {
        const row = document.createElement('div'); row.className = 'read-line';
        ln.split(' ').forEach(w => { const s = document.createElement('span'); s.className = 'w'; s.textContent = w; s.dataset.line = li; row.append(s, document.createTextNode(' ')); });
        text.append(row);
      });
      const done = document.createElement('button'); done.className = 'btn'; done.textContent = 'Done reading';
      wrap.append(h, text, done); layer.append(wrap);
      const samples = []; const t0 = performance.now();
      window.webgazer.showPredictionPoints(false);
      try { window.webgazer.showVideoPreview(false); } catch (e) {}   // nothing on screen but the text while reading
      window.webgazer.setGazeListener((d) => { if (d) samples.push([Math.round(performance.now() - t0), Math.round(d.x), Math.round(d.y)]); });
      const finish = () => {
        window.removeEventListener('keydown', onKey);
        window.webgazer.clearGazeListener();
        const boxes = [...text.querySelectorAll('.w')].map(s => { const r = s.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height, line: +s.dataset.line, word: s.textContent }; });
        const snap = { lines: T.lines, title: T.title, viewport: [innerWidth, innerHeight] };
        resolve({ samples, boxes, snap, duration_ms: Math.round(performance.now() - t0) });
      };
      const onKey = e => { if (e.code === 'Space') { e.preventDefault(); finish(); } };
      window.addEventListener('keydown', onKey); done.onclick = finish;
    });
  }

  /* Heat map + numbered scan path drawn over the saved word boxes. */
  function drawResult(canvas, task, fixations) {
    const W = task.snap.viewport[0], H = task.snap.viewport[1];
    const xs = task.boxes.map(b => b.x), ys = task.boxes.map(b => b.y);
    const minx = Math.min(...xs) - 60, miny = Math.min(...ys) - 60;
    const maxx = Math.max(...task.boxes.map(b => b.x + b.w)) + 60, maxy = Math.max(...task.boxes.map(b => b.y + b.h)) + 60;
    const sw = maxx - minx, sh = maxy - miny, scale = canvas.clientWidth / sw;
    canvas.width = Math.round(sw * scale * devicePixelRatio); canvas.height = Math.round(sh * scale * devicePixelRatio);
    canvas.style.height = (sh * scale) + 'px';
    const g = canvas.getContext('2d'); g.setTransform(scale * devicePixelRatio, 0, 0, scale * devicePixelRatio, -minx * scale * devicePixelRatio, -miny * scale * devicePixelRatio);
    const css = getComputedStyle(document.documentElement);
    g.fillStyle = css.getPropertyValue('--surface') || '#fff'; g.fillRect(minx, miny, sw, sh);
    // heat
    const heat = document.createElement('canvas'); heat.width = sw; heat.height = sh; const hg = heat.getContext('2d');
    fixations.forEach(f => { const r = 22 + Math.min(f.dur, 600) / 12; const grd = hg.createRadialGradient(f.x - minx, f.y - miny, 0, f.x - minx, f.y - miny, r);
      grd.addColorStop(0, `rgba(0,0,0,${Math.min(0.08 + f.dur / 1500, 0.5)})`); grd.addColorStop(1, 'rgba(0,0,0,0)'); hg.fillStyle = grd; hg.fillRect(0, 0, sw, sh); });
    const img = hg.getImageData(0, 0, sw, sh), d = img.data;
    for (let i = 0; i < d.length; i += 4) { const a = d[i + 3] / 255; if (!a) continue; const t = Math.min(a * 2.2, 1);
      d[i] = 255; d[i + 1] = Math.round(200 * (1 - t) + 60 * t); d[i + 2] = Math.round(80 * (1 - t)); d[i + 3] = Math.round(170 * t); }
    hg.putImageData(img, 0, 0); g.drawImage(heat, minx, miny);
    // words
    g.font = getComputedStyle(document.body).fontFamily ? `600 30px ${getComputedStyle(document.body).fontFamily}` : '600 30px sans-serif';
    g.fillStyle = css.getPropertyValue('--ink') || '#222'; g.textBaseline = 'top';
    task.boxes.forEach(b => g.fillText(b.word, b.x, b.y + 4));
    // path
    g.strokeStyle = 'rgba(40,90,200,0.75)'; g.lineWidth = 2; g.beginPath();
    fixations.forEach((f, i) => i ? g.lineTo(f.x, f.y) : g.moveTo(f.x, f.y)); g.stroke();
    fixations.forEach((f, i) => { g.fillStyle = 'rgba(40,90,200,0.9)'; g.beginPath(); g.arc(f.x, f.y, 5 + Math.min(f.dur, 600) / 80, 0, 7); g.fill();
      if (fixations.length < 70) { g.fillStyle = '#fff'; g.font = '700 10px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(i + 1, f.x, f.y); g.textAlign = 'left'; g.textBaseline = 'top'; } });
  }

  window.EyeTest = { TEXTS, ORDER, cameras, startGazer, stopGazer, calibrate, readTask, drawResult };
})();
