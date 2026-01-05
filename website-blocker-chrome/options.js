const websiteInput = document.getElementById('websiteInput');
const addBtn = document.getElementById('addBtn');
const blockedList = document.getElementById('blockedList');

// Base ID for rules (declarativeNetRequest requires integer IDs)
// We'll use Date.now() + index or similar, but simplified for MVP.
// However, rule IDs must be static for removal. We store them.

async function loadRules() {
    const data = await chrome.storage.local.get('rules');
    const rules = data.rules || [];
    renderList(rules);
}

function renderList(rules) {
    blockedList.innerHTML = '';
    rules.forEach(rule => {
        const li = document.createElement('li');
        // Display domain if available, otherwise fallback to regex (for checking old rules or debug)
        li.textContent = rule.domain || rule.regex;

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Remove';
        deleteBtn.className = 'delete-btn';
        deleteBtn.onclick = () => removeRule(rule.id);

        li.appendChild(deleteBtn);
        blockedList.appendChild(li);
    });
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function addRule() {
    const domain = websiteInput.value.trim();
    if (!domain) return;

    // Basic domain validation (optional, can be improved)
    if (domain.includes(' ') || !domain.includes('.')) {
        alert('Please enter a valid domain (e.g., example.com)');
        return;
    }

    const id = Math.floor(Math.random() * 1000000) + 1; // Simple random ID

    // Construct regex to match the domain and www. subdomain
    // Escape the domain input to treat dots as literals
    const escapedDomain = escapeRegex(domain);
    // Pattern: ^https?://(www\.)?domain(/.*)?$
    // Matches http/https, optional www., then domain, then optional path/query
    const regex = `^https?:\\/\\/(www\\.)?${escapedDomain}(\\/.*)?$`;

    const newRule = { id, domain, regex };

    const data = await chrome.storage.local.get('rules');
    const rules = data.rules || [];

    // Avoid duplicates
    if (rules.some(r => r.domain === domain)) {
        alert('This domain is already blocked.');
        return;
    }

    rules.push(newRule);

    await chrome.storage.local.set({ rules });
    await updateBlockingRules(newRule, 'add');

    websiteInput.value = '';
    renderList(rules);
}

async function removeRule(id) {
    const data = await chrome.storage.local.get('rules');
    let rules = data.rules || [];
    const ruleToRemove = rules.find(r => r.id === id);

    if (!ruleToRemove) return;

    rules = rules.filter(r => r.id !== id);

    await chrome.storage.local.set({ rules });
    await updateBlockingRules(ruleToRemove, 'remove');

    renderList(rules);
}

async function updateBlockingRules(rule, action) {
    if (action === 'add') {
        const dnrRule = {
            id: rule.id,
            priority: 1,
            action: {
                type: 'redirect',
                redirect: { url: 'http://127.0.0.1' }
            },
            condition: {
                regexFilter: rule.regex,
                resourceTypes: ['main_frame']
            }
        };
        await chrome.declarativeNetRequest.updateDynamicRules({
            addRules: [dnrRule],
            removeRuleIds: []
        });
    } else if (action === 'remove') {
        await chrome.declarativeNetRequest.updateDynamicRules({
            addRules: [],
            removeRuleIds: [rule.id]
        });
    }
}

addBtn.addEventListener('click', addRule);
websiteInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addRule();
});

// Initial load
loadRules();
