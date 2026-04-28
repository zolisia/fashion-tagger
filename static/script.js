const form = document.getElementById('tag-form');
const urlInput = document.getElementById('url');
const submitBtn = document.getElementById('submit');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const imageEl = document.getElementById('result-image');
const tagsEl = document.getElementById('tags');

const LABELS = {
  garment_type: 'Garment',
  neckline: 'Neckline',
  sleeve_type: 'Sleeve',
  silhouette: 'Silhouette',
  formality: 'Formality',
};

function setStatus(msg, isError = false) {
  if (!msg) {
    statusEl.hidden = true;
    statusEl.textContent = '';
    statusEl.classList.remove('error');
    return;
  }
  statusEl.hidden = false;
  statusEl.classList.toggle('error', isError);
  statusEl.innerHTML = isError
    ? msg
    : `<span class="spinner"></span>${msg}`;
}

function renderResult(imageUrl, tags) {
  imageEl.src = imageUrl;
  imageEl.alt = `${tags.garment_type ?? 'product'} preview`;
  tagsEl.innerHTML = '';
  for (const [key, label] of Object.entries(LABELS)) {
    const value = tags[key] ?? '—';
    const row = document.createElement('div');
    row.innerHTML = `<dt>${label}</dt><dd>${value}</dd>`;
    tagsEl.appendChild(row);
  }
  resultEl.hidden = false;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  resultEl.hidden = true;
  submitBtn.disabled = true;
  setStatus('Fetching the image and reading the garment…');

  try {
    const res = await fetch('/api/tag', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const detail = data.detail || `Request failed (${res.status})`;
      setStatus(detail, true);
      return;
    }

    setStatus('');
    renderResult(data.image_url, data.tags);
  } catch (err) {
    setStatus(`Network error: ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});
