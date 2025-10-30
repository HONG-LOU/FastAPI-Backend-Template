import { defineStore } from 'pinia'

export type TokenPair = {
  access_token: string
  refresh_token: string
  token_type?: string
}

function readTokenPair(): TokenPair | null {
  try {
    const raw = localStorage.getItem('token_pair')
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function writeTokenPair(tokens: TokenPair | null) {
  if (tokens) localStorage.setItem('token_pair', JSON.stringify(tokens))
  else localStorage.removeItem('token_pair')
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    tokens: readTokenPair() as TokenPair | null,
    me: null as null | { id: number; email: string; email_verified?: boolean }
  }),
  getters: {
    isAuthenticated: (s) => !!s.tokens?.access_token
  },
  actions: {
    setTokens(tokens: TokenPair | null) {
      this.tokens = tokens
      writeTokenPair(tokens)
    },
    logout() {
      this.setTokens(null)
      this.me = null
    }
  }
})


