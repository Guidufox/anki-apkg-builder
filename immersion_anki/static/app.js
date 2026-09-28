"use strict";

const state = { deck: null, cards: [], selectedId: null, preview: "recognition", importReady: false, poller: null, proposal: null };
const fields = ["japanese", "reading", "meaning", "example", "translation", "context", "tags", "cloze", "cloze_answer"];
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let saveTimer;

async function api(url, options = {}) {
  const config = { ...options, headers: { ...(options.headers || {}) } };
  if (config.body && typeof config.body !== "string") {
    config.headers["Content-Type"] = "application/json";
    config.body = JSON.stringify(config.body);
  }
  const response = await fetch(url, config);
  if (!response.ok) {
    let message = `Error ${response.status}`;
    try { message = (await response.json()).error || message; } catch (_) {}
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function toast(message, error = false) {
  const node = $("#toast");
  node.textContent = message;
  node.className = error ? "show error" : "show";
  clearTimeout(node.timer);
  node.timer = setTimeout(() => node.className = "", 2600);
}

async function loadProject(selectId = null) {
  const project = await api("/api/project");
  state.deck = project.deck;
  state.cards = project.cards;
  $("#deck-name").value = project.deck.name;
  renderTags(project.tags);
  const candidate = selectId ?? state.selectedId ?? state.cards[0]?.id;
  state.selectedId = state.cards.some(card => card.id === candidate) ? candidate : state.cards[0]?.id ?? null;
  renderList();
  loadSelected();
}

function filteredCards() {
  const query = $("#search").value.trim().toLocaleLowerCase();
  const tag = $("#tag-filter").value;
  return state.cards.filter(card => {
    const text = fields.map(field => card[field]).join(" ").toLocaleLowerCase();
    const tags = card.tags.split(/\s+/);
    return (!query || text.includes(query)) && (!tag || tags.includes(tag));
  });
}

function renderTags(tags) {
  const select = $("#tag-filter");
  const selected = select.value;
  select.replaceChildren(new Option("All tags", ""));
  tags.forEach(tag => select.add(new Option(tag, tag)));
  if (tags.includes(selected)) select.value = selected;
}

function renderList() {
  const list = $("#card-list");
  list.replaceChildren();
  const visible = filteredCards();
  visible.forEach(card => {
    const row = document.createElement("div");
    row.className = `card-row${card.id === state.selectedId ? " active" : ""}`;
    row.draggable = true;
    row.dataset.id = card.id;
    const handle = document.createElement("span"); handle.className = "drag-handle"; handle.textContent = "⠿";
    const content = document.createElement("div");
    const primary = document.createElement("span"); primary.className = "card-primary"; primary.lang = "ja"; primary.textContent = card.japanese || "Untitled";
    const secondary = document.createElement("span"); secondary.className = "card-secondary"; secondary.textContent = `${card.reading || "—"} · ${card.meaning || "—"}`;
    content.append(primary, secondary);
    const index = document.createElement("span"); index.className = "card-index"; index.textContent = String(card.position + 1).padStart(2, "0");
    row.append(handle, content, index);
    row.addEventListener("click", () => selectCard(card.id));
    row.addEventListener("dragstart", event => event.dataTransfer.setData("text/plain", String(card.id)));
    row.addEventListener("dragover", event => event.preventDefault());
    row.addEventListener("drop", event => { event.preventDefault(); reorderDrag(Number(event.dataTransfer.getData("text/plain")), card.id); });
    list.append(row);
  });
  $("#card-count").textContent = `${state.cards.length} entries · ${state.cards.length * 2} Anki cards`;
  if (!visible.length) { const empty = document.createElement("p"); empty.className = "muted"; empty.style.padding = "15px"; empty.textContent = "No cards found."; list.append(empty); }
}

function selectCard(id) { state.selectedId = id; renderList(); loadSelected(); }
function selectedCard() { return state.cards.find(card => card.id === state.selectedId); }

function loadSelected() {
  const card = selectedCard();
  $("#card-form").classList.toggle("hidden", !card);
  $("#editor-title").textContent = card ? (card.japanese || "New card") : "No card selected";
  $$("#duplicate-card, #delete-card, #move-up, #move-down, #research-start").forEach(button => button.disabled = !card);
  if (card) fields.forEach(field => $(`#card-form [name="${field}"]`).value = card[field] || "");
  renderPreview();
  $("#proposal").classList.add("hidden");
  if (card) loadLatestProposal(card.id);
}

function formData() { return Object.fromEntries(fields.map(field => [field, $(`#card-form [name="${field}"]`).value])); }
function markSaving() { $("#save-status").textContent = "Saving…"; }
function scheduleSave() {
  if (!state.selectedId) return;
  markSaving(); renderPreview();
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveCard, 500);
}

async function saveCard() {
  const id = state.selectedId;
  if (!id) return;
  try {
    const card = await api(`/api/cards/${id}`, { method: "PUT", body: formData() });
    const index = state.cards.findIndex(item => item.id === id);
    if (index >= 0) state.cards[index] = card;
    $("#save-status").textContent = "Saved";
    $("#editor-title").textContent = card.japanese || "New card";
    renderList();
  } catch (error) { $("#save-status").textContent = "Error"; toast(error.message, true); }
}

function line(className, text) { const node = document.createElement("div"); node.className = className; node.textContent = text || "—"; return node; }
function renderPreview() {
  const data = state.selectedId ? formData() : Object.fromEntries(fields.map(field => [field, ""]));
  const front = $("#preview-front"), back = $("#preview-back"); front.replaceChildren(); back.replaceChildren();
  if (state.preview === "recognition") {
    front.append(line("jp", data.example), line("", ""), line("jp", `${data.japanese || "—"}【${data.reading || "—"}】`));
    back.append(line("jp", data.japanese), line("reading", data.reading), line("meaning", data.meaning), line("divider", ""), line("jp", data.example), line("translation", data.translation));
  } else {
    front.append(line("meaning", data.meaning), line("jp", data.cloze || "Completa manualmente Cloze sentence"));
    back.append(line("answer jp", data.cloze_answer || "—"), line("jp", `${data.japanese || "—"}【${data.reading || "—"}】`), line("divider", ""), line("jp", data.example));
  }
}

async function addCard() { const card = await api("/api/cards", { method: "POST", body: {} }); await loadProject(card.id); setTimeout(() => $("[name=japanese]").focus(), 0); }
async function deleteCard() { const card = selectedCard(); if (!card || !confirm(`Delete “${card.japanese || "this card"}”?`)) return; await api(`/api/cards/${card.id}`, { method: "DELETE" }); state.selectedId = null; await loadProject(); toast("Card deleted"); }
async function duplicateCard() { const card = await api(`/api/cards/${state.selectedId}/duplicate`, { method: "POST" }); await loadProject(card.id); toast("Card duplicated"); }

async function reorder(ids) { await api("/api/cards/reorder", { method: "PUT", body: { ids } }); await loadProject(state.selectedId); }
function reorderDrag(sourceId, targetId) { if (sourceId === targetId) return; const ids = state.cards.map(card => card.id); const source = ids.indexOf(sourceId), target = ids.indexOf(targetId); ids.splice(target, 0, ids.splice(source, 1)[0]); reorder(ids).catch(error => toast(error.message, true)); }
function moveSelected(delta) { const ids = state.cards.map(card => card.id), index = ids.indexOf(state.selectedId), target = index + delta; if (index < 0 || target < 0 || target >= ids.length) return; [ids[index], ids[target]] = [ids[target], ids[index]]; reorder(ids).catch(error => toast(error.message, true)); }

async function downloadResponse(url, options, fallback) {
  const response = await fetch(url, options);
  if (!response.ok) { let message = `Error ${response.status}`; try { message = (await response.json()).error || message; } catch (_) {} throw new Error(message); }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename\*?=(?:UTF-8'')?[\"']?([^\"';]+)/i);
  const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = match ? decodeURIComponent(match[1]) : fallback; link.click(); URL.revokeObjectURL(link.href);
}

async function previewImport() {
  try {
    const data = await api("/api/import/preview", { method: "POST", body: { text: $("#import-text").value, format: $("#import-format").value } });
    const tbody = $("#import-preview-body"); tbody.replaceChildren();
    data.rows.forEach(row => { const tr = document.createElement("tr"); ["japanese", "reading", "meaning", "example", "translation", "context", "tags"].forEach(key => { const td = document.createElement("td"); td.textContent = row[key]; tr.append(td); }); tbody.append(tr); });
    state.importReady = data.rows.length > 0; $("#import-commit").disabled = !state.importReady; $("#import-message").textContent = `${data.rows.length} rows ready`;
  } catch (error) { state.importReady = false; $("#import-commit").disabled = true; $("#import-message").textContent = error.message; }
}

async function commitImport() { try { const result = await api("/api/import/commit", { method: "POST", body: { text: $("#import-text").value, format: $("#import-format").value } }); $("#import-dialog").close(); await loadProject(result.cards[0]?.id); toast(`${result.cards.length} cards imported`); } catch (error) { toast(error.message, true); } }

async function loadSettings() {
  const s = await api("/api/settings");
  $("#ai-enabled").checked = s.ai_enabled; $("#ai-format").value = s.ai_api_format; $("#ai-url").value = s.ai_base_url; $("#ai-model").value = s.ai_model;
  $("#ai-context").value = s.ai_context_length; $("#ai-timeout").value = s.ai_timeout; $("#network-enabled").checked = s.network_enabled; $("#web-enabled").checked = s.web_access;
  $("#browser-enabled").checked = s.browser_enabled; $("#browser-headless").checked = s.browser_headless; $("#browser-profile").value = s.browser_profile;
  updatePrivacy(); loadLogs();
}
function settingsData() { return { ai_enabled: $("#ai-enabled").checked, ai_api_format: $("#ai-format").value, ai_base_url: $("#ai-url").value, ai_model: $("#ai-model").value, ai_context_length: Number($("#ai-context").value), ai_timeout: Number($("#ai-timeout").value), network_enabled: $("#network-enabled").checked, web_access: $("#web-enabled").checked, browser_enabled: $("#browser-enabled").checked, browser_headless: $("#browser-headless").checked, browser_profile: $("#browser-profile").value }; }
function updatePrivacy() { $("#privacy-web").textContent = $("#web-enabled").checked ? "ON" : "OFF"; $("#privacy-browser").textContent = $("#browser-enabled").checked ? "ON" : "OFF"; $("#privacy-network").textContent = $("#network-enabled").checked ? "ON" : "OFF"; }
async function saveSettings() { try { await api("/api/settings", { method: "PUT", body: settingsData() }); $("#settings-message").textContent = "Settings saved locally."; updatePrivacy(); } catch (error) { $("#settings-message").textContent = error.message; } }
async function loadLogs() { const logs = await api("/api/agent/logs"); const node = $("#agent-logs"); node.replaceChildren(); logs.forEach(log => { const entry = document.createElement("div"); entry.className = "log-entry"; entry.textContent = `${log.timestamp} · ${log.action} · ${log.url || "local"} · ${log.result}`; node.append(entry); }); if (!logs.length) node.textContent = "No agent activity yet."; }

async function startResearch() { try { const result = await api(`/api/cards/${state.selectedId}/research`, { method: "POST", body: { task: $("#research-task").value } }); updateAgent(result); startPolling(); } catch (error) { toast(error.message, true); } }
function startPolling() { clearInterval(state.poller); state.poller = setInterval(pollAgent, 1000); pollAgent(); }
async function pollAgent() { try { const data = await api("/api/agent/status"); updateAgent(data); if (["completed", "failed", "idle"].includes(data.status)) { clearInterval(state.poller); if (data.research?.status === "proposal") showProposal(data.research); } } catch (_) {} }
function updateAgent(data) {
  $("#agent-monitor").classList.remove("hidden"); $("#agent-dot").classList.toggle("off", ["idle", "failed", "completed", "stopped"].includes(data.status));
  $("#agent-status").textContent = data.status || "—"; $("#agent-url").textContent = data.current_url || "—"; $("#agent-task").textContent = data.current_task || "—"; $("#agent-last").textContent = data.last_action || "—"; $("#agent-next").textContent = data.next_proposed_action || data.error || "—";
  $("#agent-confirm").classList.toggle("hidden", !data.confirmation_required); $("#confirm-reason").textContent = data.confirmation_reason || "";
}
async function agentCommand(command, body) { try { updateAgent(await api(`/api/agent/${command}`, { method: "POST", body: body || {} })); } catch (error) { toast(error.message, true); } }
async function loadLatestProposal(cardId) { try { const proposal = await api(`/api/cards/${cardId}/research`); if (proposal.status === "proposal") showProposal(proposal); } catch (_) {} }
function showProposal(proposal) { state.proposal = proposal; $("#proposal").classList.remove("hidden"); $("#proposal-summary").value = proposal.summary; $("#proposal-meaning").value = proposal.suggested_meaning; $("#proposal-example").value = proposal.suggested_example; $("#proposal-notes").value = proposal.notes; const sources = $("#proposal-sources"); sources.replaceChildren(); proposal.sources.forEach(source => { const div = document.createElement("div"); div.className = "source"; const a = document.createElement("a"); a.href = source.url; a.target = "_blank"; a.rel = "noopener noreferrer"; a.textContent = source.page_title || source.url; const info = document.createElement("div"); info.textContent = `${source.accessed_at} · ${source.fragment.slice(0, 180)}`; div.append(a, info); sources.append(div); }); }
async function decideProposal(decision) { if (!state.proposal) return; if (decision === "accepted") { $("[name=meaning]").value = $("#proposal-meaning").value; $("[name=example]").value = $("#proposal-example").value; const notes = $("#proposal-notes").value; if (notes) $("[name=context]").value = [$("[name=context]").value, notes].filter(Boolean).join("\n\n"); scheduleSave(); } await api(`/api/research/${state.proposal.id}/decision`, { method: "POST", body: { decision } }); $("#proposal").classList.add("hidden"); toast(decision === "accepted" ? "Proposal copied to the editor" : "Proposal rejected"); }

document.addEventListener("DOMContentLoaded", async () => {
  try { await loadProject(); } catch (error) { toast(error.message, true); }
  $("#card-form").addEventListener("input", scheduleSave);
  $("#deck-name").addEventListener("input", () => { markSaving(); clearTimeout(saveTimer); saveTimer = setTimeout(async () => { try { state.deck = await api("/api/deck", { method: "PUT", body: { name: $("#deck-name").value } }); $("#save-status").textContent = "Saved"; } catch (error) { toast(error.message, true); } }, 500); });
  $("#search").addEventListener("input", renderList); $("#tag-filter").addEventListener("change", renderList);
  $("#add-card").addEventListener("click", () => addCard().catch(error => toast(error.message, true))); $("#delete-card").addEventListener("click", deleteCard); $("#duplicate-card").addEventListener("click", duplicateCard); $("#move-up").addEventListener("click", () => moveSelected(-1)); $("#move-down").addEventListener("click", () => moveSelected(1));
  $$("[data-preview]").forEach(button => button.addEventListener("click", () => { state.preview = button.dataset.preview; $$("[data-preview]").forEach(item => item.classList.toggle("active", item === button)); renderPreview(); }));
  $("#export-apkg").addEventListener("click", async () => { try { await saveCard(); await downloadResponse("/api/export", { method: "POST" }, "deck.apkg"); toast("APKG generated in exports/ and downloaded"); } catch (error) { toast(error.message, true); } });
  $("#backup-export").addEventListener("click", () => downloadResponse("/api/backup", {}, "anki-project.json").catch(error => toast(error.message, true)));
  $("#backup-file").addEventListener("change", async event => { const file = event.target.files[0]; if (!file || !confirm("Restore this backup? Current cards will be replaced.")) return; try { await api("/api/backup", { method: "POST", body: JSON.parse(await file.text()) }); state.selectedId = null; await loadProject(); toast("Backup restored"); } catch (error) { toast(error.message, true); } event.target.value = ""; });
  $("#import-open").addEventListener("click", () => $("#import-dialog").showModal()); $("#import-preview").addEventListener("click", previewImport); $("#import-commit").addEventListener("click", commitImport); $("#import-file").addEventListener("change", async event => { const file = event.target.files[0]; if (file) { $("#import-text").value = await file.text(); $("#import-format").value = file.name.toLowerCase().endsWith(".tsv") ? "tsv" : "csv"; } });
  $("#settings-open").addEventListener("click", async () => { await loadSettings(); $("#settings-dialog").showModal(); }); $$(".close-dialog").forEach(button => button.addEventListener("click", event => event.currentTarget.closest("dialog").close()));
  $$("#network-enabled, #web-enabled, #browser-enabled").forEach(input => input.addEventListener("change", updatePrivacy)); $("#save-settings").addEventListener("click", saveSettings);
  $("#disable-network").addEventListener("click", async () => { if (!confirm("Disable all network and browser access now?")) return; await api("/api/settings/disable-network", { method: "POST" }); await loadSettings(); toast("All network access disabled"); });
  $("#test-ai").addEventListener("click", async () => { await saveSettings(); try { const result = await api("/api/settings/test-ai", { method: "POST" }); $("#settings-message").textContent = result.available ? "Local AI endpoint is reachable." : `Local AI unavailable: ${result.error}`; } catch (error) { $("#settings-message").textContent = error.message; } });
  $("#research-start").addEventListener("click", startResearch); $("#agent-pause").addEventListener("click", () => agentCommand("pause")); $("#agent-resume").addEventListener("click", () => agentCommand("resume")); $("#agent-stop").addEventListener("click", () => agentCommand("stop")); $("#confirm-yes").addEventListener("click", () => agentCommand("confirm", { allowed: true })); $("#confirm-no").addEventListener("click", () => agentCommand("confirm", { allowed: false }));
  $("#proposal-accept").addEventListener("click", () => decideProposal("accepted")); $("#proposal-reject").addEventListener("click", () => decideProposal("rejected"));
});
