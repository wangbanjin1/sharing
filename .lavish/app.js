/* Shared interactive script for Multi-HTML Agent Evaluation Hub */
function toggleTheme() {
  const b = document.body;
  const next = b.getAttribute('data-theme') === 'github' ? 'parchment' : 'github';
  b.setAttribute('data-theme', next);
  try { localStorage.setItem('agent_bench_theme', next); } catch(e) {}
}

(function initTheme() {
  try {
    const saved = localStorage.getItem('agent_bench_theme');
    if (saved) document.body.setAttribute('data-theme', saved);
  } catch(e) {}
})();

function toggleAllDetails(openState) {
  document.querySelectorAll('details.paper-card').forEach(d => {
    d.open = openState;
  });
}

function filterPapers(query, catFilter) {
  const q = (query || '').trim().toLowerCase();
  const cat = catFilter || window._currentCat || 'all';
  window._currentCat = cat;
  document.querySelectorAll('.paper-item').forEach(el => {
    const text = (el.getAttribute('data-search') || el.innerText || '').toLowerCase();
    const itemCat = el.getAttribute('data-cat') || 'all';
    const matchQ = !q || text.includes(q);
    const matchC = (cat === 'all') || (itemCat === cat);
    el.style.display = (matchQ && matchC) ? '' : 'none';
  });
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.classList.toggle('primary', btn.getAttribute('data-cat') === cat);
  });
}

window.addEventListener('DOMContentLoaded', () => {
  if (window.location.hash) {
    const target = document.querySelector(window.location.hash);
    if (target && target.tagName.toLowerCase() === 'details') {
      target.open = true;
      setTimeout(() => target.scrollIntoView({behavior: 'smooth', block: 'start'}), 100);
    }
  }
});
