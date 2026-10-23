import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { registerSW } from "virtual:pwa-register";
import App from "./App";
import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root is missing from index.html");
createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// The service worker keeps the app shell and catalog files available offline.
if (import.meta.env.PROD) registerSW({ immediate: true });
