/* ═══════════════════════════════════════════════════════════════
   LENS BASE — Shared Behavior
   Extracted from Work Order (the 90% reference).
   Every lens <script src>s this file. Lens-specific JS goes inline.
   ═══════════════════════════════════════════════════════════════ */

// Theme toggle — CSS handles icon visibility via .icon-sun / .icon-moon rules
function toggleTheme() {
  var html = document.documentElement;
  var current = html.getAttribute('data-theme');
  html.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
}

// Section collapse/expand
function toggleSec(id) {
  document.getElementById(id).classList.toggle('collapsed');
}

// Dropdown
function toggleDd(e) {
  e.stopPropagation();
  document.getElementById('dd').classList.toggle('open');
}
function closeDd() {
  document.getElementById('dd').classList.remove('open');
}
document.addEventListener('click', closeDd);

// Scroll reveal
var obs = new IntersectionObserver(function(entries) {
  entries.forEach(function(e) {
    if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
  });
}, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(function(el) { obs.observe(el); });
setTimeout(function() {
  document.querySelectorAll('.reveal').forEach(function(el) {
    if (el.getBoundingClientRect().top < window.innerHeight) {
      el.classList.add('visible'); obs.unobserve(el);
    }
  });
}, 80);
