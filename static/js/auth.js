// Authentication and session management

class AuthManager {
    constructor() {
        this.storageKey = 'cotrial_auth';
        this.trialKey = 'cotrial_trial';
    }

    isAuthenticated() {
        const auth = this.getAuth();
        return auth && auth.authenticated === true;
    }

    login(username, password) {
        // Stubbed login - accept any credentials
        if (username && password) {
            const auth = {
                authenticated: true,
                username: username,
                timestamp: Date.now(),
            };
            localStorage.setItem(this.storageKey, JSON.stringify(auth));
            return true;
        }
        return false;
    }

    logout() {
        localStorage.removeItem(this.storageKey);
        localStorage.removeItem(this.trialKey);
    }

    getAuth() {
        const authStr = localStorage.getItem(this.storageKey);
        if (!authStr) return null;
        
        try {
            return JSON.parse(authStr);
        } catch {
            return null;
        }
    }

    getUsername() {
        const auth = this.getAuth();
        return auth ? auth.username : null;
    }

    setSelectedTrial(trialId) {
        localStorage.setItem(this.trialKey, trialId);
    }

    getSelectedTrial() {
        return localStorage.getItem(this.trialKey);
    }

    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/';
            return false;
        }
        return true;
    }
}

// Export singleton instance
const authManager = new AuthManager();
window.authManager = authManager;

