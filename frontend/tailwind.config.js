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
        'hema-primary': '#10a37f',
        'hema-primary-dark': '#0d8a6a',
        // Background colors
        'hema-bg-light': '#ffffff',
        'hema-bg-dark': '#212121',
        // Sidebar colors
        'hema-sidebar-light': '#f9fafb',
        'hema-sidebar-dark': '#171717',
        // Message colors
        'hema-message-light': '#f7f7f8',
        'hema-message-dark': '#2f2f2f',
        // Border colors
        'hema-border-light': '#e5e5e5',
        'hema-border-dark': '#3f3f3f',
        // Text colors
        'hema-text-light': '#1a1a1a',
        'hema-text-dark': '#ececec',
        'hema-text-secondary-light': '#6b7280',
        'hema-text-secondary-dark': '#9ca3af',
        // Hover colors
        'hema-hover-light': '#f3f4f6',
        'hema-hover-dark': '#3a3a3a',
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
