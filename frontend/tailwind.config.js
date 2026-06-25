/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        rasoi: {
          DEFAULT: '#1D9E75',
          light: '#E8F5F0',
          dark: '#16795A',
          amber: '#E67E22',
          'amber-light': '#FEF3E2',
          red: '#C0392B',
          'red-light': '#FDECEA',
          panel: '#F8F9FA',
        },
      },
      borderRadius: {
        card: '12px',
        pill: '50px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 12px rgba(0,0,0,0.07)',
        'card-hover': '0 6px 24px rgba(29,158,117,0.15)',
      },
      animation: {
        wiggle: 'wiggle 0.6s ease-in-out',
        'bounce-in': 'bounceIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.25s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        wiggle: {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '25%': { transform: 'rotate(-14deg)' },
          '75%': { transform: 'rotate(14deg)' },
        },
        bounceIn: {
          '0%': { transform: 'scale(0.7) translateY(20px)', opacity: '0' },
          '70%': { transform: 'scale(1.05) translateY(-4px)' },
          '100%': { transform: 'scale(1) translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(-6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
