// Chat interface functionality

class ChatManager {
    constructor() {
        this.messages = [];
        this.loadMessages();
        this.setupEventListeners();
    }

    loadMessages() {
        const saved = localStorage.getItem('cotrial_messages');
        if (saved) {
            try {
                this.messages = JSON.parse(saved);
            } catch {
                this.messages = [];
            }
        }
    }

    saveMessages() {
        localStorage.setItem('cotrial_messages', JSON.stringify(this.messages));
    }

    setupEventListeners() {
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');
        const form = document.getElementById('chat-form');

        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }

        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                this.sendMessage();
            });
        }
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');
        
        if (!input || !input.value.trim()) return;

        const query = input.value.trim();
        input.value = '';
        input.disabled = true;
        if (sendBtn) sendBtn.disabled = true;

        // Add user message
        this.addMessage('user', query);

        // Show loading indicator
        const loadingId = this.addMessage('assistant', '', true);

        try {
            const response = await window.apiClient.chat(query);
            
            // Remove loading message
            this.removeMessage(loadingId);
            
            // Add assistant response
            this.addMessage('assistant', response.answer, false, response.citations || []);
        } catch (error) {
            // Remove loading message
            this.removeMessage(loadingId);
            
            // Show error
            this.addMessage('assistant', `⚠️ **Error**: ${error.message}\n\nThe service may be initializing. Please wait a moment and try again.`);
        } finally {
            input.disabled = false;
            if (sendBtn) sendBtn.disabled = false;
            input.focus();
        }
    }

    addMessage(role, content, isLoading = false, citations = []) {
        const messageId = Date.now();
        const message = {
            id: messageId,
            role,
            content,
            citations,
            isLoading,
        };

        this.messages.push(message);
        this.saveMessages();
        this.renderMessage(message);
        
        // Auto-scroll disabled - user controls scrolling manually

        return messageId;
    }

    removeMessage(messageId) {
        const element = document.getElementById(`message-${messageId}`);
        if (element) {
            element.remove();
        }
        this.messages = this.messages.filter(m => m.id !== messageId);
        this.saveMessages();
    }

    renderMessage(message) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const messageDiv = document.createElement('div');
        messageDiv.id = `message-${message.id}`;
        messageDiv.className = `chat-message ${message.role}`;

        if (message.isLoading) {
            messageDiv.innerHTML = `
                <div class="chat-message-content">
                    <div class="spinner"></div> Researching...
                </div>
            `;
        } else {
            const content = this.formatMessage(message.content);
            let citationsHtml = '';
            
            if (message.citations && message.citations.length > 0) {
                citationsHtml = this.renderCitations(message.citations);
            }

            messageDiv.innerHTML = `
                <div class="chat-message-content">
                    ${content}
                    ${citationsHtml}
                </div>
            `;

            // Setup citation toggles
            this.setupCitationToggles(messageDiv);
        }

        container.appendChild(messageDiv);
    }

    formatMessage(content) {
        // Simple markdown-like formatting
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        
        return `<p>${formatted}</p>`;
    }

    renderCitations(citations) {
        if (!citations || citations.length === 0) return '';

        let html = `
            <div class="citations-section">
                <h4 class="citations-title">Referenced Sources</h4>
        `;

        citations.forEach((citation, idx) => {
            const corpus = (citation.corpus || 'unknown').toUpperCase();
            const score = citation.score || 0;
            const snippet = citation.snippet || 'No snippet available';
            const chunkId = citation.chunk_id || 'N/A';
            const citationId = `citation-${Date.now()}-${idx}`;

            html += `
                <div class="citation-item">
                    <button class="citation-header" data-citation-id="${citationId}">
                        <span>Source ${idx + 1}: ${corpus} (Relevance: ${score.toFixed(3)})</span>
                        <span class="citation-arrow" id="${citationId}-arrow">▼</span>
                    </button>
                    <div class="citation-content" id="${citationId}-content">
                        <div class="citation-snippet">
                            <p>${this.escapeHtml(snippet)}</p>
                            <p class="citation-meta"><strong>Document ID:</strong> ${this.escapeHtml(chunkId)}</p>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        return html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    setupCitationToggles(container) {
        const headers = container.querySelectorAll('.citation-header');
        headers.forEach(header => {
            const citationId = header.getAttribute('data-citation-id');
            if (citationId) {
                header.addEventListener('click', (e) => {
                    e.preventDefault();
                    toggleCitation(citationId);
                });
            }
        });
    }

    renderAllMessages() {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        container.innerHTML = '';
        this.messages.forEach(msg => {
            if (!msg.isLoading) {
                this.renderMessage(msg);
            }
        });
    }

    clearMessages() {
        this.messages = [];
        this.saveMessages();
        const container = document.getElementById('chat-messages');
        if (container) {
            container.innerHTML = '';
        }
    }
}

// Global citation toggle function
function toggleCitation(id) {
    const content = document.getElementById(`${id}-content`);
    const arrow = document.getElementById(`${id}-arrow`);
    
    if (content && arrow) {
        if (content.classList.contains('active')) {
            content.classList.remove('active');
            arrow.textContent = '▼';
            arrow.classList.remove('active');
        } else {
            content.classList.add('active');
            arrow.textContent = '▲';
            arrow.classList.add('active');
        }
    }
}

// Export
window.ChatManager = ChatManager;
window.toggleCitation = toggleCitation;

