// ---------- Elements ----------
const $ = (id) => document.getElementById(id);
const messagesEl = $("messages");
const emptyState = $("emptyState");
const inputEl = $("input");
const sendBtn = $("sendBtn");
const toneSelect = $("toneSelect");
const exportBtn = $("exportBtn");
const historyList = $("historyList");
const chatTitle = $("chatTitle");
const counter = $("counter");
const sidebar = $("sidebar");
const overlay = $("overlay");

const MAX_LENGTH = 4000;
let currentId = null;
let isStreaming = false;

// ---------- Small helpers ----------
function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Very small markdown renderer: code blocks, inline code, bold, line breaks.
function renderMarkdown(text) {
  return text
    .split("```")
    .map((part, i) => {
      if (i % 2 === 1) {
        const newline = part.indexOf("\n");
        const code = newline >= 0 ? part.slice(newline + 1) : "";
        return `<pre><code>${escapeHtml(code)}</code></pre>`;
      }
      return escapeHtml(part)
        .replace(/`([^`\n]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
    })
    .join("");
}

function formatTime(iso) {
  const date = iso ? new Date(iso) : new Date();
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

let toastTimer;
function showToast(text, isError = false) {
  const toast = $("toast");
  toast.textContent = text;
  toast.className = "toast show" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toast.className = "toast"), 2400);
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function readError(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]) {
      return data.detail[0].msg.replace(/^Value error, /, "");
    }
  } catch (_) {}
  return `Request failed (${response.status}).`;
}

// ---------- Message rendering ----------
function addMessage(role, text, timestamp) {
  emptyState.style.display = "none";

  const row = document.createElement("div");
  row.className = `row ${role}`;
  const stack = document.createElement("div");
  stack.className = "stack";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (role === "user") bubble.textContent = text;
  else if (role === "assistant") bubble.innerHTML = renderMarkdown(text);
  else bubble.textContent = text; // error
  stack.appendChild(bubble);
  row.appendChild(stack);
  messagesEl.appendChild(row);
  scrollToBottom();

  const api = { bubble, stack };
  if (text && role !== "error") api.meta = addMeta(stack, role, text, timestamp);
  return api;
}

function addMeta(stack, role, text, timestamp) {
  const meta = document.createElement("div");
  meta.className = "meta";
  const time = document.createElement("span");
  time.textContent = formatTime(timestamp);
  meta.appendChild(time);

  if (role === "assistant") {
    const copy = document.createElement("button");
    copy.className = "copy-btn";
    copy.textContent = "Copy";
    copy.addEventListener("click", () => copyText(text));
    meta.appendChild(copy);
  }
  stack.appendChild(meta);
  return meta;
}

function showTyping(bubble) {
  bubble.innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';
}

function resetChatView() {
  messagesEl.querySelectorAll(".row").forEach((r) => r.remove());
  emptyState.style.display = "";
}

// ---------- Copy ----------
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast("Response copied");
  } catch (_) {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand("copy");
      showToast("Response copied");
    } catch (err) {
      showToast("Could not copy", true);
    }
    area.remove();
  }
}

// ---------- Sidebar / history ----------
async function loadHistory() {
  try {
    const response = await fetch("/api/conversations");
    if (!response.ok) throw new Error(await readError(response));
    renderHistory(await response.json());
  } catch (err) {
    historyList.innerHTML = '<li class="h-empty">Could not load history.</li>';
  }
}

function renderHistory(items) {
  historyList.innerHTML = "";
  if (!items.length) {
    historyList.innerHTML = '<li class="h-empty">No chats yet.</li>';
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    if (item.id === currentId) li.classList.add("active");

    const title = document.createElement("span");
    title.className = "h-title";
    title.textContent = item.title;

    const del = document.createElement("button");
    del.className = "h-del";
    del.textContent = "\u00d7";
    del.title = "Delete chat";
    del.setAttribute("aria-label", "Delete chat");
    del.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteConversation(item.id);
    });

    li.append(title, del);
    li.addEventListener("click", () => openConversation(item.id));
    historyList.appendChild(li);
  });
}

