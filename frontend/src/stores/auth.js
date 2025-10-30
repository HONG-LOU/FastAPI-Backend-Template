import { defineStore } from 'pinia';
function readTokenPair() {
    try {
        const raw = localStorage.getItem('token_pair');
        if (!raw)
            return null;
        return JSON.parse(raw);
    }
    catch {
        return null;
    }
}
function writeTokenPair(tokens) {
    if (tokens)
        localStorage.setItem('token_pair', JSON.stringify(tokens));
    else
        localStorage.removeItem('token_pair');
}
export const useAuthStore = defineStore('auth', {
    state: () => ({
        tokens: readTokenPair(),
        me: null
    }),
    getters: {
        isAuthenticated: (s) => !!s.tokens?.access_token
    },
    actions: {
        setTokens(tokens) {
            this.tokens = tokens;
            writeTokenPair(tokens);
        },
        logout() {
            this.setTokens(null);
            this.me = null;
        }
    }
});
