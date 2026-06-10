export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Hanken Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
      },
      colors: {
        paper: "#F4F2EE",
        surface: "#FFFFFF",
        ink: {
          DEFAULT: "#1F1B17",
          soft: "#4A443D",
          muted: "#857C71",
          faint: "#B4ABA0",
        },
        line: "#E6E1D8",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(31,27,23,0.06)",
        card: "0 1px 2px rgba(31,27,23,0.04), 0 8px 24px -14px rgba(31,27,23,0.12)",
        pop: "0 16px 48px -16px rgba(31,27,23,0.22)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
}
