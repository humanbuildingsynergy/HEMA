/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Custom colors inspired by modern chat interfaces
        'bear-primary': '#10a37f',
        'bear-primary-dark': '#0d8a6a',
        // Background colors
        'bear-bg-light': '#ffffff',
        'bear-bg-dark': '#212121',
        // Sidebar colors
        'bear-sidebar-light': '#f9fafb',
        'bear-sidebar-dark': '#171717',
        // Message colors
        'bear-message-light': '#f7f7f8',
        'bear-message-dark': '#2f2f2f',
        // Border colors
        'bear-border-light': '#e5e5e5',
        'bear-border-dark': '#3f3f3f',
        // Text colors
        'bear-text-light': '#1a1a1a',
        'bear-text-dark': '#ececec',
        'bear-text-secondary-light': '#6b7280',
        'bear-text-secondary-dark': '#9ca3af',
        // Hover colors
        'bear-hover-light': '#f3f4f6',
        'bear-hover-dark': '#3a3a3a',
      },
      fontFamily: {
        sans: ['Inter', 'Söhne', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['Söhne Mono', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 1.5s infinite',
      }
    },
  },
  plugins: [],
}
