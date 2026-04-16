/* MARAMARA — Client helpers + SPA-style nav so the floating recorder stays alive. */

(function () {
  'use strict';

  // ----- SPA navigation -----
  // Intercept clicks on same-origin links. Fetch the target HTML, swap the
  // <main> element and <title>, push history. This keeps the floating
  // recorder pod's JS state alive across "page" changes.
  function initSpaNav() {
    document.addEventListener('click', async (e) => {
      const a = e.target.closest('a');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
      if (a.target === '_blank' || a.hasAttribute('download')) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      if (a.dataset.noSpa === '1') return;
      let url;
      try { url = new URL(href, location.href); } catch { return; }
      if (url.origin !== location.origin) return;
      // Skip API routes + static assets + downloads
      if (url.pathname.startsWith('/static') ||
          url.pathname.startsWith('/api') ||
          url.pathname.includes('/api/')) return;

      e.preventDefault();
      await navigateTo(url.pathname + url.search, true);
    });

    window.addEventListener('popstate', () => {
      navigateTo(location.pathname + location.search, false);
    });
  }

  async function navigateTo(path, pushHistory) {
    try {
      showSpaProgress();
      const res = await fetch(path, {
        headers: { 'X-Requested-With': 'maramara-spa' },
        credentials: 'include',
      });
      if (!res.ok) { location.href = path; return; }
      const html = await res.text();

      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');

      const newMain = doc.querySelector('main.app-main');
      const newTitle = doc.querySelector('title')?.textContent;
      const curMain = document.querySelector('main.app-main');
      if (!newMain || !curMain) { location.href = path; return; }

      if (newTitle) document.title = newTitle;
      curMain.innerHTML = newMain.innerHTML;

      // Also swap nav active state (simple approach: replace whole nav)
      const newNav = doc.querySelector('nav.nav');
      const curNav = document.querySelector('nav.nav');
      if (newNav && curNav) curNav.innerHTML = newNav.innerHTML;

      if (pushHistory) history.pushState({}, '', path);
      window.scrollTo({ top: 0, behavior: 'instant' });

      // Run any inline <script> tags inside the new main (they won't execute
      // after innerHTML swap otherwise).
      curMain.querySelectorAll('script').forEach(old => {
        const s = document.createElement('script');
        for (const attr of old.attributes) s.setAttribute(attr.name, attr.value);
        s.textContent = old.textContent;
        old.replaceWith(s);
      });

      window.dispatchEvent(new CustomEvent('maramara:navigated', { detail: { path } }));
    } catch (err) {
      console.error('SPA nav failed:', err);
      location.href = path;
    } finally {
      hideSpaProgress();
    }
  }

  function showSpaProgress() {
    let b = document.getElementById('spa-progress');
    if (!b) {
      b = document.createElement('div');
      b.id = 'spa-progress';
      b.style.cssText = 'position:fixed;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#6b5ce7,#6dd5ed);z-index:9999;transform-origin:left;transform:scaleX(0);transition:transform 300ms ease';
      document.body.appendChild(b);
    }
    requestAnimationFrame(() => { b.style.transform = 'scaleX(0.9)'; });
  }
  function hideSpaProgress() {
    const b = document.getElementById('spa-progress');
    if (!b) return;
    b.style.transform = 'scaleX(1)';
    setTimeout(() => { b.style.transform = 'scaleX(0)'; }, 200);
  }

  document.addEventListener('DOMContentLoaded', initSpaNav);

  // ----- Language / me helpers (unchanged) -----
  async function switchLang(lang) {
    if (!['he', 'en'].includes(lang)) return;
    await fetch('/auth/api/me', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language: lang }),
      credentials: 'include',
    });
    location.reload();
  }

  async function loadMe() {
    try {
      const res = await fetch('/auth/api/me', { credentials: 'include' });
      if (!res.ok) return null;
      return (await res.json()).data;
    } catch { return null; }
  }

  window.MARAMARA = { switchLang, loadMe, navigateTo };
})();
