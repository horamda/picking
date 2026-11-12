module.exports = {
    content: ['./index.html', './src/**/*.{js,jsx}'],
    theme: {
        extend: {
            fontFamily: { sans: ['"Inter Variable"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
            borderRadius: { lg: '8px', xl: '8px', '2xl': '10px', '3xl': '12px' },
            colors: {
                brand: {
                    50: '#eef4ff',
                    100: '#d9e7ff',
                    200: '#bcd3ff',
                    300: '#8eb7ff',
                    400: '#588ff5',
                    500: '#2868d7',
                    600: '#174fb5',
                    700: '#0b3d91',
                    800: '#0b3478',
                    900: '#0d2d61',
                    950: '#071a3b',
                }
            }
        }
    },
    plugins: [],
}
