async function checkHealth() {
    const statusEl = document.querySelector("#status");
    try {
        const response = await fetch("/api/health");
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        statusEl.textContent = data.status;
    } catch (error) {
    statusEl.textContent = `unreachable (${error.message})`;
  }
}

checkHealth();
