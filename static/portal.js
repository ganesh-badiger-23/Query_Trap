(() => {
  const $ = id => document.getElementById(id);
  let bag = 0, toastTimer;

  // ── Toast Notification Helper ─────────────────────────────────────────────
  function toast(message) {
    const el = $('portalToast');
    if (!el) return;
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
  }

  // ── "Add to Bag" Interactivity ───────────────────────────────────────────
  document.querySelectorAll('.add-button').forEach(button => {
    button.addEventListener('click', e => {
      e.preventDefault();
      bag++;
      const bagEl = $('bagCount');
      if (bagEl) bagEl.textContent = bag;
      
      const itemName = button.dataset.item || 'Item';
      const originalHtml = button.innerHTML;
      button.innerHTML = 'Added <span>✓</span>';
      button.classList.add('added');
      toast(`Added "${itemName}" to your studio bag.`);

      setTimeout(() => {
        button.innerHTML = originalHtml;
        button.classList.remove('added');
      }, 1400);
    });
  });

  const config = window.SENTINEL_CONFIG || {};

  function getQueryUrl() {
    if (config.sentinelUrl && !config.isUnified) {
      return `${config.sentinelUrl.replace(/\/+$/, '')}/api/query`;
    }
    return '/api/query';
  }

  function getHoneypotRedirect(handoffToken) {
    let base = config.replicaUrl || config.honeypotUrl || (config.isUnified ? '/honeypot' : 'http://127.0.0.1:5300/');
    const separator = base.includes('?') ? '&' : '?';
    return `${base}${separator}handoff=${encodeURIComponent(handoffToken)}`;
  }

  // ── Product Icon Finder ───────────────────────────────────────────────────
  function getProductIcon(name) {
    const s = String(name).toLowerCase();
    if (s.includes('notebook')) return '📓';
    if (s.includes('lamp') || s.includes('light')) return '💡';
    if (s.includes('mug') || s.includes('cup')) return '☕';
    if (s.includes('pen')) return '✒️';
    if (s.includes('leather') || s.includes('mat')) return '💼';
    if (s.includes('organizer') || s.includes('tray')) return '🗂️';
    if (s.includes('sleeve')) return '💻';
    if (s.includes('riser')) return '🖥️';
    return '📦';
  }

  // ── Render Dynamic Search Results in the Products Grid ────────────────────
  function renderProductsGrid(rows, queryText) {
    const grid = $('productsGrid');
    if (!grid) return;

    if (!rows || !rows.length) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 48px 24px; background: #fff; border-radius: 12px; border: 1px dashed #cbd5e1;">
          <span style="font-size: 32px; display: block; margin-bottom: 12px;">🔍</span>
          <h3 style="font: 700 20px var(--font-serif); margin: 0 0 8px; color: var(--pine-900);">No objects found for "${queryText}"</h3>
          <p style="color: var(--slate-500); font-size: 13.5px; margin: 0 0 16px;">Try searching for stationery, brass desk lamps, or leather organizers.</p>
          <a href="${config.storefrontUrl || '/'}" style="display: inline-block; padding: 8px 18px; border-radius: 20px; background: var(--pine-800); color: #fff; font-weight: 600; font-size: 12px;">Browse full collection →</a>
        </div>
      `;
      return;
    }

    grid.replaceChildren();
    rows.forEach(p => {
      const article = document.createElement('article');
      article.className = 'product-card';
      const priceNum = Number(p.price || 0).toFixed(2);
      const badgeText = p.price > 80 ? 'PREMIUM CRAFT' : (p.price < 25 ? 'BESTSELLER' : 'STUDIO FAVORITE');

      article.innerHTML = `
        <div class="card-image-wrap">
          <span class="stock-badge">${badgeText}</span>
          <div class="product-art-preview ${String(p.category || '').toLowerCase()}">
            <div class="art-icon-circle">${getProductIcon(p.item)}</div>
          </div>
        </div>
        <div class="product-info">
          <div class="product-category-row">
            <span class="product-cat">${p.category || 'Collection'}</span>
            <span class="product-rating">★★★★★ <small>(4.9)</small></span>
          </div>
          <h3 class="product-name">${p.item}</h3>
          <div class="product-footer">
            <span class="product-price">$${priceNum}</span>
            <button class="add-button" data-item="${p.item}" data-price="${priceNum}">
              Add to Bag <span>+</span>
            </button>
          </div>
        </div>
      `;
      
      const btn = article.querySelector('.add-button');
      btn.addEventListener('click', e => {
        e.preventDefault();
        bag++;
        const bagEl = $('bagCount');
        if (bagEl) bagEl.textContent = bag;
        btn.innerHTML = 'Added <span>✓</span>';
        btn.classList.add('added');
        toast(`Added "${p.item}" to your studio bag.`);
        setTimeout(() => {
          btn.innerHTML = 'Add to Bag <span>+</span>';
          btn.classList.remove('added');
        }, 1400);
      });

      grid.append(article);
    });
  }

  // ── Unified Search Handler (Handles Hero & Header Inputs) ──────────────────
  async function performSearch(query, triggerBtn) {
    if (!query) return;
    if (triggerBtn) {
      triggerBtn.disabled = true;
      triggerBtn.style.opacity = '0.7';
    }

    try {
      const response = await fetch(getQueryUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: query, 
          search_term: query, 
          site_context: `${location.origin}/` 
        }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Search service unavailable');

      // Transparent Redirection to Honeypot if Malicious / High-Risk
      if (data.bucket === 'honeypot') {
        location.assign(getHoneypotRedirect(data.handoff));
        return;
      }

      // Safe Query: Update UI smoothly with genuine catalog results
      renderProductsGrid(data.rows, query);
      const col = $('collection');
      if (col) col.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      toast('Search could not be completed right now. Please try again.');
    } finally {
      if (triggerBtn) {
        triggerBtn.disabled = false;
        triggerBtn.style.opacity = '1';
      }
    }
  }

  // Bind Hero Search Form
  const heroForm = $('searchForm');
  if (heroForm) {
    heroForm.addEventListener('submit', e => {
      e.preventDefault();
      const q = $('searchQuery').value.trim();
      const btn = heroForm.querySelector('.search-submit-btn');
      performSearch(q, btn);
    });
  }

  // Bind Header Search Form
  const headerForm = $('headerSearchForm');
  if (headerForm) {
    headerForm.addEventListener('submit', e => {
      e.preventDefault();
      const q = $('headerSearchInput').value.trim();
      const btn = headerForm.querySelector('button');
      performSearch(q, btn);
    });
  }

  // ── Handle Address-Bar Initial Query (?q=notebook) ───────────────────────
  const init = window.PORTAL_INITIAL || {};
  if (init.searched && init.rows !== null) {
    renderProductsGrid(init.rows, init.query || '');
    if (init.query) {
      if ($('searchQuery')) $('searchQuery').value = init.query;
      if ($('headerSearchInput')) $('headerSearchInput').value = init.query;
    }
  }
})();
