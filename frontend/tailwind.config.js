/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
      },
      colors: {
        wa: {
          green: '#25D366',
          'green-dark': '#128C7E',
          'green-darker': '#075E54',
          teal: '#075E54',
          bg: '#ECE5DD',
          panel: '#F0F2F5',
          bubble: '#FFFFFF',
          'bubble-out': '#DCF8C6',
        },
        // Validated single-hue sequential ramp (data-viz skill) -- used only
        // for magnitude encodings (mastery/accuracy/QDI bars, score meter),
        // never for chrome. Passes --ordinal: monotone L, >=0.06 adjacent
        // gaps, light-end contrast 2.13:1 vs #fcfcfb.
        seq: {
          100: '#6ec090',
          300: '#2fa268',
          500: '#187a49',
          700: '#0a4f2f',
        },
        // Fixed status palette (never themed / never reused for series) --
        // always paired with an icon + label, never color alone.
        status: {
          good: '#0ca30c',
          warning: '#fab219',
          serious: '#ec835a',
          critical: '#d03b3b',
        },
        ink: {
          primary: '#0b0b0b',
          secondary: '#52514e',
          muted: '#898781',
        },
      },
      keyframes: {
        'bubble-in': {
          '0%': { opacity: '0', transform: 'translateY(6px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'typing-bounce': {
          '0%, 80%, 100%': { transform: 'translateY(0)', opacity: '0.5' },
          '40%': { transform: 'translateY(-4px)', opacity: '1' },
        },
        'pop': {
          '0%': { transform: 'scale(1)' },
          '40%': { transform: 'scale(0.96)' },
          '100%': { transform: 'scale(1)' },
        },
        'ring-grow': {
          '0%': { strokeDashoffset: 'var(--ring-circumference)' },
          '100%': { strokeDashoffset: 'var(--ring-offset)' },
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'bubble-in': 'bubble-in 0.22s ease-out',
        'typing-bounce': 'typing-bounce 1.2s ease-in-out infinite',
        pop: 'pop 0.22s ease-out',
        'ring-grow': 'ring-grow 0.8s ease-out forwards',
        'fade-up': 'fade-up 0.3s ease-out',
      },
    },
  },
  plugins: [],
}
