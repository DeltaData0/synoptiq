export function renderTrust(element, evaluation) {
  element.innerHTML = `<h2>Trust & evaluation</h2><p><strong>${evaluation.status}</strong> — ${evaluation.message}</p><p>Data mode: <code>${evaluation.data_mode}</code>. API documentation: <a href="http://127.0.0.1:8000/docs">/docs</a>.</p>`;
}

