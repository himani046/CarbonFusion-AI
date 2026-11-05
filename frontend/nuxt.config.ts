export default defineNuxtConfig({
  compatibilityDate: '2026-09-01',
  devtools: { enabled: false },
  css: ['~/assets/css/main.css', 'maplibre-gl/dist/maplibre-gl.css'],
  runtimeConfig: { public: { apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000' } },
  app: { head: { title: 'CarbonFusion AI | Forest Intelligence', meta: [
    { name: 'description', content: 'Research dashboard for forest aboveground biomass and calibrated uncertainty.' },
    { name: 'theme-color', content: '#071419' }
  ] } }
})
