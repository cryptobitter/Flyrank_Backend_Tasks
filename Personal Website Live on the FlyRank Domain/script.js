/**
 * Aditya Rajput — Personal Portfolio & Infrastructure Showcase
 * Vanilla JavaScript (Zero external dependencies)
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initCvModal();
  initSmoothScroll();
  initLightbox();
  initImageFallbacks();
});

/**
 * Theme Toggle with LocalStorage & OS Preference Fallback
 */
function initTheme() {
  const themeToggle = document.getElementById('themeToggle');
  const htmlRoot = document.documentElement;

  // Retrieve saved theme or infer from system
  const savedTheme = localStorage.getItem('ar_portfolio_theme');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (savedTheme) {
    htmlRoot.setAttribute('data-theme', savedTheme);
  } else if (!prefersDark) {
    htmlRoot.setAttribute('data-theme', 'light');
  } else {
    htmlRoot.setAttribute('data-theme', 'dark');
  }

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = htmlRoot.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      htmlRoot.setAttribute('data-theme', newTheme);
      localStorage.setItem('ar_portfolio_theme', newTheme);
    });
  }
}

/**
 * CV Modal Controller
 */
function initCvModal() {
  const modal = document.getElementById('cvModal');
  const openBtn = document.getElementById('openCvModalBtn');
  const closeBtn = document.getElementById('closeCvModalBtn');
  const closeFooterBtn = document.getElementById('closeCvModalFooterBtn');
  const copyBtn = document.getElementById('copyCvLinkBtn');

  if (!modal) return;

  const openModal = () => {
    modal.classList.add('is-active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    modal.classList.remove('is-active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  };

  if (openBtn) openBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (closeFooterBtn) closeFooterBtn.addEventListener('click', closeModal);

  // Close on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeModal();
    }
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('is-active')) {
      closeModal();
    }
  });

  // Copy portfolio URL to clipboard
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const currentUrl = window.location.href;
      try {
        await navigator.clipboard.writeText(currentUrl);
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Link Copied!';
        copyBtn.style.backgroundColor = '#10b981';
        copyBtn.style.color = '#ffffff';

        setTimeout(() => {
          copyBtn.textContent = originalText;
          copyBtn.style.backgroundColor = '';
          copyBtn.style.color = '';
        }, 2000);
      } catch (err) {
        console.error('Clipboard copy failed:', err);
      }
    });
  }
}

/**
 * Accessible Certificate Lightbox Modal
 * - Keyboard accessible (Enter, Space to trigger)
 * - Esc key to close
 * - Focus trapping and restoration
 * - Descriptive alt text
 */
function initLightbox() {
  const lightbox = document.getElementById('certLightbox');
  const lightboxImg = document.getElementById('lightboxImage');
  const lightboxTitle = document.getElementById('lightboxTitle');
  const lightboxCaption = document.getElementById('lightboxCaption');
  const closeBtn = document.getElementById('closeLightboxBtn');
  const closeFooterBtn = document.getElementById('closeLightboxFooterBtn');

  if (!lightbox || !lightboxImg) return;

  let triggerElement = null;

  const openLightbox = (src, title, altText, trigger) => {
    triggerElement = trigger;
    lightboxImg.src = src;
    lightboxImg.alt = altText || title || 'Certificate Preview';
    if (lightboxTitle) lightboxTitle.textContent = title || 'Certificate Preview';
    if (lightboxCaption) lightboxCaption.textContent = title || '';

    lightbox.classList.add('is-open');
    lightbox.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    // Focus close button for accessible keyboard navigation
    if (closeBtn) {
      setTimeout(() => closeBtn.focus(), 50);
    }
  };

  const closeLightbox = () => {
    lightbox.classList.remove('is-open');
    lightbox.setAttribute('aria-hidden', 'true');
    lightboxImg.src = '';
    document.body.style.overflow = '';

    // Restore focus to trigger element
    if (triggerElement && typeof triggerElement.focus === 'function') {
      triggerElement.focus();
    }
  };

  // Attach listener to all certificate thumbnail buttons
  const certButtons = document.querySelectorAll('.cert-thumb-btn');
  certButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const src = btn.getAttribute('data-cert-src');
      const title = btn.getAttribute('data-cert-title') || 'Certificate Preview';
      const img = btn.querySelector('img');
      const altText = img ? img.getAttribute('alt') : title;
      if (src) {
        openLightbox(src, title, altText, btn);
      }
    });
  });

  if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
  if (closeFooterBtn) closeFooterBtn.addEventListener('click', closeLightbox);

  // Close on backdrop click (outside container)
  lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) {
      closeLightbox();
    }
  });

  // Keyboard navigation: Escape key to close, Tab trap
  document.addEventListener('keydown', (e) => {
    if (!lightbox.classList.contains('is-open')) return;

    if (e.key === 'Escape') {
      e.preventDefault();
      closeLightbox();
      return;
    }

    if (e.key === 'Tab') {
      const focusableElements = lightbox.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusableElements.length === 0) return;

      const firstEl = focusableElements[0];
      const lastEl = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === firstEl) {
          e.preventDefault();
          lastEl.focus();
        }
      } else {
        if (document.activeElement === lastEl) {
          e.preventDefault();
          firstEl.focus();
        }
      }
    }
  });
}

/**
 * Image Fallback Handler:
 * If any certificate thumbnail fails to load or file is missing,
 * remove/hide the container so nothing renders empty or broken.
 */
function initImageFallbacks() {
  const images = document.querySelectorAll('.credential-card img');
  images.forEach(img => {
    img.addEventListener('error', () => {
      const media = img.closest('.credential-media');
      if (media) {
        media.style.display = 'none';
      }
      const card = img.closest('.credential-card');
      if (card) {
        card.classList.add('no-media');
      }
    });
  });
}

/**
 * Smooth Scrolling for Anchor Links
 */
function initSmoothScroll() {
  const links = document.querySelectorAll('a[href^="#"]');
  
  links.forEach(link => {
    link.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#' || targetId === '') return;

      const targetEl = document.querySelector(targetId);
      if (targetEl) {
        e.preventDefault();
        targetEl.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
}
