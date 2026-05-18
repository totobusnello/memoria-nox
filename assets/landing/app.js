/* memoria-nox landing — minimal JS
 * No analytics. No tracking. No framework.
 * Activates on DOMContentLoaded.
 */
(function () {
  'use strict';

  /* Scroll-reveal: fade-in sections as they enter the viewport */
  function initReveal() {
    if (!('IntersectionObserver' in window)) return;

    var targets = document.querySelectorAll(
      '.usp-card, .stat, .pillar-card, .arch-layers li'
    );

    targets.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(12px)';
      el.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'none';
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );

    targets.forEach(function (el) { observer.observe(el); });
  }

  document.addEventListener('DOMContentLoaded', initReveal);
})();
