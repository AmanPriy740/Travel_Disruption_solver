/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B1220",
        panel: "#111A2C",
        line: "#233047",
        signal: "#F5A623",
        alert: "#E5484D",
        go: "#2FBF71",
        wash: "#0E1626",
      },
      fontFamily: {
        display: ["'IBM Plex Mono'", "monospace"],
        body: ["'Inter'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}
