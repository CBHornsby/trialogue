/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0e0d0c",
          900: "#15140f",
          800: "#1c1a14",
          700: "#26231b",
          600: "#3a352a",
          500: "#5a5346",
          400: "#7a7264",
          300: "#a39a8a",
          200: "#c9bfae",
          100: "#e8dfcd",
          50:  "#f5ecd9",
        },
        proposer: {
          DEFAULT: "#d4a25e",  // warm amber
          dim: "#8a6a3e",
        },
        critic: {
          DEFAULT: "#7d9bb4",  // cool slate
          dim: "#516576",
        },
        judge: {
          DEFAULT: "#88a888",  // muted sage
          dim: "#5a715a",
        },
      },
      fontFamily: {
        display: ['"Fraunces"', "ui-serif", "Georgia", "serif"],
        body: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.5s ease-out",
        "pulse-slow": "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
