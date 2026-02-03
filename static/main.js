const API_URL = ""; // Empty string means same origin (useful for simple deployment)

async function ingestData() {
    const text = document.getElementById('corpusInput').value;
    const statusEl = document.getElementById('ingestStatus');
    const btn = document.getElementById('ingestBtn');

    if (!text) return alert("Please enter some text first.");

    btn.disabled = true;
    statusEl.textContent = "Chunking & Embedding...";
    statusEl.style.color = "#64748b";

    try {
        // CHANGED: Sending JSON body instead of URL params
        const response = await fetch(`${API_URL}/ingest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        
        const data = await response.json();
        statusEl.textContent = `Success! Indexed ${data.chunks} chunks.`;
        statusEl.style.color = "green";
    } catch (err) {
        statusEl.textContent = "Error: " + err.message;
        statusEl.style.color = "red";
    } finally {
        btn.disabled = false;
    }
}

async function askQuestion() {
    const question = document.getElementById('queryInput').value;
    const resArea = document.getElementById('resultsArea');
    const btn = document.getElementById('askBtn');
    
    if (!question) return alert("Please ask a question.");

    btn.disabled = true;
    btn.textContent = "Thinking...";
    resArea.style.display = 'none';

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });

        const data = await response.json();

        // Render Answer
        // Simple regex to bold citations like [1]
        let formattedAnswer = data.answer.replace(/\[(\d+)\]/g, '<b>[$1]</b>');
        document.getElementById('answerText').innerHTML = formattedAnswer;

        // Render Citations
        const citationsDiv = document.getElementById('citationsList');
        citationsDiv.innerHTML = '';
        data.citations.forEach(cit => {
            const div = document.createElement('div');
            div.className = 'citation-box';
            div.innerHTML = `<strong>[${cit.id}]</strong> ${cit.text.substring(0, 150)}...`;
            citationsDiv.appendChild(div);
        });

        // Render Stats
        document.getElementById('latency').textContent = `⏱️ Time: ${data.time_taken}s`;
        // Rough estimate: Input + Output tokens logic (simplified)
        document.getElementById('costEst').textContent = `💰 Est. Cost: < $0.0002`; 

        resArea.style.display = 'block';

    } catch (err) {
        alert("Failed to get answer: " + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Ask Question";
    }
}