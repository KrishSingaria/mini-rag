const API_URL = "";

// ============ UTILITIES ============
function updateStatus(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = message;
}

function getElement(id) {
    return document.getElementById(id);
}

async function apiCall(endpoint, body = null) {
    const options = {
        method: body ? 'POST' : 'POST',
        headers: { 'Content-Type': 'application/json' }
    };
    if (body) options.body = JSON.stringify(body);
    
    return fetch(`${API_URL}${endpoint}`, options);
}

// ============ INITIALIZATION ============
window.onload = async function() {
    console.log("Resetting DB...");
    updateStatus('resetStatus', "Resetting DB...");
    
    try {
        await apiCall('/reset');
        updateStatus('resetStatus', "Memory Wiped & Ready");
    } catch (e) {
        updateStatus('resetStatus', "Reset Failed");
    }
};

// ============ DATA INGESTION ============
async function ingestData() {
    const text = getElement('corpusInput').value;
    
    if (!text) return alert("Paste text first!");

    const btn = getElement('ingestBtn');
    btn.disabled = true;
    updateStatus('ingestStatus', "Chunking & Embedding...");

    try {
        const response = await apiCall('/ingest', { text });
        const data = await response.json();
        
        handleIngestSuccess(data);
        updateStatus('ingestStatus', `Success! Indexed ${data.chunks} chunks.`);
        
    } catch (err) {
        updateStatus('ingestStatus', `Error: ${err.message}`);
    } finally {
        btn.disabled = false;
    }
}

function handleIngestSuccess(data) {
    const kbDisplay = getElement('kbDisplay');
    const text = getElement('corpusInput').value;
    
    if (kbDisplay.textContent.includes("(Memory is empty")) {
        kbDisplay.textContent = "";
    }
    
    const separator = kbDisplay.textContent.length > 0 ? "\n\n--------------------------------\n\n" : "";
    const time = new Date().toLocaleTimeString();
    kbDisplay.textContent += `${separator}[Update @ ${time}]\n${text}`;
    kbDisplay.scrollTop = kbDisplay.scrollHeight;
    getElement('corpusInput').value = "";
}

// ============ CHAT LOGIC ============
function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

async function sendMessage() {
    const input = getElement('queryInput');
    const question = input.value.trim();
    
    if (!question) return;

    const history = getElement('chat-history');
    const btn = getElement('sendBtn');

    addMessageToHistory(history, question, 'user');
    input.value = "";
    btn.disabled = true;

    const loadingId = `loading-${Date.now()}`;
    addMessageToHistory(history, "Thinking...", 'bot', loadingId);

    try {
        const response = await apiCall('/chat', { question });
        const data = await response.json();
        const loadingBubble = getElement(loadingId);

        if (!response.ok || !data.answer) {
            loadingBubble.innerHTML = `<span style="color: red;">⚠️ Error: ${data.detail || "Server issue"}</span>`;
            return;
        }

        const htmlContent = formatResponse(data);
        loadingBubble.innerHTML = htmlContent;

    } catch (err) {
        getElement(loadingId).innerHTML = `<span style="color: red;">Connection Error: ${err.message}</span>`;
    } finally {
        btn.disabled = false;
        history.scrollTop = history.scrollHeight;
    }
}

function addMessageToHistory(history, text, role, id = null) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    if (id) div.id = id;
    div.textContent = text;
    history.appendChild(div);
    history.scrollTop = history.scrollHeight;
}

function formatResponse(data) {
    let html = typeof marked !== 'undefined' ? marked.parse(data.answer) : data.answer;
    
    if (data.citations?.length > 0) {
        html += '<div class="citation-block"><strong>Sources:</strong><br>';
        data.citations.forEach(cit => {
            html += `<span class="citation-item">[${cit.id}] ${cit.text.substring(0, 100)}...</span>`;
        });
        html += '</div>';
    }
    
    return html;
}