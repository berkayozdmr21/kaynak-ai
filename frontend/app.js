const $ = id => document.getElementById(id);
let documents = [], selected = new Set(), busy = false;
const notice = (message, error = false) => { $('notice').textContent = message; $('notice').className = error ? 'error' : ''; };
async function api(path, options = {}) {
  const response = await fetch('/api' + path, options);
  if (!response.ok) {
    let message = 'İşlem başarısız (' + response.status + ')';
    try { const body = await response.json(); if (typeof body.detail === 'string') message = body.detail; } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function element(tag, text, className) {
  const node = document.createElement(tag); if (text !== undefined) node.textContent = text;
  if (className) node.className = className; return node;
}
function renderDocuments() {
  $('documents').replaceChildren(); $('count').textContent = documents.length;
  for (const doc of documents) {
    const row = element('div', undefined, 'document');
    const input = document.createElement('input'); input.type = 'checkbox'; input.id = 'doc-' + doc.id; input.checked = selected.has(doc.id);
    input.onchange = () => { input.checked ? selected.add(doc.id) : selected.delete(doc.id); updateSelection(); };
    const label = element('label', doc.name); label.htmlFor = input.id;
    label.append(element('small', `${doc.pages} sayfa · ${doc.chunks} metin parçası`));
    const remove = element('button', '×', 'delete'); remove.title = 'Belgeyi sil'; remove.setAttribute('aria-label', doc.name + ' belgesini sil');
    remove.onclick = async () => {
      if (busy || !confirm(`“${doc.name}” silinsin mi?`)) return;
      try { await api('/documents/' + doc.id, {method: 'DELETE'}); selected.delete(doc.id); await refresh(); $('result').hidden = true; notice('Belge silindi.'); } catch (e) { notice(e.message, true); }
    };
    row.append(input, label, remove); $('documents').append(row);
  }
  updateSelection();
}
function updateSelection() { $('selection').textContent = selected.size ? `${selected.size} belge seçili · Kaynaklı araştırma` : 'Önce bir belge seç'; }
async function refresh(newId) { documents = await api('/documents'); if (newId) selected.add(newId); selected = new Set([...selected].filter(id => documents.some(d => d.id === id))); renderDocuments(); }
async function upload(file) {
  if (!file || busy) return;
  if (file.size > 10 * 1024 * 1024) return notice('En fazla 10 MB dosya yükleyebilirsiniz.', true);
  busy = true; $('ask').disabled = true; notice('PDF okunuyor ve arama için hazırlanıyor…');
  try { const form = new FormData(); form.append('file', file); const doc = await api('/documents', {method: 'POST', body: form}); await refresh(doc.id); notice(`${doc.name} hazır. Sorunu sorabilirsin.`); }
  catch (e) { notice(e.message, true); }
  finally { busy = false; $('ask').disabled = false; $('file').value = ''; }
}
$('file').onchange = e => upload(e.target.files[0]);
for (const name of ['dragenter', 'dragover']) $('dropzone').addEventListener(name, e => { e.preventDefault(); $('dropzone').classList.add('drag'); });
for (const name of ['dragleave', 'drop']) $('dropzone').addEventListener(name, e => { e.preventDefault(); $('dropzone').classList.remove('drag'); });
$('dropzone').addEventListener('drop', e => upload(e.dataTransfer.files[0]));
$('demo').onclick = async () => {
  if (busy) return; busy = true; $('demo').disabled = true;
  try { const doc = await api('/demo', {method:'POST'}); await refresh(doc.id); notice('Örnek rehber hazır. Aşağıdaki örnek sorulardan birini seçebilirsin.'); }
  catch (e) { notice(e.message, true); } finally { busy = false; $('demo').disabled = false; }
};
document.querySelectorAll('[data-q]').forEach(button => button.onclick = () => { $('question').value = button.dataset.q; $('question').focus(); });
$('question').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); $('ask').click(); } });
$('ask').onclick = async () => {
  if (busy) return;
  const question = $('question').value.trim();
  if (question.length < 3) return notice('En az üç karakter içeren bir soru yaz.', true);
  if (!selected.size) return notice('Bir PDF ekle veya örnek belgelerle dene.', true);
  busy = true; $('ask').disabled = true; $('ask').textContent = 'Araştırılıyor…'; notice('Seçili belgelerde ilgili kaynaklar aranıyor…'); $('result').hidden = true;
  try {
    const result = await api('/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question, document_ids:[...selected]})});
    $('answer').textContent = result.answer;
    $('result-meta').textContent = `${result.mode === 'generated' ? 'Model yanıtı' : 'Kaynak alıntıları'} · ${result.latency_ms} ms`;
    $('source-count').textContent = result.sources.length; $('sources').replaceChildren();
    for (const source of result.sources) {
      const card = element('article', undefined, 'source');
      const title = element('div', undefined, 'source-title');
      title.append(element('span', '[' + source.citation + ']', 'citation'), element('span', source.name), element('span', 'Arama skoru ' + source.score.toFixed(2), 'score'));
      card.append(title, element('p', source.text));
      if (!source.name.startsWith('Örnek ·')) { const link = element('a', `Sayfa ${source.page} · PDF’i aç ↗`); link.href = '/api/documents/' + source.document_id + '/file#page=' + source.page; link.target = '_blank'; link.rel = 'noopener'; card.append(link); }
      else card.append(element('small', 'Örnek metin · Sayfa ' + source.page));
      $('sources').append(card);
    }
    $('result').hidden = false;
    notice(result.warning || (result.mode === 'extractive' && result.sources.length ? 'Alıntı modu: Metinler doğrudan belgelerden gelir; model tarafından özetlenmez. Arama skoru doğruluk olasılığı değildir.' : ''));
  } catch (e) { notice(e.message, true); }
  finally { busy = false; $('ask').disabled = false; $('ask').replaceChildren(document.createTextNode('Araştır '), element('span','↗')); }
};
(async () => {
  try { const health = await api('/health'); $('status').textContent = health.generation_enabled ? '● Model bağlantısı ayarlı' : '● Anahtarsız alıntı modu'; await refresh(); documents.forEach(doc => selected.add(doc.id)); renderDocuments(); }
  catch (e) { $('status').textContent = 'Bağlantı kurulamadı'; notice(e.message, true); }
})();
