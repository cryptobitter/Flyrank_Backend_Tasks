import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        border: "var(--border)",
        card: "var(--card)",
        "card-foreground": "var(--card-foreground)",
        primary: "var(--primary)",
        "primary-foreground": "var(--primary-foreground)",
        secondary: "var(--secondary)",
        "secondary-foreground": "var(--secondary-foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)",
        "accent-foreground": "var(--accent-foreground)",
        destructive: "var(--destructive)",
        "destructive-foreground": "var(--destructive-foreground)",
        decision: {
          yes: "#10b981",
          no: "#ef4444",
          running: "#3b82f6",
        }
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 15px rgba(59, 130, 246, 0.6)" },
          "50%": { boxShadow: "0 0 30px rgba(59, 130, 246, 0.9)" },
        },
        flowDash: {
          "0%": { strokeDashoffset: "24" },
          "100%": { strokeDashoffset: "0" },
        }
      },
      animation: {
        "pulse-glow": "pulseGlow 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "flow-dash": "flowDash 0.8s linear infinite",
      }
    },
  },
  plugins: [],
};
export default config;
