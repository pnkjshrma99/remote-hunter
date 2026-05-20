import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172126",
        paper: "#f7f5ef",
        moss: "#2f6f5e",
        coral: "#c95b45",
        sky: "#2f6db5"
      }
    }
  },
  plugins: []
};

export default config;
