(() => {
  const $ = (id) => document.getElementById(id);
  const colors = { safe: '#38c9cf', suspicious: '#e9ac55', critical: '#eb6c7a', honeypot: '#eb6c7a' };
  let events = [], counts = { safe: 0, suspicious: 0, honeypot: 0 }, toastTimer;
  let currentChartEvents = [];
  let activeFilter = 'all';
  let searchText = '';

  function getPointColor(e) {
    if (!e) return colors.safe;
    if (e.risk >= 70 || e.risk_band === 'critical') return colors.critical;
    if (e.risk >= 31 || e.risk_band === 'suspicious') return colors.suspicious;
    return colors.safe;
  }

  const lineCtx = $('riskChart').getContext('2d');
  const gradient = lineCtx.createLinearGradient(0, 0, 0, 180);
  gradient.addColorStop(0, 'rgba(56,201,207,.18)');
  gradient.addColorStop(1, 'rgba(56,201,207,0)');
  const riskChart = new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: colors.safe,
        backgroundColor: gradient,
        fill: true,
        borderWidth: 2,
        pointRadius: 3.5,
        pointHoverRadius: 5.5,
        pointBackgroundColor: [],
        pointBorderColor: '#101923',
        pointBorderWidth: 1.5,
        tension: .32
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 280 },
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f1722',
          borderColor: '#243342',
          borderWidth: 1,
          titleColor: '#e6edf3',
          titleFont: { family: 'DM Sans', size: 12, weight: 'bold' },
          bodyColor: '#9eacb9',
          bodyFont: { family: 'DM Mono', size: 11 },
          padding: 10,
          displayColors: true,
          boxWidth: 8,
          boxHeight: 8,
          usePointStyle: true,
          callbacks: {
            title: (items) => {
              if (!items.length) return '';
              const evt = currentChartEvents[items[0].dataIndex];
              if (!evt) return '';
              return `${timeLabel(evt.timestamp)} · ${classifyEvent(evt)}`;
            },
            label: (c) => {
              const evt = currentChartEvents[c.dataIndex];
              if (!evt) return ` Risk score: ${c.raw}`;
              const band = (evt.risk_band || (evt.risk >= 70 ? 'CRITICAL' : evt.risk >= 31 ? 'SUSPICIOUS' : 'SAFE')).toUpperCase();
              return ` Risk Score: ${evt.risk} / 100 [${band}]`;
            },
            afterLabel: (c) => {
              const evt = currentChartEvents[c.dataIndex];
              if (!evt) return [];
              const lines = [];
              if (evt.route === 'honeypot' || evt.bucket === 'honeypot') {
                lines.push(`🚨 Defense Action : HONEYPOT REDIRECTION (HTTP 302)`);
                lines.push(`🪤 Database Target: honeypot.db / Canary Store`);
              } else {
                lines.push(`✅ Defense Action : Production DB Allowed (HTTP 200)`);
                lines.push(`📦 Database Target: production.db [Catalog]`);
              }
              const cleanQ = (evt.query || '').trim();
              const truncatedQ = cleanQ.slice(0, 38) + (cleanQ.length > 38 ? '…' : '');
              lines.push(`🔍 Query Statement: "${truncatedQ}"`);
              if (evt.threats && evt.threats.length > 0) {
                lines.push(`⚠️ Threat Tags    : ${evt.threats.join(', ')}`);
              }
              return lines;
            },
            labelColor: (c) => {
              const evt = currentChartEvents[c.dataIndex];
              const color = evt ? getPointColor(evt) : '#38c9cf';
              return {
                borderColor: color,
                backgroundColor: color,
              };
            }
          }
        }
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: '#718091', font: { family: 'DM Mono', size: 8 }, maxTicksLimit: 7, maxRotation: 0 } },
        y: { min: 0, max: 100, grid: { color: 'rgba(125,143,160,.11)' }, border: { display: false, dash: [3, 5] }, ticks: { stepSize: 25, color: '#687788', font: { family: 'DM Mono', size: 8 }, padding: 7 } }
      }
    }
  });

  const doughnut = new Chart($('distributionChart').getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Safe', 'Suspicious', 'Honeypot'],
      datasets: [{
        data: [1, 0, 0],
        backgroundColor: ['#26363c', '#263239', '#2d2830'],
        borderWidth: 0,
        hoverOffset: 4,
        spacing: 3,
        borderRadius: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '79%',
      plugins: { legend: { display: false }, tooltip: { enabled: true, backgroundColor: '#18232e', padding: 8 } }
    }
  });

  const timeLabel = (iso) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return String(iso || '');
    }
  };

  const safeText = (v) => String(v ?? '');

  function classifyEvent(e) {
    if (e.query_type) return e.query_type;
    const q = (e.query || '').toLowerCase();
    const threats = (e.threats || []).join(' ').toLowerCase();
    if (e.bucket === 'safe' || (!threats && (q.includes('notebook') || q.includes('lamp') || q.includes('mug') || q.includes('catalog')))) {
      return 'Product Catalog Search';
    }
    if (threats.includes('port') || q.includes('port=')) return 'Port Reconnaissance Probe';
    if (threats.includes('destructive') || q.includes('drop table')) return 'SQLi · Destructive Drop/Delete';
    if (threats.includes('tautology') || q.includes("'1'='1") || q.includes("'or'")) return "SQLi · Tautology Bypass ('1'='1)";
    if (threats.includes('union') || q.includes('union select')) return 'SQLi · UNION Data Leak Probe';
    if (threats.includes('time-based') || q.includes('sleep(')) return 'SQLi · Blind Delay Fingerprint';
    if (threats.includes('script') || threats.includes('xss') || q.includes('<script')) return 'Cross-Site Scripting (XSS)';
    if (q.includes('users') || (e.table && e.table.includes('users'))) return 'Credential Exfiltration (users table)';
    if (q.includes('financial') || (e.table && e.table.includes('financial'))) return 'Financial Exfiltration (ledger)';
    return 'Suspicious Injection Attack';
  }

  function getBadgeClass(qtype) {
    const t = qtype.toLowerCase();
    if (t.includes('product') || t.includes('catalog')) return 'type-product';
    if (t.includes('port')) return 'type-port';
    if (t.includes('xss') || t.includes('script')) return 'type-xss';
    if (t.includes('credential') || t.includes('users')) return 'type-cred';
    if (t.includes('financial')) return 'type-fin';
    if (t.includes('sqli') || t.includes('injection')) return 'type-sqli';
    return 'type-other';
  }

  function getTypeIcon(qtype) {
    const t = qtype.toLowerCase();
    if (t.includes('product') || t.includes('catalog')) return '🛍️';
    if (t.includes('port')) return '🛡️';
    if (t.includes('xss') || t.includes('script')) return '⚡';
    if (t.includes('credential') || t.includes('users')) return '🚨';
    if (t.includes('financial')) return '💰';
    if (t.includes('sqli') || t.includes('injection')) return '💉';
    return '⚠️';
  }

  function getDbTarget(e) {
    if (e.db_target) return e.db_target;
    return e.route === 'production' ? 'production.db [Catalog]' : 'honeypot.db / Canary Store';
  }

  function updateCharts() {
    currentChartEvents = events.slice(-30);
    riskChart.data.labels = currentChartEvents.map(e => timeLabel(e.timestamp));
    riskChart.data.datasets[0].data = currentChartEvents.map(e => e.risk);
    riskChart.data.datasets[0].pointBackgroundColor = currentChartEvents.map(e => getPointColor(e));
    riskChart.data.datasets[0].pointBorderColor = currentChartEvents.map(e => (e.route === 'honeypot' || e.bucket === 'honeypot') ? '#ffffff' : '#101923');
    riskChart.data.datasets[0].pointBorderWidth = currentChartEvents.map(e => (e.route === 'honeypot' || e.bucket === 'honeypot') ? 2.5 : 1.5);
    riskChart.data.datasets[0].pointRadius = currentChartEvents.map(e => (e.route === 'honeypot' || e.bucket === 'honeypot') ? 5.5 : 3.5);
    riskChart.data.datasets[0].pointHoverRadius = currentChartEvents.map(e => (e.route === 'honeypot' || e.bucket === 'honeypot') ? 8 : 5.5);
    riskChart.update();
    $('emptyChart').classList.toggle('hidden', events.length > 0);

    const productEvents = events.filter(e => {
      const qtype = classifyEvent(e).toLowerCase();
      return e.bucket === 'safe' || qtype.includes('product');
    });

    const vals = [counts.safe || 0, counts.suspicious || 0, counts.honeypot || 0];
    const total = vals.reduce((a, b) => a + b, 0);
    doughnut.data.datasets[0].data = total ? vals : [1, 0, 0];
    doughnut.data.datasets[0].backgroundColor = total ? [colors.safe, colors.suspicious, colors.honeypot] : ['#26363c', '#263239', '#2d2830'];
    doughnut.update();

    $('donutTotal').textContent = total;
    $('totalCount').textContent = total;
    if ($('productCount')) $('productCount').textContent = productEvents.length;
    $('threatCount').textContent = vals[1] + vals[2];
    $('honeypotCount').textContent = vals[2];

    const mean = events.length ? Math.round(events.reduce((s, e) => s + e.risk, 0) / events.length) : 0;
    $('meanRisk').textContent = mean;
    $('riskMeter').style.width = `${mean}%`;
    $('riskMeter').style.background = mean >= 70 ? colors.honeypot : mean >= 31 ? colors.suspicious : colors.safe;

    [['safePct', vals[0]], ['suspiciousPct', vals[1]], ['honeypotPct', vals[2]]].forEach(([id, n]) => {
      $(id).textContent = `${total ? Math.round(n / total * 100) : 0}%`;
    });

    updateFilterCounts();
  }

  function updateFilterCounts() {
    let cAll = events.length;
    let cProd = 0, cAttacks = 0, cSqli = 0, cPort = 0, cXss = 0;

    events.forEach(e => {
      const qtype = classifyEvent(e).toLowerCase();
      const threats = (e.threats || []).join(' ').toLowerCase();
      const q = (e.query || '').toLowerCase();

      if (e.bucket === 'safe' || qtype.includes('product')) cProd++;
      if (e.bucket !== 'safe') cAttacks++;
      if (qtype.includes('sqli') || threats.includes('sqli') || q.includes('select') || q.includes("'1'='1") || q.includes('drop')) cSqli++;
      if (qtype.includes('port') || threats.includes('port') || q.includes('port=')) cPort++;
      if (qtype.includes('xss') || threats.includes('xss') || q.includes('<script') || q.includes('onerror=')) cXss++;
    });

    if ($('countAll')) $('countAll').textContent = cAll;
    if ($('countProducts')) $('countProducts').textContent = cProd;
    if ($('countAttacks')) $('countAttacks').textContent = cAttacks;
    if ($('countSqli')) $('countSqli').textContent = cSqli;
    if ($('countPort')) $('countPort').textContent = cPort;
    if ($('countXss')) $('countXss').textContent = cXss;
  }

  function matchesFilter(e) {
    const qtype = classifyEvent(e).toLowerCase();
    const threats = (e.threats || []).join(' ').toLowerCase();
    const q = (e.query || '').toLowerCase();

    if (activeFilter === 'products') {
      if (!(e.bucket === 'safe' || qtype.includes('product'))) return false;
    } else if (activeFilter === 'attacks') {
      if (e.bucket === 'safe') return false;
    } else if (activeFilter === 'sqli') {
      if (!(qtype.includes('sqli') || threats.includes('sqli') || q.includes('select') || q.includes("'1'='1") || q.includes('drop'))) return false;
    } else if (activeFilter === 'port') {
      if (!(qtype.includes('port') || threats.includes('port') || q.includes('port='))) return false;
    } else if (activeFilter === 'xss') {
      if (!(qtype.includes('xss') || threats.includes('xss') || q.includes('<script') || q.includes('onerror='))) return false;
    }

    if (searchText) {
      const term = searchText.toLowerCase();
      const haystack = `${e.query || ''} ${e.ip || ''} ${qtype} ${threats} ${e.site_context || ''} ${e.route || ''} ${e.table || ''}`.toLowerCase();
      if (!haystack.includes(term)) return false;
    }

    return true;
  }

  function renderRows() {
    $('eventCount').textContent = events.length;
    const body = $('eventRows');
    body.replaceChildren();

    const filtered = events.slice().reverse().filter(matchesFilter);

    if ($('filterStatus')) {
      if (activeFilter === 'all' && !searchText) {
        $('filterStatus').textContent = `Showing all ${events.length} logged queries`;
      } else {
        $('filterStatus').textContent = `Showing ${filtered.length} of ${events.length} events (Filter: ${activeFilter}${searchText ? ` · Search: "${searchText}"` : ''})`;
      }
    }

    if (!filtered.length) {
      const tr = document.createElement('tr');
      tr.className = 'empty-row';
      const td = document.createElement('td');
      td.colSpan = 7;
      td.innerHTML = `<span class="empty-symbol">⌁</span><b>No matching queries found</b><small>${events.length ? 'Try clearing or changing your search filters.' : 'Analyzed requests will appear here in real time.'}</small>`;
      tr.append(td);
      body.append(tr);
      return;
    }

    filtered.forEach(e => {
      const tr = document.createElement('tr');
      const qtype = classifyEvent(e);
      const dbTarget = getDbTarget(e);
      const isHoneypot = e.bucket === 'honeypot';
      const isSuspicious = e.bucket === 'suspicious';

      // 1. TIME
      const tdTime = document.createElement('td');
      tdTime.className = 'mono-cell';
      tdTime.textContent = timeLabel(e.timestamp);

      // 2. CLIENT IP
      const tdIp = document.createElement('td');
      tdIp.className = 'mono-cell';
      tdIp.textContent = safeText(e.ip);

      // 3. QUERY / SEARCH TERM
      const tdQuery = document.createElement('td');
      tdQuery.className = 'query-cell';
      tdQuery.title = `Click to inspect: ${safeText(e.query)}`;
      const site = document.createElement('small');
      site.className = 'site-ref';
      site.textContent = safeText(e.site_context || '—');
      const query = document.createElement('span');
      query.textContent = safeText(e.query);
      tdQuery.append(site, query);

      // 4. QUERY CLASSIFICATION
      const tdType = document.createElement('td');
      const typeSpan = document.createElement('span');
      typeSpan.className = `type-badge ${getBadgeClass(qtype)}`;
      typeSpan.textContent = `${getTypeIcon(qtype)} ${qtype}`;
      tdType.append(typeSpan);

      // 5. DATABASE ACCESSED
      const tdDb = document.createElement('td');
      const dbSpan = document.createElement('span');
      dbSpan.className = `dbtag ${e.route === 'production' ? 'dbtag-prod' : 'dbtag-decoy'}`;
      dbSpan.textContent = e.route === 'production' ? '🟢 production.db' : '🟠 honeypot.db';
      tdDb.append(dbSpan);

      // 6. RISK SCORE
      const tdRisk = document.createElement('td');
      const pill = document.createElement('span');
      const riskBand = e.risk_band || (e.risk >= 70 ? 'critical' : e.risk >= 31 ? 'suspicious' : 'safe');
      pill.className = `score-pill score-${riskBand}`;
      pill.textContent = safeText(e.risk);
      tdRisk.append(pill);

      // 7. DEFENSE ACTION
      const tdAction = document.createElement('td');
      tdAction.className = `route-cell route-${isHoneypot ? 'honeypot' : isSuspicious ? 'monitor' : 'safe'}`;
      tdAction.textContent = isHoneypot ? '302 Honeypot Redirect' : isSuspicious ? 'Flagged / Monitored' : '200 OK (Store Catalog)';

      tr.append(tdTime, tdIp, tdQuery, tdType, tdDb, tdRisk, tdAction);

      // Click to open detailed modal inspection
      tr.addEventListener('click', () => openEventModal(e));

      body.append(tr);
    });
  }

  function openEventModal(e) {
    const modal = $('eventModal');
    if (!modal) return;
    const qtype = classifyEvent(e);
    const dbTarget = getDbTarget(e);

    $('modalTitle').textContent = `SOC Audit: ${qtype}`;
    $('modalTime').textContent = e.timestamp || '—';
    $('modalIp').textContent = e.ip || '—';

    const typeBadge = $('modalTypeBadge');
    typeBadge.className = `type-badge ${getBadgeClass(qtype)}`;
    typeBadge.textContent = `${getTypeIcon(qtype)} ${qtype}`;

    const dbTag = $('modalDbTag');
    dbTag.className = `dbtag ${e.route === 'production' ? 'dbtag-prod' : 'dbtag-decoy'}`;
    dbTag.textContent = dbTarget;

    const riskPill = $('modalRiskPill');
    const band = e.risk_band || (e.risk >= 70 ? 'critical' : e.risk >= 31 ? 'suspicious' : 'safe');
    riskPill.className = `score-pill score-${band}`;
    riskPill.textContent = `${e.risk} / 100 (${band.toUpperCase()})`;

    $('modalRoute').textContent = e.route === 'production' ? 'Production Route (HTTP 200)' : 'Isolated Honeypot Decoy (HTTP 302)';
    $('modalRoute').style.color = e.route === 'production' ? colors.safe : colors.honeypot;

    $('modalRawQuery').textContent = e.query || '—';
    $('modalSiteContext').textContent = e.site_context || '—';

    const threatsBox = $('modalThreats');
    threatsBox.replaceChildren();
    if (!e.threats || !e.threats.length) {
      const chip = document.createElement('span');
      chip.className = 'threat-chip safe';
      chip.textContent = 'No Threat Signatures Matched';
      threatsBox.append(chip);
    } else {
      e.threats.forEach(t => {
        const chip = document.createElement('span');
        chip.className = `threat-chip${e.bucket === 'honeypot' ? '' : ' warn'}`;
        chip.textContent = t;
        threatsBox.append(chip);
      });
    }

    $('modalAction').textContent = e.action_taken || (e.route === 'production'
      ? 'Executed fixed parameterized lookup on data/production.db. Returned authentic catalog product records.'
      : 'Attack payload trapped before reaching database connection pool. Seamlessly deflected to isolated honeypot environment with single-use handoff broker.');

    modal.classList.remove('hidden');
  }

  function closeEventModal() {
    const modal = $('eventModal');
    if (modal) modal.classList.add('hidden');
  }

  if ($('closeModal')) $('closeModal').addEventListener('click', closeEventModal);
  if ($('eventModal')) {
    $('eventModal').addEventListener('click', (ev) => {
      if (ev.target === $('eventModal')) closeEventModal();
    });
  }

  // Filter Buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter || 'all';
      renderRows();
    });
  });

  // Search Filter
  if ($('telemetrySearch')) {
    $('telemetrySearch').addEventListener('input', (e) => {
      searchText = e.target.value.trim();
      renderRows();
    });
  }
  if ($('clearSearch')) {
    $('clearSearch').addEventListener('click', () => {
      if ($('telemetrySearch')) $('telemetrySearch').value = '';
      searchText = '';
      renderRows();
    });
  }

  // Export JSON
  if ($('exportJsonBtn')) {
    $('exportJsonBtn').addEventListener('click', () => {
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(events, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `sentinel_telemetry_logs_${Date.now()}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      notify('Exported telemetry audit logs as JSON file.');
    });
  }

  function paint() {
    updateCharts();
    renderRows();
  }

  function addEvent(evt, newCounts) {
    if (!evt) return;
    if (!events.some(x => x.id === evt.id)) events.push(evt);
    if (newCounts) counts = newCounts;
    else { counts[evt.bucket] = (counts[evt.bucket] || 0) + 1; }
    if (events.length > 200) events = events.slice(-200);
    paint();
  }

  function notify(message) {
    const el = $('toast');
    if (!el) return;
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
  }

  function showResult(result) {
    const panel = $('resultPanel');
    panel.classList.remove('hidden');
    panel.dataset.kind = result.bucket;
    $('resultRisk').textContent = result.risk;
    $('resultTrack').style.width = `${result.risk}%`;
    $('resultTrack').style.background = colors[result.bucket];
    $('resultRoute').textContent = result.route;
    $('resultRoute').style.color = colors[result.bucket];
    $('resultTitle').textContent = result.bucket === 'honeypot' ? 'Threat contained' : result.bucket === 'suspicious' ? 'Suspicious query flagged' : 'Query analyzed';
    $('resultThreats').textContent = result.threats.length ? result.threats.join(' · ') : 'No known signatures matched';
    $('resultSource').textContent = result.bucket === 'honeypot' ? 'Honeypot decoy database' : 'Production demo database';
    $('resultRows').textContent = JSON.stringify(result.rows, null, 2);
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  $('queryInput').addEventListener('input', e => $('charCount').textContent = `${e.target.value.length} / 2000`);
  document.querySelectorAll('[data-payload]').forEach(btn => btn.addEventListener('click', () => {
    $('queryInput').value = btn.dataset.payload;
    $('queryInput').dispatchEvent(new Event('input'));
    $('queryInput').focus();
  }));

  $('queryForm').addEventListener('submit', async e => {
    e.preventDefault();
    const button = e.currentTarget.querySelector('button[type="submit"]'), input = $('queryInput');
    button.disabled = true;
    button.querySelector('span').textContent = 'Analyzing…';
    const authToken = (window.SENTINEL_CONFIG && window.SENTINEL_CONFIG.authToken) || '';
    const authHeaders = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
    try {
      const res = await fetch('/api/query' + (authToken ? `?token=${encodeURIComponent(authToken)}` : ''), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ query: input.value, site_context: $('siteContext').value })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Request failed');
      showResult(data);
      const snapshot = await fetch('/api/events' + (authToken ? `?token=${encodeURIComponent(authToken)}` : '')).then(r => r.json());
      events = snapshot.events || [];
      counts = snapshot.counts || counts;
      paint();
    } catch (err) {
      notify(err.message || 'Unable to reach the detection engine.');
    } finally {
      button.disabled = false;
      button.querySelector('span').textContent = 'Analyze query';
    }
  });

  $('closeResult').addEventListener('click', () => $('resultPanel').classList.add('hidden'));

  $('clearBtn').addEventListener('click', () => {
    events = [];
    counts = { safe: 0, suspicious: 0, honeypot: 0 };
    paint();
    riskChart.data.labels = [];
    riskChart.data.datasets[0].data = [];
    riskChart.update();
    notify('Dashboard view cleared. Server event history remains for this session.');
  });

  const streamToken = (window.SENTINEL_CONFIG && window.SENTINEL_CONFIG.authToken) || '';
  const socket = io({
    transports: ['websocket', 'polling'],
    auth: { token: streamToken },
    query: { token: streamToken }
  });
  socket.on('telemetry', ({ event, counts: c }) => addEvent(event, c));
  socket.on('connect', () => { $('tableStatus').innerHTML = '<i></i> Listening for incoming events'; });
  socket.on('disconnect', () => { $('tableStatus').textContent = 'Reconnecting to telemetry stream…'; });

  fetch('/api/events' + (streamToken ? `?token=${encodeURIComponent(streamToken)}` : '')).then(r => r.json()).then(data => {
    events = data.events || [];
    counts = data.counts || counts;
    paint();
  }).catch(() => notify('Could not load event history.'));

  function tick() {
    $('clock').textContent = `${new Date().toLocaleTimeString([], { hour12: false })} LOCAL`;
  }
  tick();
  setInterval(tick, 1000);
})();
