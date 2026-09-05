// ==================== UTILITIES ====================
const $ = id => document.getElementById(id);

let currentCustomer = "";
const sessionId = "agent-demo";

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

async function request(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Request failed:', error);
        throw error;
    }
}

// ==================== CUSTOMER LOADING ====================
async function loadCustomers() {
    try {
        const customers = await request('/api/customers');
        const select = $('customer-select');
        select.innerHTML = customers
            .map(c => `<option value="${c.customer_id}">${escapeHtml(c.full_name)} (${c.customer_id})</option>`)
            .join('');
        currentCustomer = customers[0]?.customer_id || '';
        if (currentCustomer) {
            await loadCustomer();
        }
    } catch (error) {
        console.error('Failed to load customers:', error);
        $('customer-select').innerHTML = '<option>Error loading customers</option>';
    }
}

// ==================== CUSTOMER CONTEXT ====================
function formatContextHtml(data) {
    const customer = data.customer || {};
    const service = data.service || {};
    const billing = data.billing || {};

    return `
        <div class="fact">
            <b>Customer ID:</b> ${escapeHtml(customer.customer_id || 'N/A')}
        </div>
        <div class="fact">
            <b>${escapeHtml(customer.full_name || 'Unknown')}</b>
        </div>
        <div class="fact">
            <b>Service:</b> ${escapeHtml(service.service_type || 'N/A')} 
            <span style="color: #627080;">•</span> 
            ${escapeHtml(service.plan_name || 'N/A')}
        </div>
        <div class="fact">
            <b>Service Status:</b> 
            <span style="font-weight: 600; color: ${service.service_status === 'active' ? '#1b7c3b' : '#c33939'};">
                ${escapeHtml(service.service_status || 'Unknown')}
            </span>
        </div>
        <div class="fact">
            <b>Payment Status:</b> 
            <span style="font-weight: 600; color: ${billing.payment_status === 'paid' ? '#1b7c3b' : '#b8860b'};">
                ${escapeHtml(billing.payment_status || 'Unknown')}
            </span>
        </div>
        <div class="fact">
            <b>Balance:</b> ${escapeHtml(billing.current_balance || 'N/A')}
        </div>
        <div class="fact">
            <b>Recent Charge:</b> ${escapeHtml(billing.recent_charge_summary || 'No summary available')}
        </div>
    `;
}

function formatTicketsHtml(tickets) {
    if (!tickets || tickets.length === 0) {
        return '<p class="placeholder">No recent tickets</p>';
    }

    return tickets
        .map(ticket => `
            <div class="ticket">
                <b>${escapeHtml(ticket.ticket_id || 'Unknown')} • ${escapeHtml(ticket.category || 'General')}</b>
                <div>${escapeHtml(ticket.summary || '')}</div>
                <small>Troubleshooting: ${escapeHtml(ticket.actions_taken || 'None recorded')}</small>
            </div>
        `)
        .join('');
}

async function loadCustomer() {
    if (!currentCustomer) return;

    try {
        const [data, messages] = await Promise.all([
            request(`/api/customers/${currentCustomer}`),
            request(`/api/customers/${currentCustomer}/conversation?session_id=${sessionId}`)
        ]);

        $('account').innerHTML = formatContextHtml(data);
        $('tickets').innerHTML = formatTicketsHtml(data.tickets);
        renderConversation(messages);
        resetRecommendation();
    } catch (error) {
        console.error('Failed to load customer:', error);
        $('account').innerHTML = '<p class="placeholder">Failed to load customer details</p>';
        $('tickets').innerHTML = '<p class="placeholder">Failed to load tickets</p>';
    }
}

// ==================== CONVERSATION ====================
function renderConversation(messages) {
    const conversation = $('conversation');
    
    if (!messages || messages.length === 0) {
        conversation.innerHTML = '<p class="placeholder">No conversation yet</p>';
        return;
    }

    conversation.innerHTML = messages
        .map(msg => `
            <div class="message ${msg.role === 'customer' ? 'customer' : 'assistant'}">
                <b>${msg.role === 'customer' ? 'Customer' : 'Assistant'}</b>
                ${escapeHtml(msg.content)}
            </div>
        `)
        .join('');

    // Auto-scroll to bottom
    setTimeout(() => {
        conversation.scrollTop = conversation.scrollHeight;
    }, 0);
}

// ==================== RESULT FORMATTING ====================
function formatEvidenceHtml(citations) {
    if (!citations || citations.length === 0) {
        return '';
    }

    const items = citations
        .map(citation => `
            <div class="evidence-item">
                <span class="evidence-item-id">${escapeHtml(citation.article_id || 'Unknown')}</span>
                <span class="evidence-item-title">${escapeHtml(citation.title || '')}</span>
                ${citation.section ? `<span class="evidence-item-section">${escapeHtml(citation.section)}</span>` : ''}
                ${citation.excerpt ? `<span class="evidence-item-excerpt">"${escapeHtml(citation.excerpt)}"</span>` : ''}
            </div>
        `)
        .join('');

    return `
        <div class="evidence">
            <h3>✓ Verified Support Evidence</h3>
            ${items}
        </div>
    `;
}

