/* Shared chrome: topbar (with brand mark + nav + ⌘K) and helpers
   No sidebar, no filesystem breadcrumb — distinct from ARL reference.
*/

function renderTopbar(activePage) {
  const links = [
    { href: 'index.html#home', key: 'home', label: 'Overview' },
    { href: 'index.html#leaderboard', key: 'leaderboard', label: 'Leaderboard' },
    { href: 'index.html#browse', key: 'browse', label: 'Browse tasks' },
    { href: 'index.html#method', key: 'method', label: 'Methodology' },
    { href: 'index.html#findings', key: 'findings', label: 'Findings' },
  ];
  return `
    <div class="topbar">
      <div class="topbar-inner">
        <a href="index.html" class="brand">
          <span class="brand-mark"></span>
          <span class="brand-text">
            DEEPWEB-BENCH
            <span class="brand-text-ver">arXiv 2605.21482</span>
          </span>
        </a>
        <nav class="topbar-nav">
          ${links.map(l => `<a href="${l.href}" class="topbar-link ${activePage === l.key ? 'active' : ''}">${l.label}</a>`).join('')}
        </nav>
        <div class="topbar-actions">
          <button id="cmdk-open" class="btn btn-secondary btn-sm" style="gap: 8px">
            <span>Search</span>
            <span class="kbd">⌘K</span>
          </button>
          <a href="https://github.com/sixiongxie1001-dot/deep-research-benchmark2.0" class="btn btn-ghost btn-sm">GitHub</a>
        </div>
      </div>
    </div>
  `;
}

function renderFooter() {
  return `
    <footer class="footer">
      <div class="container">
        <div class="footer-grid">
          <div>
            <a href="index.html" class="brand">
              <span class="brand-mark"></span>
              <span class="brand-text">DEEPWEB-BENCH</span>
            </a>
            <p class="footer-brand-text">A deep research benchmark.</p>
            <p class="footer-brand-sub">Massive evidence collection, cross-source reconciliation, and long-horizon multi-step derivation across 100 industry-grounded tasks. 6,400 cells, graded by an independent rubric.</p>
          </div>
          <div class="footer-col">
            <h4>Project</h4>
            <ul>
              <li><a href="index.html#home">Overview</a></li>
              <li><a href="index.html#leaderboard">Leaderboard</a></li>
              <li><a href="index.html#browse">Browse tasks</a></li>
              <li><a href="index.html#method">Methodology</a></li>
            </ul>
          </div>
          <div class="footer-col">
            <h4>Resources</h4>
            <ul>
              <li><a href="https://github.com/sixiongxie1001-dot/deep-research-benchmark2.0">GitHub</a></li>
              <li><a href="https://huggingface.co/datasets/deepweb-bench-anon/deepweb-bench">Hugging Face dataset</a></li>
              <li><a href="https://gitee.com/xie-sixiong/deep-research-benchmark">Gitee mirror</a></li>
            </ul>
          </div>
          <div class="footer-col">
            <h4>Affiliation</h4>
            <ul>
              <li>Peking University</li>
              <li style="margin-top: 6px; color: var(--text-faint); font-size: 11px">11 authors · 3 equal contribution</li>
            </ul>
          </div>
        </div>
        <div class="footer-bottom">
          <span>© 2026 DEEPWEB-BENCH · Data CC-BY-4.0 · Code MIT</span>
          <span class="mono">v3.8 · 100 × 9 × 64 cells</span>
        </div>
      </div>
    </footer>
  `;
}

function renderCmdK() {
  return `
    <div id="cmdk" class="cmdk-overlay">
      <div class="cmdk-modal">
        <input id="cmdk-input" class="cmdk-input" placeholder="Search 100 cases by domain, entity, or ID…" autocomplete="off" spellcheck="false">
        <div id="cmdk-list" class="cmdk-list styled-scroll"></div>
        <div class="cmdk-foot">
          <span><span class="kbd">↑↓</span> navigate · <span class="kbd">↵</span> open</span>
          <span><span class="kbd">esc</span> close</span>
        </div>
      </div>
    </div>
  `;
}

