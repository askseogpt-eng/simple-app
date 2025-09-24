document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('primary-navigation');

  if (!toggle || !nav) {
    return;
  }

  const closeOnEscape = (event) => {
    if (event.key === 'Escape') {
      setOpenState(false);
      toggle.focus();
    }
  };

  const setOpenState = (isOpen) => {
    toggle.setAttribute('aria-expanded', String(isOpen));
    nav.classList.toggle('is-open', isOpen);
    document.body.classList.toggle('nav-open', isOpen);
    toggle.classList.toggle('is-active', isOpen);

    if (isOpen) {
      document.addEventListener('keydown', closeOnEscape);
    } else {
      document.removeEventListener('keydown', closeOnEscape);
    }
  };

  toggle.addEventListener('click', () => {
    const isOpen = toggle.getAttribute('aria-expanded') === 'true';
    setOpenState(!isOpen);
  });

  nav.addEventListener('click', (event) => {
    if (event.target instanceof HTMLAnchorElement && toggle.offsetParent !== null) {
      setOpenState(false);
    }
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 768) {
      setOpenState(false);
    }
  });
});