function formatHandoverHtml(handover) {
    if (!handover) {
        return '';
    }

    const established = handover.established || [];
    const tried = handover.tried || [];

    return `
        <div class="handover">
            <h3>→ Human Handover Required</h3>
            <div class="handover-item">
                <span class="handover-item-label">Case Summary:</span>
                <span class="handover-item-content">${escapeHtml(handover.issue_summary)}</span>
            </div>
            <div class="handover-item">
                <span class="handover-item-label">Established Facts:</span>
                <span class="handover-item-content">${established.map(escapeHtml).join(' • ')}</span>
            </div>
            <div class="handover-item">
                <span class="handover-item-label">Troubleshooting Attempted:</span>
                <span class="handover-item-content">
                    ${tried.length > 0 ? tried.map(escapeHtml).join('; ') : 'None recorded'}
                </span>
            </div>
            <div class="handover-item">
                <span class="handover-item-label">Transfer Reason:</span>
                <span class="handover-item-content">${escapeHtml(handover.reason_for_transfer)}</span>
            </div>
        </div>
    `;
}

function formatResultHtml(result) {
    if (!result) {
        return '<p class="placeholder">No analysis available</p>';
    }

    let html = '';

    // Outcome badge
    const outcome = result.outcome || 'unknown';
    const outcomeText = outcome.replace('_', ' ').toUpperCase();
    html += `<span class="badge ${outcome}">${outcomeText}</span>`;

    // Main response or question
    if (result.draft_response) {
        html += `<div class="result-section"><div class="result-text">${escapeHtml(result.draft_response)}</div></div>`;
    }
    if (result.follow_up_question) {
        html += `<div class="result-section"><div class="result-text"><b>Follow-up Question:</b><br>${escapeHtml(result.follow_up_question)}</div></div>`;
    }

    // Status note
    if (result.status_note) {
        html += `<div class="result-section"><div class="status-note">${escapeHtml(result.status_note)}</div></div>`;
    }

    // Evidence
    if (result.citations && result.citations.length > 0) {
        html += formatEvidenceHtml(result.citations);
    }

    // Handover
    if (result.handover) {
        html += formatHandoverHtml(result.handover);
    }

    return html;
}

function resetRecommendation() {
    $('recommendation').innerHTML = `
        <div class="recommendation-placeholder">
            <p>Enter a customer message and click <strong>Analyze Case</strong> to review the case.</p>
        </div>
    `;
}

// ==================== CASE ANALYSIS ====================
async function analyzeCase() {
    const message = $('message').value.trim();
    if (!message) {
        alert('Please enter a customer message.');
        return;
    }

    if (!currentCustomer) {
        alert('Please select a customer.');
        return;
    }

    const button = $('analyze');
    const messageInput = $('message');
    const recommendation = $('recommendation');

    button.disabled = true;
    button.classList.add('loading');
    recommendation.innerHTML = '<div class="placeholder"><p>🔄 Analyzing case...</p></div>';

    try {
        const result = await request('/api/cases/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer_id: currentCustomer,
                session_id: sessionId,
                message
            })
        });

        recommendation.innerHTML = formatResultHtml(result);
        messageInput.value = '';

        // Refresh conversation to show the new assistant response
        const messages = await request(`/api/customers/${currentCustomer}/conversation?session_id=${sessionId}`);
        renderConversation(messages);
    } catch (error) {
        console.error('Analysis failed:', error);
        recommendation.innerHTML = `
            <div class="result-section">
                <span class="badge escalate">Error</span>
                <div class="result-text">
                    Unable to analyze this case safely. Please try again or transfer to a human agent.
                </div>
                <div class="status-note">
                    The system encountered an issue while processing your request. This case should be escalated.
                </div>
            </div>
        `;
    } finally {
        button.disabled = false;
        button.classList.remove('loading');
    }
}

// ==================== HEALTH CHECK ====================
async function updateHealthStatus() {
    try {
        const health = await request('/api/health');
        const statusBadge = $('health');
        if (health.gemini_configured) {
            statusBadge.textContent = '✓ Gemini Available';
            statusBadge.style.color = '#4ade80';
        } else {
            statusBadge.textContent = '⚙ Safe Local Fallback';
            statusBadge.style.color = '#facc15';
        }
    } catch (error) {
        console.error('Health check failed:', error);
        $('health').textContent = '⚠ Service Unavailable';
        $('health').style.color = '#ef4444';
    }
}

// ==================== EVENT LISTENERS ====================
$('customer-select').addEventListener('change', async (e) => {
    currentCustomer = e.target.value;
    await loadCustomer();
});

$('analyze').addEventListener('click', analyzeCase);

$('message').addEventListener('keydown', (e) => {
    // Ctrl+Enter or Cmd+Enter to submit
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        analyzeCase();
    }
});

// ==================== INITIALIZATION ====================
(async () => {
    await updateHealthStatus();
    await loadCustomers();
})();
