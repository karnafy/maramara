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

  // ----- Topic → Hebrew label + SVG icon -----
  // Used across home, insights, recordings to render topics consistently in RTL.
  const TOPIC_MAP = {
    work:          { he: 'עבודה',  icon: 'briefcase' },
    relationships: { he: 'זוגיות',  icon: 'heart' },
    family:        { he: 'משפחה',   icon: 'home' },
    health:        { he: 'בריאות',  icon: 'pulse' },
    money:         { he: 'כסף',     icon: 'wallet' },
    self:          { he: 'עצמי',    icon: 'user' },
    environment:   { he: 'סביבה',   icon: 'globe' },
    other:         { he: 'אחר',     icon: 'dots' },
  };
  const TOPIC_ICONS = {
    briefcase: '<path d="M9 4h6a2 2 0 0 1 2 2v2h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2h3V6a2 2 0 0 1 2-2zm0 4h6V6H9v2z" fill="currentColor"/>',
    heart:     '<path d="M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2.5 4.5-9.5 9-9.5 9z" fill="currentColor"/>',
    home:      '<path d="M3 11.5 12 4l9 7.5V20a2 2 0 0 1-2 2h-4v-6h-6v6H5a2 2 0 0 1-2-2v-8.5z" fill="currentColor"/>',
    pulse:     '<path d="M3 12h4l2-6 4 12 2-6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
    wallet:    '<path d="M3 7a2 2 0 0 1 2-2h12v2H5v10h14V9h-3a2 2 0 0 0 0 4h4v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" fill="currentColor"/>',
    user:      '<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 1 1 14 0H5z" fill="currentColor"/>',
    globe:     '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 2a8 8 0 0 1 3.5.8c-.5 1-1.4 1.7-2.5 1.9V8a2 2 0 0 1-2 2H9a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2h1v3a2 2 0 0 0 2 2v-.1A8 8 0 0 1 12 4z" fill="currentColor"/>',
    dots:      '<circle cx="5" cy="12" r="2" fill="currentColor"/><circle cx="12" cy="12" r="2" fill="currentColor"/><circle cx="19" cy="12" r="2" fill="currentColor"/>',
  };

  function topicLabel(raw) {
    if (!raw) return 'אחר';
    const k = String(raw).toLowerCase().trim();
    return (TOPIC_MAP[k] && TOPIC_MAP[k].he) || raw;
  }
  function topicIconSvg(raw) {
    const k = String(raw || 'other').toLowerCase().trim();
    const name = (TOPIC_MAP[k] && TOPIC_MAP[k].icon) || 'dots';
    const inner = TOPIC_ICONS[name] || TOPIC_ICONS.dots;
    return `<svg viewBox="0 0 24 24" aria-hidden="true">${inner}</svg>`;
  }

  // Merge — don't overwrite. Other partials (e.g. _mood_gauge.html) also
  // populate window.MARAMARA, and this script runs after them.
  window.MARAMARA = Object.assign(window.MARAMARA || {}, {
    switchLang, loadMe, navigateTo, topicLabel, topicIconSvg,
  });
})();
