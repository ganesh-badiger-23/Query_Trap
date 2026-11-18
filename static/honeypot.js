(async () => {
  const $ = id => document.getElementById(id);
  const token = new URLSearchParams(location.search).get('handoff');
  let result = (() => {
    try {
      return JSON.parse(sessionStorage.getItem('honeypotResult') || 'null');
    } catch {
      return null;
    }
  })();

  if (token) {
    try {
      const response = await fetch(`/api/handoff/${encodeURIComponent(token)}`);
      if (response.ok) {
        result = await response.json();
        sessionStorage.setItem('honeypotResult', JSON.stringify(result));
      }
    } catch {
      result = null;
    }
    history.replaceState({}, '', location.pathname);
  }

  let rows = result?.rows || [
    { id: 1, item: 'Field notebook', category: 'Stationery', price: 8.50 },
    { id: 2, item: 'Desk lamp', category: 'Home', price: 24.00 },
    { id: 3, item: 'Travel mug', category: 'Kitchen', price: 16.25 },
  ];
  let cols = rows.length ? Object.keys(rows[0]) : ['id', 'item', 'category', 'price'];
  let filtered = [...rows], sortKey = '', sortAsc = true;
  const title = s => String(s || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());

  const CANARY_KEYS = new Set([
    'canary_token',
    'canary_serial',
    'canary_hash',
    'jwt_canary_id',
    'api_secret',
    'access_key_id',
    'password_hash',
    'vault_sig',
    'routing_transit',
    'swift_bic'
  ]);

  function isCanaryField(key) {
    return CANARY_KEYS.has(key) || key.startsWith('canary_');
  }

  function syncDisplayMetadata() {
    if (result) {
      let queryDisplay = '';
      const q = (result.query || '').trim();
      if (q) {
        if (q.toLowerCase().startsWith('select') || q.toLowerCase().startsWith('insert') || q.toLowerCase().startsWith('update')) {
          queryDisplay = q;
        } else if (q.includes("'") || q.includes('=')) {
          queryDisplay = `SELECT * FROM ${result.table || 'public_catalog'} WHERE item = '${q.replace(/'/g, "''")}'; -- (Extracted query)`;
        } else {
          queryDisplay = `SELECT * FROM ${result.table || 'public_catalog'} WHERE instr(lower(item), '${q.toLowerCase()}') > 0 ORDER BY id ASC LIMIT 50;`;
        }
      } else {
        queryDisplay = `SELECT * FROM ${result.table || 'public_catalog'} ORDER BY id ASC LIMIT 50;`;
      }
      
      $('requestText').textContent = queryDisplay;
      $('siteContextValue').textContent = 'Internal Data Gateway · API Proxy Node 127.0.0.1';
      $('requestTime').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      $('recordCaption').textContent = `${title(result.table || 'database')} · ${rows.length} records retrieved`;
      $('activityTime').textContent = 'Just now';

      if (result.is_synthetic) {
        const tabs = $('datasetTabs');
        if (tabs) tabs.classList.remove('hidden');
      }
    }
  }

  syncDisplayMetadata();

  function renderHead() {
    const head = document.createElement('tr');
    cols.forEach(key => {
      const th = document.createElement('th');
      th.textContent = `${title(key)}${sortKey === key ? (sortAsc ? ' ↑' : ' ↓') : ' ↕'}`;
      th.title = 'Sort by ' + title(key);
      th.className = 'sortable' + (isCanaryField(key) ? ' canary-col' : '');
      th.addEventListener('click', () => {
        sortAsc = sortKey === key ? !sortAsc : true;
        sortKey = key;
        render();
      });
      head.append(th);
    });
    $('tableHead').replaceChildren(head);
  }

  function render() {
    renderHead();
    const body = $('tableBody');
    body.replaceChildren();
    const query = $('recordSearch').value.trim().toLowerCase();
    filtered = rows.filter(row => Object.values(row).some(value => String(value).toLowerCase().includes(query)));
    if (sortKey) {
      filtered.sort((a, b) => {
        const av = a[sortKey], bv = b[sortKey];
        return (typeof av === 'number' && typeof bv === 'number'
          ? av - bv
          : String(av).localeCompare(String(bv), undefined, { numeric: true, sensitivity: 'base' })) * (sortAsc ? 1 : -1);
      });
    }
    if (!filtered.length) {
      const tr = document.createElement('tr'), td = document.createElement('td');
      td.colSpan = Math.max(cols.length, 1);
      td.className = 'no-records';
      td.textContent = 'No records match this filter.';
      tr.append(td);
      body.append(tr);
    }
    filtered.forEach(row => {
      const tr = document.createElement('tr');
      tr.className = 'record-row';
      tr.tabIndex = 0;
      tr.setAttribute('role', 'button');
      tr.setAttribute('aria-label', 'Inspect record ' + (row.id ?? ''));
      cols.forEach(key => {
        const td = document.createElement('td');
        if (key === 'id') td.className = 'hp-id';
        if (key === 'balance') td.className = 'hp-balance';
        
        if (isCanaryField(key)) {
          const badge = document.createElement('span');
          badge.className = 'canary-cell';
          badge.textContent = String(row[key] ?? '');
          td.append(badge);
        } else if (key === 'role') {
          const badge = document.createElement('span');
          badge.className = `role-badge ${String(row[key]).toLowerCase() === 'admin' ? 'role-admin' : ''}`;
          badge.textContent = String(row[key]);
          td.append(badge);
        } else {
          td.textContent = String(row[key] ?? '');
        }
        tr.append(td);
      });
      const inspect = () => showDetail(row);
      tr.addEventListener('click', inspect);
      tr.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inspect();
        }
      });
      body.append(tr);
    });
    $('rowCount').textContent = `${filtered.length} of ${rows.length} records`;
  }

  function showDetail(row) {
    $('detailTitle').textContent = `${title(result?.table || 'workspace')} · ${row.id ?? 'record'}`;
    const fields = $('detailFields');
    fields.replaceChildren();
    Object.entries(row).forEach(([key, value]) => {
      const group = document.createElement('div'),
        label = document.createElement('small'),
        content = document.createElement('b');
      label.textContent = title(key);
      content.textContent = String(value ?? '');
      if (isCanaryField(key)) {
        content.className = 'canary-cell';
      }
      group.append(label, content);
      fields.append(group);
    });
    $('recordDetail').classList.remove('hidden');
  }

  $('recordSearch').addEventListener('input', render);
  $('resetFilter').addEventListener('click', () => {
    $('recordSearch').value = '';
    sortKey = '';
    render();
  });
  $('closeDetail').addEventListener('click', () => $('recordDetail').classList.add('hidden'));

  async function loadDataset(datasetName) {
    try {
      const res = await fetch(`/api/decoy/records?table=synthetic_${encodeURIComponent(datasetName)}&source=synthetic`);
      if (res.ok) {
        const data = await res.json();
        if (data.rows && data.rows.length) {
          rows = data.rows;
          cols = Object.keys(rows[0]);
          if (!result) result = {};
          result.table = data.table;
          result.is_synthetic = true;
          $('recordCaption').textContent = `${title(data.table)} · ${rows.length} records retrieved`;
          syncDisplayMetadata();
          render();
        }
      }
    } catch (e) {
      console.warn('Dataset load failed:', e);
    }
  }

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const ds = btn.dataset.dataset;
      if (ds) {
        loadDataset(ds);
      }
    });
  });

  $('refreshBtn').addEventListener('click', async () => {
    $('refreshBtn').classList.add('is-refreshing');
    try {
      const targetTable = result?.table || 'users';
      const source = result?.is_synthetic ? '&source=synthetic' : '';
      const res = await fetch(`/api/decoy/records?table=${encodeURIComponent(targetTable)}${source}`);
      if (res.ok) {
        const data = await res.json();
        if (data.rows && data.rows.length) {
          rows = data.rows;
          cols = Object.keys(rows[0]);
        }
      }
    } catch {
      // Fallback to local refresh
    } finally {
      $('activityTime').textContent = 'Just now';
      $('syncLabel').textContent = 'Data synced just now';
      render();
      setTimeout(() => $('refreshBtn').classList.remove('is-refreshing'), 450);
    }
  });

  function tick() {
    $('hpClock').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  render();
  tick();
  setInterval(tick, 30000);
})();
