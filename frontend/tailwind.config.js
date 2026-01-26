/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './App.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './pages/**/*.{ts,tsx}',
    './store/**/*.{ts,tsx}',
    './types.{ts,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        secondary: '#64748B',
        success: '#22C55E',
        warning: '#F59E0B',
        error: '#EF4444',
        background: {
          light: '#F8FAFC',
          dark: '#0F172A',
        },
        card: {
          light: '#FFFFFF',
          dark: '#111827',
        },
        text: {
          primary: '#0F172A',
          primaryDark: '#E5E7EB',
          secondary: '#475569',
          secondaryDark: '#9CA3AF',
        },
      },
    },
  },
  plugins: [],
};
