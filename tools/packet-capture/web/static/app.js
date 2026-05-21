let currentConfig = null;

function showTab(tabId, btn) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
    if (tabId === 'config') loadConfig();
}

async function loadStats() {
    try {
        const resp = await fetch('/api/stats');
        const result = await resp.json();
        if (result.success) updateStats(result.data, result.gateway || {});
    } catch (e) {
        console.error('loadStats failed:', e);
    }
}

function updateStats(stats, gateway) {
    let totalSent = 0, totalReceived = 0, totalPrompt = 0, totalCompletion = 0;
    const container = document.getElementById('app-stats-container');
    container.innerHTML = '';

    for (const [name, s] of Object.entries(stats)) {
        const sent = s.TotalSentBytes || 0;
        const recv = s.TotalReceivedBytes || 0;
        const pt = s.TotalPromptTokens || 0;
        const ct = s.TotalCompletionTokens || 0;
        totalSent += sent;
        totalReceived += recv;
        totalPrompt += pt;
        totalCompletion += ct;

        const running = s.IsRunning || false;
        const network = s.HasNetworkConn || false;
        const procs = s.RunningProcessNames || [];
        const pnames = s.ProcessNames || [];

        let sc, st;
        if (running && network) { sc = 'status-network'; st = '联网'; }
        else if (running) { sc = 'status-running'; st = '运行'; }
        else { sc = 'status-stopped'; st = '离线'; }

        const card = document.createElement('div');
        card.className = 'app-stat-card';
        card.innerHTML = `
            <div class="app-stat-header">
                <h3>${name}</h3>
                <div class="app-status">
                    <span class="status-dot ${sc}"></span>
                    <span class="status-text">${st}</span>
                </div>
            </div>
            <div class="app-meta">
                <span class="meta-item">${s.ProviderName || '-'}</span>
                <span class="meta-item">${pnames.join(', ')}</span>
                ${procs.length ? `<span class="meta-item meta-running" title="${procs.join(', ')}">${procs.length > 6 ? procs.slice(0, 6).join(', ') + '...' : procs.join(', ')}</span>` : ''}
            </div>
            <div class="app-stat-details">
                <div class="app-stat-detail">
                    <label>发送</label>
                    <span>${formatBytes(sent)}</span>
                </div>
                <div class="app-stat-detail">
                    <label>接收</label>
                    <span>${formatBytes(recv)}</span>
                </div>
                <div class="app-stat-detail highlight">
                    <label>输入 Token</label>
                    <span>${pt.toLocaleString()}</span>
                </div>
                <div class="app-stat-detail highlight">
                    <label>输出 Token</label>
                    <span>${ct.toLocaleString()}</span>
                </div>
                <div class="app-stat-detail">
                    <label>本次输入</label>
                    <span>${(s.SessionPromptTokens || 0).toLocaleString()}</span>
                </div>
                <div class="app-stat-detail">
                    <label>本次输出</label>
                    <span>${(s.SessionCompletionTokens || 0).toLocaleString()}</span>
                </div>
                <div class="app-stat-detail">
                    <label>更新时间</label>
                    <span>${s.LastUpdate ? new Date(s.LastUpdate).toLocaleTimeString() : '-'}</span>
                </div>
            </div>`;
        container.appendChild(card);
    }

    document.getElementById('total-sent').textContent = formatBytes(totalSent);
    document.getElementById('total-received').textContent = formatBytes(totalReceived);
    document.getElementById('total-prompt').textContent = totalPrompt.toLocaleString();
    document.getElementById('total-completion').textContent = totalCompletion.toLocaleString();

    updateReportStats(gateway);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    if (i === 0) return bytes + ' B';
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + units[i];
}

async function loadConfig() {
    try {
        const resp = await fetch('/api/config');
        const result = await resp.json();
        if (result.success) {
            currentConfig = result.data;
            populateConfigForm(result.data);
        }
    } catch (e) {
        console.error('loadConfig failed:', e);
    }
}

