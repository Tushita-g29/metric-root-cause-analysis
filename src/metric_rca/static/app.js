const backendStatusText = document.getElementById('backend-status-text');
const messageArea = document.getElementById('message-area');
const demoButton = document.getElementById('demo-button');
const realButton = document.getElementById('real-button');
const aiButton = document.getElementById('ai-button');

const summaryContent = document.getElementById('summary-content');
const anomalyContent = document.getElementById('anomaly-content');
const dataQualityContent = document.getElementById('data-quality-content');
const findingsContent = document.getElementById('findings-content');
const warningsContent = document.getElementById('warnings-content');
const aiContent = document.getElementById('ai-content');

let currentInvestigation = null;
let activeRequest = false;

function setMessage(text, type = 'info') {
    messageArea.textContent = text;
    messageArea.className = 'message-area';
    if (type === 'error') {
        messageArea.classList.add('error');
    } else if (type === 'success') {
        messageArea.classList.add('success');
    }
}

function setLoadingState(isLoading, label = 'Loading…') {
    activeRequest = isLoading;
    demoButton.disabled = isLoading;
    realButton.disabled = isLoading;
    aiButton.disabled = isLoading || !currentInvestigation;
    demoButton.textContent = isLoading ? label : 'Run Demo Investigation';
    realButton.textContent = isLoading ? label : 'Run Real Data Investigation';
}

function formatNumber(value, digits = 2) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return 'N/A';
    }
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function formatPercent(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return 'N/A';
    }
    const numeric = Number(value);
    const prefix = numeric >= 0 ? '+' : '';
    return `${prefix}${numeric.toFixed(1)}%`;
}

function setEmptyState(el, text) {
    el.className = 'empty-state';
    el.textContent = text;
}

function renderSummary(result) {
    const badges = [
        `<span class="badge ${result.status === 'anomaly_detected' ? 'status-positive' : 'status-neutral'}">${result.status}</span>`,
        `<span class="badge ${result.is_simulated ? 'simulated' : 'status-neutral'}">${result.is_simulated ? 'Simulated incident' : 'Real data'}</span>`,
        `<span class="badge ${result.mode === 'demo' ? 'simulated' : 'status-neutral'}">Mode: ${result.mode}</span>`,
    ].join('');

    const itemList = [
        { label: 'Status', value: result.status },
        { label: 'Mode', value: result.mode },
        { label: 'Simulated', value: result.is_simulated ? 'Yes' : 'No' },
        { label: 'Message', value: result.message || 'No message provided.' },
    ];

    summaryContent.className = 'summary-content';
    summaryContent.innerHTML = `
    <div class="badges">${badges}</div>
    <div class="metric-list">
      ${itemList.map((item) => `<div class="metric-item"><strong>${item.label}</strong><span>${item.value}</span></div>`).join('')}
    </div>
  `;
}

function renderAnomaly(result) {
    const anomaly = result.anomaly || {};
    const isAnomaly = Boolean(anomaly.is_drop_anomaly);

    if (!anomaly || Object.keys(anomaly).length === 0) {
        setEmptyState(anomalyContent, 'No anomaly data available.');
        return;
    }

    const metricItems = [
        ['Anomaly detected', isAnomaly ? 'Yes' : 'No'],
        ['Current period', anomaly.current_period_start && anomaly.current_period_end ? `${anomaly.current_period_start} to ${anomaly.current_period_end}` : 'N/A'],
        ['Baseline period', anomaly.baseline_period_start && anomaly.baseline_period_end ? `${anomaly.baseline_period_start} to ${anomaly.baseline_period_end}` : 'N/A'],
        ['Current metric value', anomaly.current_value !== undefined ? formatNumber(anomaly.current_value) : 'N/A'],
        ['Baseline metric value', anomaly.baseline_value !== undefined ? formatNumber(anomaly.baseline_value) : 'N/A'],
        ['Percentage change', anomaly.percent_change !== undefined ? formatPercent(anomaly.percent_change) : 'N/A'],
        ['Drop threshold p-value', anomaly.p_value !== undefined ? formatNumber(anomaly.p_value, 4) : 'N/A'],
    ];

    anomalyContent.className = 'summary-content';
    anomalyContent.innerHTML = `
    <div class="badges">
      <span class="badge ${isAnomaly ? 'status-positive' : 'status-neutral'}">${isAnomaly ? 'Anomaly detected' : 'No anomaly'}</span>
    </div>
    <div class="metric-list">
      ${metricItems.map(([label, value]) => `<div class="metric-item"><strong>${label}</strong><span>${value}</span></div>`).join('')}
    </div>
  `;
}

function renderDataQuality(result) {
    const quality = result.data_quality || {};
    if (!quality || Object.keys(quality).length === 0) {
        setEmptyState(dataQualityContent, 'No data quality summary yet.');
        return;
    }

    const metrics = [
        ['Row count', quality.row_count ?? 'N/A'],
        ['Date range', quality.date_range ? `${quality.date_range.start} to ${quality.date_range.end}` : 'N/A'],
        ['Total revenue', quality.total_revenue !== undefined ? formatNumber(quality.total_revenue) : 'N/A'],
        ['Unique sessions', quality.unique_sessions ?? 'N/A'],
    ];

    dataQualityContent.className = 'summary-content';
    dataQualityContent.innerHTML = `
    <div class="metric-list">
      ${metrics.map(([label, value]) => `<div class="metric-item"><strong>${label}</strong><span>${value}</span></div>`).join('')}
    </div>
  `;
}