/* Cmd+K palette */
function initCmdK(cases) {
  const cmdk = document.getElementById('cmdk');
  const input = document.getElementById('cmdk-input');
  const list = document.getElementById('cmdk-list');
  let sel = 0;
  let results = [];

  function open() {
    cmdk.classList.add('open');
    input.value = '';
    update('');
    setTimeout(() => input.focus(), 30);
  }
  function close() { cmdk.classList.remove('open'); }
  function update(q) {
    q = q.toLowerCase().trim();
    results = (!q ? cases.slice(0, 20)
      : cases.filter(c => (c.case_id + ' ' + c.title + ' ' + c.domain + ' ' + c.entities.join(' ')).toLowerCase().includes(q))
    ).slice(0, 30);
    sel = 0;
    render();
  }
  function render() {
    if (!results.length) {
      list.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-faint); font-size: 13px">No results</div>';
      return;
    }
    list.innerHTML = results.map((c, i) => `
      <div class="cmdk-item ${i === sel ? 'selected' : ''}" data-idx="${i}">
        <div style="display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0">
          <span class="case-id">${c.case_id}</span>
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">${c.domain || c.title}</span>
        </div>
        ${c.avg_score != null ? `<span class="pill ${scoreClass(c.avg_score)}">${c.avg_score.toFixed(1)}</span>` : ''}
      </div>`).join('');
    list.querySelectorAll('.cmdk-item').forEach(el => {
      el.addEventListener('mouseenter', () => { sel = +el.dataset.idx; render(); });
      el.addEventListener('click', () => { location.href = 'case.html?id=' + encodeURIComponent(results[+el.dataset.idx].case_id); });
    });
  }

  const openBtn = document.getElementById('cmdk-open');
  if (openBtn) openBtn.addEventListener('click', open);
  cmdk.addEventListener('click', e => { if (e.target === cmdk) close(); });
  input.addEventListener('input', e => update(e.target.value));
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); cmdk.classList.contains('open') ? close() : open(); }
    if (cmdk.classList.contains('open')) {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowDown') { sel = Math.min(results.length - 1, sel + 1); render(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { sel = Math.max(0, sel - 1); render(); e.preventDefault(); }
      else if (e.key === 'Enter' && results[sel]) location.href = 'case.html?id=' + encodeURIComponent(results[sel].case_id);
    }
  });
}

/* Scroll shadow */
window.addEventListener('scroll', () => {
  document.body.classList.toggle('scrolled', window.scrollY > 8);
}, { passive: true });

/* Score helpers — globals */
window.scoreClass = function(s) {
  if (s == null) return 'pill-neutral';
  if (s >= 20 && s <= 35) return 'pill-pass';
  if (s > 35) return 'pill-easy';
  return 'pill-hard';
};
window.verdictBadge = function(v) {
  const c = { pass: { l: 'Pass', cls: 'badge-pass' }, too_easy: { l: 'Easy', cls: 'badge-easy' }, too_hard: { l: 'Hard', cls: 'badge-hard' } }[v];
  return c ? `<span class="badge ${c.cls}">${c.l}</span>` : '';
};
window.scoreColor = function(s) {
  if (s == null) return '#f4f1ea';
  if (s >= 20 && s <= 35) {
    // teal scale
    const t = Math.min(1, (s - 20) / 15);
    return `hsl(174, ${36 + t * 30}%, ${82 - t * 18}%)`;
  }
  if (s > 35) {
    const t = Math.min(1, (s - 35) / 30);
    return `hsl(217, ${36 + t * 24}%, ${84 - t * 20}%)`;
  }
  const t = Math.min(1, (20 - s) / 20);
  return `hsl(0, ${36 + t * 26}%, ${86 - t * 16}%)`;
};
window.scoreTextColor = function(s) {
  if (s == null) return 'var(--text-faint)';
  if (s >= 30 || s <= 8) return '#fff';
  return 'var(--text)';
};

window.renderTopbar = renderTopbar;
window.renderFooter = renderFooter;
window.renderCmdK = renderCmdK;
window.initCmdK = initCmdK;