function populateConfigForm(cfg) {
    document.getElementById('gateway-enabled').checked = cfg.gateway.enabled;
    renderAppList(cfg.monitored_apps || []);
}

function renderAppList(apps) {
    const container = document.getElementById('monitored-apps-container');
    container.innerHTML = '';
    apps.forEach((app, idx) => {
        const card = document.createElement('div');
        card.className = 'app-config-card';
        card.dataset.index = idx;
        card.innerHTML = `
            <div class="app-config-info">
                <span class="app-config-name">${app.name}</span>
                <span class="app-config-meta">${app.tool_name} / ${app.provider_name} / ${(app.process_names || []).join(', ')}</span>
            </div>
            <div class="app-config-actions">
                <button type="button" class="btn-icon btn-edit" title="编辑" onclick="editApp(${idx})">&#9998;</button>
                <button type="button" class="btn-icon" title="删除" onclick="removeApp(${idx})">&#10005;</button>
            </div>`;
        container.appendChild(card);
    });
}

let editingIndex = -1;

function openAddDialog() {
    editingIndex = -1;
    document.querySelector('#app-dialog .dialog-header h3').textContent = '添加应用';
    document.getElementById('dlg-name').value = '';
    document.getElementById('dlg-toolname').value = '';
    document.getElementById('dlg-provider').value = '';
    document.getElementById('dlg-process-names').value = '';
    document.getElementById('dlg-token-ratio').value = '4';
    document.getElementById('dlg-network-ratio').value = '0.05';
    clearDialogErrors();
    document.getElementById('app-dialog').style.display = '';
}

function editApp(idx) {
    if (!currentConfig || !currentConfig.monitored_apps) return;
    const app = currentConfig.monitored_apps[idx];
    if (!app) return;
    editingIndex = idx;
    document.querySelector('#app-dialog .dialog-header h3').textContent = '编辑应用';
    document.getElementById('dlg-name').value = app.name || '';
    document.getElementById('dlg-toolname').value = app.tool_name || '';
    document.getElementById('dlg-provider').value = app.provider_name || '';
    document.getElementById('dlg-process-names').value = (app.process_names || []).join(',');
    document.getElementById('dlg-token-ratio').value = app.token_ratio || 4;
    document.getElementById('dlg-network-ratio').value = app.network_ratio || 0.05;
    clearDialogErrors();
    document.getElementById('app-dialog').style.display = '';
}

function closeAddDialog() {
    document.getElementById('app-dialog').style.display = 'none';
}

function clearDialogErrors() {
    document.querySelectorAll('#app-dialog .form-group').forEach(g => g.classList.remove('error'));
}

function confirmAddApp() {
    if (!currentConfig) {
        showAlert('配置尚未加载，请稍后重试', 'error');
        return;
    }

    const name = document.getElementById('dlg-name').value.trim();
    const toolName = document.getElementById('dlg-toolname').value.trim();
    const provider = document.getElementById('dlg-provider').value.trim();
    const pStr = document.getElementById('dlg-process-names').value.trim();
    const tr = parseFloat(document.getElementById('dlg-token-ratio').value) || 4;
    const nr = parseFloat(document.getElementById('dlg-network-ratio').value) || 0.05;
    const pnames = pStr.split(',').map(s => s.trim()).filter(s => s);

    clearDialogErrors();
    let hasError = false;
    if (!name) { document.getElementById('dlg-name').parentElement.classList.add('error'); hasError = true; }
    if (!toolName) { document.getElementById('dlg-toolname').parentElement.classList.add('error'); hasError = true; }
    if (!provider) { document.getElementById('dlg-provider').parentElement.classList.add('error'); hasError = true; }
    if (!pnames.length) { document.getElementById('dlg-process-names').parentElement.classList.add('error'); hasError = true; }
    if (hasError) return;

    const app = { name, tool_name: toolName, provider_name: provider, process_names: pnames, token_ratio: tr, network_ratio: nr };

    if (!currentConfig.monitored_apps) currentConfig.monitored_apps = [];
    if (editingIndex >= 0) {
        currentConfig.monitored_apps[editingIndex] = app;
    } else {
        currentConfig.monitored_apps.push(app);
    }

    renderAppList(currentConfig.monitored_apps);
    closeAddDialog();
    saveConfig();
}

