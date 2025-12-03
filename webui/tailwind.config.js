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
        // Custom colors for agent status
        'agent-working': '#3B82F6',    // blue-500
        'agent-voting': '#F59E0B',      // amber-500
        'agent-completed': '#10B981',   // green-500
        'agent-failed': '#EF4444',      // red-500
        'agent-waiting': '#6B7280',     // gray-500
        // Winner highlight
        'winner-gold': '#EAB308',       // yellow-500
        'winner-glow': 'rgba(234, 179, 8, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px 5px rgba(234, 179, 8, 0.3)' },
          '50%': { boxShadow: '0 0 40px 10px rgba(234, 179, 8, 0.5)' },
        },
      },
    },
  },
  plugins: [],
}
