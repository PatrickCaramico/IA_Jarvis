import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// V7.2: o Branding Book ilustrado (docs/branding-book.html) vai junto com a central, em /branding-book.html,
// para o botão 📘 BRANDING abrir dentro do JARVIS (no PC, no app e no site), sem duplicar o arquivo no projeto.
const BRANDING_BOOK = fileURLToPath(new URL("../docs/branding-book.html", import.meta.url));

function brandingBook() {
  return {
    name: "jarvis-branding-book",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url || !req.url.split("?")[0].endsWith("/branding-book.html")) return next();
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        res.end(readFileSync(BRANDING_BOOK));
      });
    },
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "branding-book.html", source: readFileSync(BRANDING_BOOK) });
    },
  };
}

export default defineConfig({
  plugins: [react(), brandingBook()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        // V7: React num pacote separado: muda pouco entre versões, então o navegador/app reaproveita do cache
        manualChunks(id) {
          if (/node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) return "react";
          return undefined;
        },
      },
    },
  },
});