function removeApp(idx) {
    if (!currentConfig || !currentConfig.monitored_apps) return;
    const appName = currentConfig.monitored_apps[idx].name || '该应用';
    openConfirmDialog(`确定要删除应用「${appName}」吗？此操作不可撤销。`, () => {
        currentConfig.monitored_apps.splice(idx, 1);
        renderAppList(currentConfig.monitored_apps);
        saveConfig();
    });
}

let confirmCallback = null;

function openConfirmDialog(message, onConfirm) {
    document.getElementById('confirm-message').textContent = message;
    confirmCallback = onConfirm;
    document.getElementById('confirm-dialog').style.display = '';
}

function closeConfirmDialog() {
    document.getElementById('confirm-dialog').style.display = 'none';
    confirmCallback = null;
}

document.getElementById('confirm-ok-btn').addEventListener('click', () => {
    if (confirmCallback) confirmCallback();
    closeConfirmDialog();
});

document.getElementById('confirm-dialog').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeConfirmDialog();
});

function updateReportStats(gateway) {
    const successCount = gateway.success_count || 0;
    const failCount = gateway.fail_count || 0;
    const total = successCount + failCount;

    const statusEl = document.getElementById('report-status');
    const gatewayEnabled = currentConfig && currentConfig.gateway && currentConfig.gateway.enabled;
    const hasRecords = total > 0;

    if (gatewayEnabled) {
        if (failCount > 0 && successCount === 0) {
            statusEl.innerHTML = '<span class="status-dot status-stopped"></span><span class="text-danger">异常</span>';
        } else if (failCount > 0) {
            statusEl.innerHTML = '<span class="status-dot status-running"></span><span style="color:#e67e22">部分异常</span>';
        } else if (hasRecords) {
            statusEl.innerHTML = '<span class="status-dot status-network"></span><span style="color:var(--blue)">正常</span>';
        } else {
            statusEl.innerHTML = '<span class="status-dot status-running"></span><span style="color:var(--green)">已启用</span>';
        }
    } else if (hasRecords) {
        statusEl.innerHTML = '<span class="status-dot status-stopped"></span><span class="text-muted">已停用</span>';
    } else {
        statusEl.innerHTML = '<span class="status-dot status-stopped"></span><span class="text-muted">未启用</span>';
    }

    document.getElementById('report-success-count').textContent = successCount.toLocaleString();
    document.getElementById('report-fail-count').textContent = failCount.toLocaleString();
    document.getElementById('report-success-rate').textContent = total > 0 ? (successCount / total * 100).toFixed(1) + '%' : '-';
}

let reportChart = null;

async function loadReportHistory() {
    try {
        const resp = await fetch('/api/report-history');
        const result = await resp.json();
        if (result.success) renderReportChart(result.data || []);
    } catch (e) {
        console.error('loadReportHistory failed:', e);
    }
}

