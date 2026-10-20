/**
 * FlyRank Embeddable Widget & Lead-Capture Client Script (v1.0.0)
 *
 * One line installation:
 * <script src="http://localhost:8000/v1/widget.js?id=WIDGET_ID" defer></script>
 *
 * Features:
 * - Scoped DOM styling (zero global CSS leakage)
 * - Automatic config retrieval with client-side caching
 * - Anti-spam Honeypot field (_hp_website)
 * - Asynchronous cross-origin submission with CORS
 * - Accessible focus indicators and mobile responsive design
 */
(function () {
  'use strict';

  // 1. Identify Widget ID from script tag query string or data attribute
  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  if (!currentScript) {
    console.error('[FlyrankWidget] Unable to locate script tag.');
    return;
  }

  const scriptUrl = new URL(currentScript.src, window.location.href);
  const widgetId = scriptUrl.searchParams.get('id') || currentScript.getAttribute('data-widget-id');

  if (!widgetId) {
    console.error('[FlyrankWidget] Missing required "id" parameter in script tag.');
    return;
  }

  const apiBase = scriptUrl.origin;
  const configUrl = `${apiBase}/api/v1/widgets/${encodeURIComponent(widgetId)}/config`;

  // 2. Fetch Widget Configuration
  fetch(configUrl, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    cache: 'default'
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`Widget config error: ${response.status} ${response.statusText}`);
      }
      return response.json();
    })
    .then(config => {
      renderWidget(config, apiBase);
    })
    .catch(err => {
      console.error('[FlyrankWidget] Failed to initialize:', err);
    });

  // 3. Render Widget into DOM
  function renderWidget(config, baseUrl) {
    let targetEl = document.getElementById(`flyrank-widget-${config.id}`);
    if (!targetEl) {
      targetEl = document.createElement('div');
      targetEl.id = `flyrank-widget-${config.id}`;
      targetEl.className = 'flyrank-embed-root';
      if (currentScript.parentNode) {
        currentScript.parentNode.insertBefore(targetEl, currentScript.nextSibling);
      } else {
        document.body.appendChild(targetEl);
      }
    }

    const themeColor = config.theme_color || '#0D9488';

    // Inject Scoped Stylesheet once
    if (!document.getElementById('flyrank-widget-styles')) {
      const styleEl = document.createElement('style');
      styleEl.id = 'flyrank-widget-styles';
      styleEl.textContent = `
        .flyrank-widget-card {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          background: #FFFFFF;
          border: 1px solid #E2E8F0;
          border-radius: 12px;
          padding: 24px;
          max-width: 440px;
          box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
          color: #0F172A;
          box-sizing: border-box;
          margin: 16px 0;
        }
        .flyrank-widget-card * {
          box-sizing: border-box;
        }
        .flyrank-widget-title {
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 8px 0;
          color: #0F172A;
        }
        .flyrank-widget-desc {
          font-size: 13.5px;
          color: #64748B;
          margin: 0 0 16px 0;
          line-height: 1.45;
        }
        .flyrank-form-group {
          margin-bottom: 14px;
        }
        .flyrank-form-label {
          display: block;
          font-size: 12.5px;
          font-weight: 600;
          margin-bottom: 5px;
          color: #334155;
        }
        .flyrank-form-input, .flyrank-form-textarea {
          width: 100%;
          padding: 10px 12px;
          font-size: 14px;
          border: 1px solid #CBD5E1;
          border-radius: 6px;
          background-color: #F8FAFC;
          color: #0F172A;
          transition: border-color 0.15s ease, box-shadow 0.15s ease;
          outline: none;
        }
        .flyrank-form-input:focus, .flyrank-form-textarea:focus {
          border-color: ${themeColor};
          box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.15);
          background-color: #FFFFFF;
        }
        .flyrank-submit-btn {
          width: 100%;
          padding: 12px 18px;
          font-size: 14px;
          font-weight: 600;
          color: #FFFFFF;
          background-color: ${themeColor};
          border: none;
          border-radius: 6px;
          cursor: pointer;
          min-height: 46px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          transition: opacity 0.15s ease, transform 0.1s ease;
        }
        .flyrank-submit-btn:hover {
          opacity: 0.92;
        }
        .flyrank-submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .flyrank-hp {
          opacity: 0;
          position: absolute;
          top: 0;
          left: 0;
          height: 0;
          width: 0;
          z-index: -1;
          pointer-events: none;
        }
        .flyrank-alert {
          padding: 12px;
          border-radius: 6px;
          font-size: 13.5px;
          margin-top: 14px;
          display: none;
        }
        .flyrank-alert-success {
          background-color: #ECFDF5;
          color: #065F46;
          border: 1px solid #A7F3D0;
        }
        .flyrank-alert-error {
          background-color: #FEF2F2;
          color: #991B1B;
          border: 1px solid #FECACA;
        }
      `;
      document.head.appendChild(styleEl);
    }

    // Build Form Fields HTML
    let fieldsHtml = '';
    (config.form_fields || []).forEach(f => {
      const isRequired = f.required ? 'required' : '';
      const reqBadge = f.required ? ' *' : '';
      if (f.type === 'textarea') {
        fieldsHtml += `
          <div class="flyrank-form-group">
            <label class="flyrank-form-label" for="fr-${config.id}-${f.name}">${escapeHtml(f.label)}${reqBadge}</label>
            <textarea id="fr-${config.id}-${f.name}" name="${escapeHtml(f.name)}" class="flyrank-form-textarea" rows="3" placeholder="${escapeHtml(f.placeholder || '')}" ${isRequired}></textarea>
          </div>
        `;
      } else {
        fieldsHtml += `
          <div class="flyrank-form-group">
            <label class="flyrank-form-label" for="fr-${config.id}-${f.name}">${escapeHtml(f.label)}${reqBadge}</label>
            <input type="${f.type || 'text'}" id="fr-${config.id}-${f.name}" name="${escapeHtml(f.name)}" class="flyrank-form-input" placeholder="${escapeHtml(f.placeholder || '')}" ${isRequired} />
          </div>
        `;
      }
    });

    targetEl.innerHTML = `
      <div class="flyrank-widget-card" role="region" aria-label="${escapeHtml(config.title)}">
        <h3 class="flyrank-widget-title">${escapeHtml(config.title)}</h3>
        ${config.description ? `<p class="flyrank-widget-desc">${escapeHtml(config.description)}</p>` : ''}
        <form class="flyrank-widget-form" novalidate>
          <!-- Honeypot Field for Bot Detection -->
          <input type="text" name="_hp_website" class="flyrank-hp" tabindex="-1" autocomplete="off" />

          ${fieldsHtml}

          <button type="submit" class="flyrank-submit-btn">
            <span class="flyrank-btn-text">${escapeHtml(config.button_text || 'Submit')}</span>
          </button>

          <div class="flyrank-alert flyrank-alert-success" role="alert">
            ✓ Thank you! Your response has been received.
          </div>
          <div class="flyrank-alert flyrank-alert-error" role="alert"></div>
        </form>
      </div>
    `;

    // Wire Submission Handler
    const formEl = targetEl.querySelector('.flyrank-widget-form');
    const submitBtn = targetEl.querySelector('.flyrank-submit-btn');
    const btnText = targetEl.querySelector('.flyrank-btn-text');
    const alertSuccess = targetEl.querySelector('.flyrank-alert-success');
    const alertError = targetEl.querySelector('.flyrank-alert-error');

    formEl.addEventListener('submit', function (evt) {
      evt.preventDefault();
      alertSuccess.style.display = 'none';
      alertError.style.display = 'none';

      // Gather input data
      const formData = new FormData(formEl);
      const payloadData = {};
      let honeypotValue = null;

      formData.forEach((val, key) => {
        if (key === '_hp_website') {
          honeypotValue = val ? String(val).trim() : null;
        } else {
          payloadData[key] = String(val).trim();
        }
      });

      // Basic client-side required field check
      let missingField = false;
      (config.form_fields || []).forEach(f => {
        if (f.required && (!payloadData[f.name] || payloadData[f.name] === '')) {
          missingField = true;
        }
      });

      if (missingField) {
        alertError.textContent = 'Please fill out all required fields.';
        alertError.style.display = 'block';
        return;
      }

      // Enter loading state
      submitBtn.disabled = true;
      btnText.textContent = 'Sending...';

      const submitEndpoint = config.submit_url || `${baseUrl}/api/v1/widgets/${encodeURIComponent(config.id)}/submit`;

      fetch(submitEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          data: payloadData,
          _hp_website: honeypotValue
        })
      })
        .then(async res => {
          const body = await res.json().catch(() => ({}));
          if (!res.ok) {
            const errorMsg = body.detail || body.message || `Submission failed with status ${res.status}`;
            throw new Error(errorMsg);
          }
          return body;
        })
        .then(data => {
          formEl.reset();
          alertSuccess.style.display = 'block';
        })
        .catch(err => {
          alertError.textContent = err.message || 'Submission error. Please try again.';
          alertError.style.display = 'block';
        })
        .finally(() => {
          submitBtn.disabled = false;
          btnText.textContent = config.button_text || 'Submit';
        });
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
})();