function renderFindings(result) {
    const findings = result.ranked_findings || [];
    if (!findings.length) {
        setEmptyState(findingsContent, 'No ranked contributors were identified for this investigation.');
        return;
    }

    const rows = findings.map((item) => `
    <tr>
      <td>${item.rank ?? ''}</td>
      <td>${item.dimension ?? 'N/A'}</td>
      <td>${item.segment ?? 'N/A'}</td>
      <td>${item.revenue_shortfall !== undefined ? formatNumber(item.revenue_shortfall) : 'N/A'}</td>
      <td>${item.percent_change !== undefined ? formatPercent(item.percent_change) : 'N/A'}</td>
      <td>${item.adjusted_p_value !== undefined ? formatNumber(item.adjusted_p_value, 4) : 'N/A'}</td>
    </tr>
  `).join('');

    findingsContent.className = 'summary-content';
    findingsContent.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Dimension</th>
            <th>Segment</th>
            <th>Revenue shortfall</th>
            <th>% change</th>
            <th>Adjusted p-value</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderWarnings(result) {
    const warnings = result.confound_warnings || [];
    if (!warnings.length) {
        setEmptyState(warningsContent, 'No overlap or confound warnings were detected.');
        return;
    }

    const cards = warnings.map((warning) => {
        const title = warning.segment_pair || warning.dimension_pair || 'Overlap warning';
        const message = warning.warning || 'Overlapping contributors may reflect shared patterns and must not be presented as independent causes.';
        return `
      <div class="warning-item">
        <h3>${Array.isArray(title) ? title.join(' / ') : title}</h3>
        <p>${message}</p>
      </div>
    `;
    }).join('');

    warningsContent.className = 'summary-content';
    warningsContent.innerHTML = `<div class="warning-list">${cards}</div>`;
}

function renderAiExplanation(text) {
    aiContent.className = 'summary-content';
    aiContent.innerHTML = `<div class="ai-box">${text}</div>`;
}

function clearAiExplanation() {
    aiContent.className = 'empty-state';
    aiContent.textContent = 'No AI explanation generated yet.';
}

async function runInvestigation(mode) {
    if (activeRequest) {
        return;
    }

    setLoadingState(true, 'Running…');
    setMessage(`Running ${mode} investigation…`, 'info');
    summaryContent.className = 'summary-content';
    summaryContent.textContent = 'Loading investigation…';
    anomalyContent.className = 'empty-state';
    anomalyContent.textContent = 'Loading anomaly data…';
    dataQualityContent.className = 'empty-state';
    dataQualityContent.textContent = 'Loading data quality summary…';
    findingsContent.className = 'empty-state';
    findingsContent.textContent = 'Loading ranked contributors…';
    warningsContent.className = 'empty-state';
    warningsContent.textContent = 'Loading overlap warnings…';
    clearAiExplanation();

    try {
        const response = await fetch(`/investigate?mode=${mode}`);
        if (!response.ok) {
            throw new Error(`Investigation failed (${response.status}).`);
        }

        const result = await response.json();
        currentInvestigation = result;
        aiButton.classList.remove('hidden');
        aiButton.disabled = false;
        setMessage(`Investigation completed: ${result.status}.`, 'success');
        renderSummary(result);
        renderAnomaly(result);
        renderDataQuality(result);
        renderFindings(result);
        renderWarnings(result);
    } catch (error) {
        currentInvestigation = null;
        aiButton.classList.add('hidden');
        setMessage(error.message || 'Investigation failed.', 'error');
        summaryContent.className = 'empty-state';
        summaryContent.textContent = 'No investigation results available.';
        anomalyContent.className = 'empty-state';
        anomalyContent.textContent = 'No anomaly data available.';
        dataQualityContent.className = 'empty-state';
        dataQualityContent.textContent = 'No data quality summary yet.';
        findingsContent.className = 'empty-state';
        findingsContent.textContent = 'No ranked findings yet.';
        warningsContent.className = 'empty-state';
        warningsContent.textContent = 'No overlap warnings yet.';
        clearAiExplanation();
    } finally {
        setLoadingState(false);
    }
}

async function handleAiExplanation() {
    if (!currentInvestigation) {
        setMessage('Run an investigation before requesting an AI explanation.', 'error');
        return;
    }

    setLoadingState(true, 'Generating…');
    setMessage('Generating AI explanation…', 'info');
    aiButton.disabled = true;

    try {
        const mode = currentInvestigation.mode || 'real';
        const response = await fetch(`/investigate/explanation?mode=${mode}`);
        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || `AI explanation failed (${response.status}).`);
        }

        const result = await response.json();
        renderAiExplanation(result.explanation || 'No explanation returned.');
        setMessage('AI explanation generated successfully.', 'success');
    } catch (error) {
        setMessage(`AI explanation unavailable: ${error.message || 'Unknown error.'}`, 'error');
        renderAiExplanation('The AI explanation could not be generated. Please try again later or check the backend status.');
    } finally {
        setLoadingState(false);
        aiButton.disabled = !currentInvestigation;
    }
}

async function checkBackendStatus() {
    try {
        const response = await fetch('/health');
        if (!response.ok) {
            throw new Error('health check failed');
        }
        const data = await response.json();
        backendStatusText.textContent = data.status === 'ok' ? 'Backend healthy' : 'Backend status unknown';
    } catch (error) {
        backendStatusText.textContent = 'Backend offline';
        messageArea.textContent = 'The backend is currently unavailable.';
        messageArea.className = 'message-area error';
    }
}

demoButton.addEventListener('click', () => runInvestigation('demo'));
realButton.addEventListener('click', () => runInvestigation('real'));
aiButton.addEventListener('click', handleAiExplanation);

checkBackendStatus();
