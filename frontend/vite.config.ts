import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // L'appel au LLM passe par le backend : la clé ne quitte jamais le serveur.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
