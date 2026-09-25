/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#FAF8F3',
        foreground: '#1C2B3A',
        primary: {
          DEFAULT: '#4A90C4',
          foreground: '#FFFFFF',
          hover: '#3A7DB0',
        },
        accent: {
          DEFAULT: '#3D8B6E',
          foreground: '#FFFFFF',
          hover: '#2D5A40',
        },
        secondary: {
          DEFAULT: '#EBF5EC',
          foreground: '#2D5A40',
        },
        muted: {
          DEFAULT: '#F0EDE7',
          foreground: '#6B7A8D',
        },
        card: {
          DEFAULT: '#FFFFFF',
          foreground: '#1C2B3A',
        },
        border: '#DDD9D1',
        ring: '#4A90C4',
        patient: {
          DEFAULT: '#4A90C4',
          tint: '#EBF4FB',
          dark: '#2B5F8A',
        },
        doctor: {
          DEFAULT: '#3D8B6E',
          tint: '#EBF5EC',
          dark: '#2D5A40',
        },
        hospital: {
          DEFAULT: '#7B5EA7',
          tint: '#F5F0FC',
          dark: '#5B3D8A',
        },
        emergency: {
          DEFAULT: '#E07B39',
          tint: '#FEF3E8',
          dark: '#A05520',
          hover: '#C96A28',
        },
        danger: {
          DEFAULT: '#D94F7A',
          tint: '#FDEEF4',
        }
      },
      fontFamily: {
        serif: ['"DM Serif Display"', 'serif'],
        sans: ['Nunito', 'sans-serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(28, 43, 58, 0.05)',
      }
    },
  },
  plugins: [],
}
