// API client for CoTrial RAG backend

const API_BASE_URL = window.location.origin;

class APIClient {
    constructor(baseURL = API_BASE_URL) {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async getStatus() {
        return this.request('/v1/status');
    }

    async chat(query, topK = 5) {
        return this.request('/v1/chat', {
            method: 'POST',
            body: JSON.stringify({ query, top_k: topK }),
        });
    }

    async health() {
        return this.request('/health');
    }
}

// Export singleton instance
const apiClient = new APIClient();
window.apiClient = apiClient;

