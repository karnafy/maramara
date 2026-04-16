/* MARAMARA — Minimal client-side helpers */

(function () {
  'use strict';

  // Update language preference via profile API
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

  // Auto-refresh nav user email from /auth/api/me
  async function loadMe() {
    try {
      const res = await fetch('/auth/api/me', { credentials: 'include' });
      if (!res.ok) return;
      return (await res.json()).data;
    } catch (e) { return null; }
  }

  window.MARAMARA = { switchLang, loadMe };
})();
