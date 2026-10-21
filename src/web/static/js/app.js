"use strict";
const $ = id => document.getElementById(id);
let prediction = null, categories = [], thresholds = {}, offset = 0, revision = 0, busy = false;
const editingId = document.body.dataset.page === "editor" ? new URLSearchParams(location.search).get("article") : null;
let editingArticle = null, modelLoaded = false, pendingDelete = null, deleting = false;
function message(text, error = false) { $("message").textContent = text; $("message").className = error ? "error" : ""; }
async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options});
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Confira os campos informados.");
  return result;
}
function option(value, label) { const node = document.createElement("option"); node.value = value; node.textContent = label; return node; }
function invalidate() {
  revision++; prediction = null; $("analysis-result").hidden = true; $("empty-analysis").hidden = false;
  $("confirmed").checked = false; $("save").disabled = true;
  $("word-count").textContent = `${$("content").value.trim().split(/\s+/).filter(Boolean).length} palavras`;
}
function showAnalysis(result, choices = categories, finalCategory = result.predicted_category) {
  prediction = result;
  $("suggested-category").textContent = result.predicted_category;
  $("confidence").textContent = `${(100 * result.confidence).toFixed(1)}%`;
  $("confidence-bar").style.width = `${result.confidence * 100}%`;
  $("confidence-label").textContent = result.confidence >= thresholds.high ? "Alta confiança" : result.confidence >= thresholds.medium ? "Revisão recomendada" : "Classificação incerta";
  $("candidates").replaceChildren(...result.top_k.map(c => {
    const li = document.createElement("li"), label = document.createElement("span"), value = document.createElement("strong");
    label.textContent = c.category; value.textContent = `${(100*c.confidence).toFixed(1)}%`; li.append(label, value); return li;
  }));
  $("final-category").replaceChildren(...choices.map(c => option(c, c)));
  $("final-category").value = finalCategory;
  $("empty-analysis").hidden = true; $("analysis-result").hidden = false;
}
async function init() {
  try {
    const [health, config] = await Promise.all([api("/health"), api("/api/categories")]);
    categories = config.categories; thresholds = config.thresholds;
    modelLoaded = health.model_loaded;
    $("model-status").textContent = !health.model_loaded ? "Modelo indisponível. Configure um modelo treinado para analisar notícias." : health.demo ? "Modo demonstração · Modelo treinado com dados sintéticos. Os resultados não representam qualidade em notícias reais." : `Modelo disponível · Versão ${health.model_version}`;
    $("model-status").classList.toggle("ready", health.model_loaded && !health.demo);
    if (document.body.dataset.page === "editor") {
      $("final-category").replaceChildren(...categories.map(c => option(c, c)));
      if (editingId) {
        editingArticle = await api(`/api/articles/${encodeURIComponent(editingId)}`);
        $("title").value = editingArticle.title;
        $("content").value = editingArticle.content;
        invalidate();
        showAnalysis(editingArticle.analysis, editingArticle.categories, editingArticle.final_category);
      }
      $("analyze").disabled = !modelLoaded;
    } else {
      $("filter-category").append(...categories.map(c => option(c, c)));
      await loadHistory();
      if (new URLSearchParams(location.search).get("updated") === "1") message("Notícia atualizada. As alterações também estão no feed.");
    }
  } catch (error) { $("model-status").textContent = "Não foi possível conectar ao serviço."; message(error.message, true); }
}
if (document.body.dataset.page === "editor") {
  ["title", "content"].forEach(id => $(id).addEventListener("input", invalidate));
  $("final-category").addEventListener("change", () => { $("confirmed").checked = false; $("save").disabled = true; });
  $("confirmed").addEventListener("change", () => { $("save").disabled = !$("confirmed").checked || !prediction || busy; });
  $("editor-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy) return;
    invalidate(); const currentRevision = revision;
    busy = true; $("analyze").disabled = true; $("analyze").textContent = "Analisando…"; message("");
    try {
      const result = await api("/api/classify", {method: "POST", body: JSON.stringify({title: $("title").value, content: $("content").value})});
      if (revision !== currentRevision) { message("O texto mudou durante a análise. Analise novamente."); return; }
      showAnalysis(result);
    } catch (error) { message(error.message, true); }
    finally { busy = false; $("analyze").disabled = !modelLoaded; $("analyze").textContent = "Analisar notícia ↗"; }
  });
  $("save").addEventListener("click", async () => {
    if (!prediction || !$("confirmed").checked || busy || (editingId && !editingArticle)) return;
    busy = true; $("save").disabled = true;
    try {
      const payload = {prediction_id:prediction.prediction_id, final_category:$("final-category").value, confirmed:true};
      if (editingId) payload.expected_revision = editingArticle.revision;
      await api(editingId ? `/api/articles/${encodeURIComponent(editingId)}` : "/api/articles", {
        method: editingId ? "PUT" : "POST", body: JSON.stringify(payload)
      });
      if (editingId) { location.assign("/history?updated=1"); return; }
      invalidate(); message("Decisão salva. Consulte o histórico editorial.");
    } catch (error) { message(error.message, true); $("save").disabled = false; }
    finally { busy = false; }
  });
} else {
  ["filter-category", "filter-correction"].forEach(id => $(id).addEventListener("change", () => { offset = 0; loadHistory().catch(e => message(e.message, true)); }));
  $("previous").addEventListener("click", () => { offset = Math.max(0, offset - 20); loadHistory().catch(e => message(e.message, true)); });
  $("next").addEventListener("click", () => { offset += 20; loadHistory().catch(e => message(e.message, true)); });
  $("cancel-delete").addEventListener("click", () => $("delete-dialog").close());
  $("delete-dialog").addEventListener("cancel", event => { if (deleting) event.preventDefault(); });
  $("delete-dialog").addEventListener("close", () => { pendingDelete = null; });
  $("confirm-delete").addEventListener("click", async () => {
    if (!pendingDelete || deleting) return;
    deleting = true; $("confirm-delete").disabled = true; $("cancel-delete").disabled = true;
    $("delete-error").textContent = "";
    try {
      await api(`/api/articles/${pendingDelete.id}`, {method:"DELETE", body:JSON.stringify({
        confirmed: true, expected_revision: pendingDelete.revision
      })});
      $("delete-dialog").close();
      message("Notícia removida do histórico e do feed.");
      await loadHistory();
      $("total").focus();
    } catch (error) {
      if ($("delete-dialog").open) $("delete-error").textContent = error.message;
      else message(`Notícia removida, mas não foi possível atualizar a lista. ${error.message}`, true);
    } finally {
      deleting = false; $("confirm-delete").disabled = false; $("cancel-delete").disabled = false;
    }
  });
}
let historyRequest = 0;
async function loadHistory() {
  const request = ++historyRequest;
  const params = new URLSearchParams({offset, limit:20});
  if ($("filter-category").value) params.set("category", $("filter-category").value);
  if ($("filter-correction").value) params.set("was_corrected", $("filter-correction").value);
  const result = await api(`/api/articles?${params}`);
  if (request !== historyRequest) return;
  if (offset > 0 && offset >= result.total) {
    offset = result.total ? Math.floor((result.total - 1) / 20) * 20 : 0;
    return loadHistory();
  }
  $("history-body").replaceChildren(...result.items.map(item => {
    const tr = document.createElement("tr");
    const first = document.createElement("td"), date = document.createElement("small"), title = document.createElement("span");
    date.textContent = new Date(item.created_at.endsWith("Z") || /[+-]\d\d:\d\d$/.test(item.created_at) ? item.created_at : item.created_at + "Z").toLocaleString("pt-BR"); title.textContent = item.title || "Sem título"; first.append(date, title); tr.append(first);
    [item.predicted_category, `${(item.predicted_confidence*100).toFixed(1)}%`, item.final_category, (item.was_corrected ? "Corrigida" : "Aceita") + (item.demo ? " · Demo" : "")].forEach(value => { const td = document.createElement("td"); td.textContent = value; tr.append(td); });
    const actions = document.createElement("td"), group = document.createElement("div"); group.className = "history-actions";
    const edit = document.createElement("a"); edit.className = "button secondary"; edit.href = `/editor?article=${item.id}`; edit.textContent = "Editar";
    edit.setAttribute("aria-label", `Editar notícia: ${item.title || "Sem título"}`);
    const remove = document.createElement("button"); remove.className = "danger-outline"; remove.type = "button"; remove.textContent = "Remover";
    remove.setAttribute("aria-label", `Remover notícia: ${item.title || "Sem título"}`);
    remove.addEventListener("click", () => {
      pendingDelete = item; $("delete-title").textContent = item.title || "Sem título";
      $("delete-error").textContent = ""; $("delete-dialog").showModal(); $("cancel-delete").focus();
    });
    group.append(edit, remove); actions.append(group); tr.append(actions); return tr;
  }));
  $("total").textContent = `${result.total} REGISTROS`; $("empty-history").hidden = result.total !== 0;
  $("previous").disabled = offset === 0; $("next").disabled = offset + 20 >= result.total;
  $("page-info").textContent = result.total ? `${offset+1}–${Math.min(offset+20,result.total)} de ${result.total}` : "0 registros";
}
init();
