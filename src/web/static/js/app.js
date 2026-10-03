"use strict";
const $ = id => document.getElementById(id);
let prediction = null, categories = [], thresholds = {}, offset = 0, revision = 0, busy = false;
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
async function init() {
  try {
    const [health, config] = await Promise.all([api("/health"), api("/api/categories")]);
    categories = config.categories; thresholds = config.thresholds;
    $("model-status").textContent = !health.model_loaded ? "Modelo indisponível. Configure um modelo treinado para analisar notícias." : health.demo ? "Modo demonstração · Modelo treinado com dados sintéticos. Os resultados não representam qualidade em notícias reais." : `Modelo disponível · Versão ${health.model_version}`;
    $("model-status").classList.toggle("ready", health.model_loaded && !health.demo);
    if (document.body.dataset.page === "editor") {
      $("analyze").disabled = !health.model_loaded;
      $("final-category").replaceChildren(...categories.map(c => option(c, c)));
    } else {
      $("filter-category").append(...categories.map(c => option(c, c)));
      await loadHistory();
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
      prediction = result;
      $("suggested-category").textContent = result.predicted_category;
      $("confidence").textContent = `${(100 * result.confidence).toFixed(1)}%`;
      $("confidence-bar").style.width = `${result.confidence * 100}%`;
      $("confidence-label").textContent = result.confidence >= thresholds.high ? "Alta confiança" : result.confidence >= thresholds.medium ? "Revisão recomendada" : "Classificação incerta";
      $("candidates").replaceChildren(...result.top_k.map(c => { const li = document.createElement("li"), label = document.createElement("span"), value = document.createElement("strong"); label.textContent = c.category; value.textContent = `${(100*c.confidence).toFixed(1)}%`; li.append(label, value); return li; }));
      $("final-category").value = result.predicted_category;
      $("empty-analysis").hidden = true; $("analysis-result").hidden = false;
    } catch (error) { message(error.message, true); }
    finally { busy = false; $("analyze").disabled = false; $("analyze").textContent = "Analisar notícia ↗"; }
  });
  $("save").addEventListener("click", async () => {
    if (!prediction || !$("confirmed").checked || busy) return;
    busy = true; $("save").disabled = true;
    try {
      await api("/api/articles", {method:"POST", body:JSON.stringify({prediction_id:prediction.prediction_id, final_category:$("final-category").value, confirmed:true})});
      invalidate(); message("Decisão salva. Consulte o histórico editorial.");
    } catch (error) { message(error.message, true); $("save").disabled = false; }
    finally { busy = false; }
  });
} else {
  ["filter-category", "filter-correction"].forEach(id => $(id).addEventListener("change", () => { offset = 0; loadHistory().catch(e => message(e.message, true)); }));
  $("previous").addEventListener("click", () => { offset = Math.max(0, offset - 20); loadHistory().catch(e => message(e.message, true)); });
  $("next").addEventListener("click", () => { offset += 20; loadHistory().catch(e => message(e.message, true)); });
}
let historyRequest = 0;
async function loadHistory() {
  const request = ++historyRequest;
  const params = new URLSearchParams({offset, limit:20});
  if ($("filter-category").value) params.set("category", $("filter-category").value);
  if ($("filter-correction").value) params.set("was_corrected", $("filter-correction").value);
  const result = await api(`/api/articles?${params}`);
  if (request !== historyRequest) return;
  $("history-body").replaceChildren(...result.items.map(item => {
    const tr = document.createElement("tr");
    const first = document.createElement("td"), date = document.createElement("small"), title = document.createElement("span");
    date.textContent = new Date(item.created_at.endsWith("Z") || /[+-]\d\d:\d\d$/.test(item.created_at) ? item.created_at : item.created_at + "Z").toLocaleString("pt-BR"); title.textContent = item.title || "Sem título"; first.append(date, title); tr.append(first);
    [item.predicted_category, `${(item.predicted_confidence*100).toFixed(1)}%`, item.final_category, (item.was_corrected ? "Corrigida" : "Aceita") + (item.demo ? " · Demo" : "")].forEach(value => { const td = document.createElement("td"); td.textContent = value; tr.append(td); }); return tr;
  }));
  $("total").textContent = `${result.total} REGISTROS`; $("empty-history").hidden = result.total !== 0;
  $("previous").disabled = offset === 0; $("next").disabled = offset + 20 >= result.total;
  $("page-info").textContent = result.total ? `${offset+1}–${Math.min(offset+20,result.total)} de ${result.total}` : "0 registros";
}
init();