async function openConversation(id) {
  if (isStreaming) return;
  try {
    const response = await fetch(`/api/conversations/${id}`);
    if (!response.ok) throw new Error(await readError(response));
    const data = await response.json();

    currentId = data.id;
    chatTitle.textContent = data.title;
    toneSelect.value = data.tone;
    exportBtn.disabled = false;
    resetChatView();
    data.messages.forEach((m) => addMessage(m.role, m.content, m.timestamp));
    closeSidebar();
    loadHistory();
  } catch (err) {
    showToast(err.message, true);
  }
}

async function deleteConversation(id) {
  if (isStreaming || !confirm("Delete this chat? This cannot be undone.")) return;
  try {
    const response = await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    if (!response.ok) throw new Error(await readError(response));
    if (id === currentId) newChat();
    loadHistory();
    showToast("Chat deleted");
  } catch (err) {
    showToast(err.message, true);
  }
}

function newChat() {
  if (isStreaming) return;
  currentId = null;
  chatTitle.textContent = "New chat";
  exportBtn.disabled = true;
  resetChatView();
  closeSidebar();
  loadHistory();
  inputEl.focus();
}

function openSidebar() { sidebar.classList.add("open"); overlay.classList.add("show"); }
function closeSidebar() { sidebar.classList.remove("open"); overlay.classList.remove("show"); }

// ---------- Sending + streaming ----------
async function sendMessage() {
  const text = inputEl.value.trim();
  if (isStreaming) return;
  if (!text) return showToast("Please type a message first.", true);
  if (text.length > MAX_LENGTH) return showToast(`Message is too long (max ${MAX_LENGTH} characters).`, true);

  isStreaming = true;
  sendBtn.disabled = true;
  inputEl.value = "";
  autoResize();

  addMessage("user", text);
  const ai = addMessage("assistant", "");
  showTyping(ai.bubble);

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, tone: toneSelect.value, conversation_id: currentId }),
    });
    if (!response.ok) throw new Error(await readError(response));

    currentId = response.headers.get("X-Conversation-Id");
    exportBtn.disabled = false;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      fullText += decoder.decode(value, { stream: true });
      ai.bubble.innerHTML = renderMarkdown(fullText);
      scrollToBottom();
    }
    fullText += decoder.decode();

    if (!fullText.trim()) throw new Error("The AI returned an empty response. Please try again.");
    ai.bubble.innerHTML = renderMarkdown(fullText);
    addMeta(ai.stack, "assistant", fullText);

    // Update title/history after the first message
    if (chatTitle.textContent === "New chat") {
      chatTitle.textContent = text.length > 50 ? text.slice(0, 50) + "..." : text;
    }
    loadHistory();
  } catch (err) {
    ai.bubble.parentElement.parentElement.remove();
    addMessage("error", err.message || "Something went wrong.");
    if (!currentId) inputEl.value = text; // let the user retry a failed first message
  } finally {
    isStreaming = false;
    sendBtn.disabled = false;
    inputEl.focus();
    scrollToBottom();
  }
}

// ---------- Input behaviour ----------
function autoResize() {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 180) + "px";
  counter.textContent = `${inputEl.value.length} / ${MAX_LENGTH}`;
  counter.classList.toggle("warn", inputEl.value.length > MAX_LENGTH - 200);
}

inputEl.addEventListener("input", autoResize);
inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});
sendBtn.addEventListener("click", sendMessage);
$("newChatBtn").addEventListener("click", newChat);
$("menuBtn").addEventListener("click", openSidebar);
overlay.addEventListener("click", closeSidebar);
document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => {
    inputEl.value = chip.textContent;
    autoResize();
    sendMessage();
  })
);

// ---------- Export ----------
exportBtn.addEventListener("click", async () => {
  if (!currentId) return;
  try {
    const response = await fetch(`/api/conversations/${currentId}/export`);
    if (!response.ok) throw new Error(await readError(response));
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = (chatTitle.textContent.replace(/[^\w-]+/g, "_").slice(0, 40) || "chat") + ".txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    showToast("Chat exported");
  } catch (err) {
    showToast(err.message, true);
  }
});

// ---------- Start ----------
loadHistory();
inputEl.focus();
