import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.resolve(__dirname, "public");

function serveGuides() {
  return {
    name: "serve-guides",
    configureServer(server) {
      // Must run before Vite's SPA history fallback
      server.middlewares.use((req, res, next) => {
        const url = (req.url || "").split("?")[0]; // strip query strings
        if (url.startsWith("/guides/") && url.endsWith(".md")) {
          const safeName = path.basename(url);
          const filePath = path.join(PUBLIC_DIR, "guides", safeName);
          if (fs.existsSync(filePath)) {
            res.setHeader("Content-Type", "text/plain; charset=utf-8");
            res.setHeader("Cache-Control", "no-cache");
            fs.createReadStream(filePath).pipe(res);
            return;
          }
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [serveGuides(), react()],
  server: {
    port: 5173,
    proxy: {
      "/v1": {
        target: process.env.VITE_API_URL || "http://api:8000",
        changeOrigin: true,
      },
    },
    watch: {
      ignored: ["**/public/guides/**"],
    },
  },
});
