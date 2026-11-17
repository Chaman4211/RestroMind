import { existsSync, readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const keyPath = join(homedir(), '.config/restromind/certs/restromind-key.pem')
const certPath = join(homedir(), '.config/restromind/certs/restromind.pem')

const httpsConfig =
  existsSync(keyPath) && existsSync(certPath)
    ? {
        key: readFileSync(keyPath),
        cert: readFileSync(certPath),
      }
    : undefined

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    ...(httpsConfig ? { https: httpsConfig } : {}),
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
