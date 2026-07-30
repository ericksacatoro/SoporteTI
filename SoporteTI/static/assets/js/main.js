/**
 * Helpdesk TI - main.js
 * Solo inicializa lo que existe en la app: AOS y scroll-top.
 * Se removieron GLightbox, PureCounter, Isotope, Swiper que no están instalados.
 */
(function () {
  "use strict";

  /* AOS (Animate On Scroll) */
  function aosInit() {
    if (typeof AOS !== 'undefined') {
      AOS.init({ duration: 600, easing: 'ease-in-out', once: true, mirror: false });
    }
  }
  window.addEventListener('load', aosInit);

  /* Scroll-top button (solo si existe el elemento) */
  var scrollTop = document.querySelector('.scroll-top');
  if (scrollTop) {
    function toggleScrollTop() {
      window.scrollY > 100
        ? scrollTop.classList.add('active')
        : scrollTop.classList.remove('active');
    }
    scrollTop.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    window.addEventListener('load', toggleScrollTop);
    document.addEventListener('scroll', toggleScrollTop);
  }

})();