function renderReportChart(records) {
    const canvas = document.getElementById('report-chart');
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    const ctx = canvas.getContext('2d');

    if (!records.length) {
        if (reportChart) { reportChart.destroy(); reportChart = null; }
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif';
        ctx.fillStyle = '#999';
        ctx.textAlign = 'center';
        ctx.fillText('暂无上报记录', canvas.width / 2, canvas.height / 2);
        return;
    }

    const timeMap = {};
    records.forEach(r => {
        const t = new Date(r.timestamp);
        const key = t.getHours().toString().padStart(2, '0') + ':' + t.getMinutes().toString().padStart(2, '0');
        if (!timeMap[key]) timeMap[key] = { success: 0, fail: 0, prompt: 0, completion: 0 };
        if (r.success) {
            timeMap[key].success++;
            timeMap[key].prompt += r.prompt_tokens || 0;
            timeMap[key].completion += r.completion_tokens || 0;
        } else {
            timeMap[key].fail++;
        }
    });

    const labels = Object.keys(timeMap);
    const successData = labels.map(l => timeMap[l].success);
    const failData = labels.map(l => timeMap[l].fail);
    const promptData = labels.map(l => timeMap[l].prompt);
    const completionData = labels.map(l => timeMap[l].completion);

    if (reportChart) reportChart.destroy();

    reportChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: '成功',
                    type: 'bar',
                    data: successData,
                    backgroundColor: 'rgba(22, 163, 74, 0.7)',
                    borderColor: 'rgba(22, 163, 74, 1)',
                    borderWidth: 1,
                    borderRadius: 3,
                    yAxisID: 'y',
                    order: 2,
                },
                {
                    label: '失败',
                    type: 'bar',
                    data: failData,
                    backgroundColor: 'rgba(220, 38, 38, 0.7)',
                    borderColor: 'rgba(220, 38, 38, 1)',
                    borderWidth: 1,
                    borderRadius: 3,
                    yAxisID: 'y',
                    order: 2,
                },
                {
                    label: '输入Token',
                    type: 'line',
                    data: promptData,
                    borderColor: 'rgba(37, 99, 235, 0.9)',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: 'rgba(37, 99, 235, 1)',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y1',
                    order: 1,
                },
                {
                    label: '输出Token',
                    type: 'line',
                    data: completionData,
                    borderColor: 'rgba(8, 145, 178, 0.9)',
                    backgroundColor: 'rgba(8, 145, 178, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: 'rgba(8, 145, 178, 1)',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y1',
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,.75)',
                    padding: 10,
                    titleFont: { size: 12 },
                    bodyFont: { size: 12 },
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11 }, color: '#999' },
                },
                y: {
                    position: 'left',
                    title: { display: true, text: '次数', font: { size: 12 } },
                    beginAtZero: true,
                    ticks: { stepSize: 1, font: { size: 11 }, color: '#999' },
                    grid: { color: 'rgba(0,0,0,.05)' },
                },
                y1: {
                    position: 'right',
                    title: { display: true, text: 'Token 数', font: { size: 12 } },
                    beginAtZero: true,
                    ticks: { font: { size: 11 }, color: '#999' },
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

async function saveConfig() {
    if (!currentConfig) return;
    const newCfg = {
        server: { port: currentConfig.server.port, web_root: currentConfig.server.web_root },
        gateway: { url: currentConfig.gateway.url, enabled: document.getElementById('gateway-enabled').checked, report_interval: currentConfig.gateway.report_interval || 10 },
        monitored_apps: currentConfig.monitored_apps || [],
        log: currentConfig.log
    };

    try {
        const resp = await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newCfg) });
        const result = await resp.json();
        if (result.success) { 
            showAlert('配置已保存', 'success'); 
            currentConfig = newCfg;
            loadStats();
        } else {
            showAlert('保存失败: ' + result.error, 'error');
        }
    } catch (e) {
        showAlert('保存失败: ' + e.message, 'error');
    }
}

document.getElementById('gateway-enabled').addEventListener('change', () => {
    if (currentConfig) saveConfig();
});

document.getElementById('app-dialog').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeAddDialog();
});

function showAlert(msg, type) {
    const el = document.createElement('div');
    el.className = `alert alert-${type}`;
    el.textContent = msg;
    const tab = document.getElementById('config');
    tab.insertBefore(el, tab.firstChild);
    setTimeout(() => el.remove(), 3000);
}

loadConfig();
loadStats();
loadReportHistory();
setInterval(loadStats, 3000);
setInterval(loadReportHistory, 30000);
