// ESLint do frontend (refatoração 4.2). Só regras do núcleo, sem plugins: roda com
//   npm run lint
// Pega nomes indefinidos, imports/variáveis sem uso, chaves duplicadas e código inalcançável.
const browserGlobals = Object.fromEntries(
  [
    "window", "document", "navigator", "localStorage", "sessionStorage", "fetch", "setTimeout", "clearTimeout",
    "setInterval", "clearInterval", "requestAnimationFrame", "cancelAnimationFrame", "performance", "URL",
    "URLSearchParams", "Blob", "Audio", "AudioContext", "AudioWorkletNode", "AudioWorkletProcessor",
    "registerProcessor", "sampleRate", "IntersectionObserver", "CustomEvent", "StorageEvent", "WebSocket",
    "console", "Event", "alert", "confirm", "atob", "btoa", "HTMLElement", "HTMLInputElement", "HTMLTextAreaElement", "MediaRecorder", "FileReader", "Image",
    "location", "history", "getComputedStyle", "matchMedia", "ResizeObserver", "queueMicrotask",
    "structuredClone", "AbortController", "TextDecoder", "TextEncoder", "SpeechSynthesisUtterance", "speechSynthesis",
  ].map((name) => [name, "readonly"]),
);

// Os comentários "eslint-disable react-hooks/exhaustive-deps" do código citam o plugin do React.
// Ele não é instalado aqui; esta regra vazia só evita o erro "regra não encontrada".
const reactHooksStub = { rules: { "exhaustive-deps": { create: () => ({}) } } };

export default [
  { ignores: ["dist/**", "node_modules/**"] },
  {
    files: ["src/**/*.{js,jsx}", "tests/**/*.js"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...browserGlobals, process: "readonly" },
    },
    plugins: { "react-hooks": reactHooksStub },
    linterOptions: { reportUnusedDisableDirectives: "off" },
    rules: {
      "no-undef": "error",
      "no-unused-vars": ["warn", { args: "none", varsIgnorePattern: "^React$" }],
      "no-dupe-keys": "error",
      "no-unreachable": "error",
    },
  },
];
