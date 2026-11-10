/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Paleta "Reator Arc": azul-gelo sobre fundo abissal
        void: "#020813",
        arc: {
          50: "#eafcff",
          100: "#c9f6ff",
          200: "#93ecff",
          300: "#4fdcff",
          400: "#1fc2f5",
          500: "#0a9fd6",
          600: "#0a7cae",
          700: "#0d5f88",
          800: "#0f4a6b",
          900: "#0b2f47",
        },
      },
      fontFamily: {
        display: ["Orbitron", "Rajdhani", "system-ui", "sans-serif"],
        body: ["Rajdhani", "system-ui", "sans-serif"],
      },
      keyframes: {
        spin_reverse: { from: { transform: "rotate(360deg)" }, to: { transform: "rotate(0deg)" } },
        arc_pulse: {
          "0%, 100%": { opacity: "0.55", transform: "scale(0.96)" },
          "50%": { opacity: "1", transform: "scale(1.04)" },
        },
        core_flicker: {
          "0%, 100%": { filter: "brightness(1)" },
          "45%": { filter: "brightness(1.25)" },
          "55%": { filter: "brightness(0.9)" },
        },
        ripple: {
          "0%": { transform: "scale(0.55)", opacity: "0.7" },
          "100%": { transform: "scale(1.35)", opacity: "0" },
        },
        blink: { "0%, 49%": { opacity: "1" }, "50%, 100%": { opacity: "0" } },
      },
      animation: {
        "spin-slow": "spin 30s linear infinite",
        "spin-reverse": "spin_reverse 30s linear infinite",
        "arc-pulse": "arc_pulse 4s ease-in-out infinite",
        "core-flicker": "core_flicker 3s ease-in-out infinite",
        ripple: "ripple 2s ease-out infinite",
        blink: "blink 1s steps(1) infinite",
      },
      boxShadow: {
        arc: "0 0 30px rgba(31,194,245,0.45), inset 0 0 20px rgba(31,194,245,0.25)",
      },
    },
  },
  plugins: [],
};
