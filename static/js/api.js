/* Small API client: keeps the login token and sends JSON or form data. */
(function () {
  const KEY = 'ds_token';
  const getToken = () => { try { return localStorage.getItem(KEY); } catch (e) { return window.__tok || null; } };
  const setToken = t => { try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch (e) { window.__tok = t; } };
  async function call(method, path, body, isForm) {
    const h = {}; const t = getToken(); if (t) h['Authorization'] = 'Bearer ' + t;
    if (body && !isForm) h['Content-Type'] = 'application/json';
    const r = await fetch(path, { method, headers: h, body: body ? (isForm ? body : JSON.stringify(body)) : undefined });
    let data = null; try { data = await r.json(); } catch (e) {}
    if (r.status === 401 && !path.includes('/auth/')) { setToken(null); location.hash = '#/login'; }
    if (!r.ok) {
      let msg = data && data.detail;
      if (Array.isArray(msg)) msg = msg.map(d => (d.loc ? d.loc[d.loc.length - 1] + ': ' : '') + d.msg).join('; ');
      throw new Error(msg || `Request failed (${r.status})`);
    }
    return data;
  }
  window.API = {
    getToken, setToken,
    get: p => call('GET', p), post: (p, b) => call('POST', p, b), del: p => call('DELETE', p),
    form: (p, fd) => call('POST', p, fd, true),
  };
})();
