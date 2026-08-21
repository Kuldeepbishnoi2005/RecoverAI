/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#F9F9F9',
        surface: {
          DEFAULT: '#FFFFFF',
          muted: '#F3F3F3',
          container: '#EEEEEE',
          dim: '#DADADA',
        },
        brand: {
          primary: '#1A1A1A',
          secondary: '#605984',
          accent: '#5C547F',
          lavender: '#D5CBFD',
          lavenderLight: '#F3EFFF',
        },
        fintech: {
          mauve: '#B68D91',
          blueGray: '#7A8C99',
          mutedBrown: '#A39185',
          border: '#E5E7EB',
          textPrimary: '#1A1C1C',
          textMuted: '#444748',
        },
        status: {
          success: '#10B981',
          successBg: '#ECFDF5',
          warning: '#F59E0B',
          warningBg: '#FFFBEB',
          danger: '#EF4444',
          dangerBg: '#FEF2F2',
          info: '#3B82F6',
          infoBg: '#EFF6FF',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['"Hanken Grotesk"', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        subtle: '0px 4px 20px rgba(0, 0, 0, 0.04)',
        card: '0px 1px 3px rgba(0, 0, 0, 0.05), 0px 1px 2px rgba(0, 0, 0, 0.03)',
      },
      borderRadius: {
        'card': '1rem', // 16px
        'elem': '0.5rem', // 8px
      }
    },
  },
  plugins: [],
}
