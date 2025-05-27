/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './lux_home/app/templates/**/*.html', // Path to Flask templates
    './lux_home/app/static/src/**/*.js', // Path to any JS files that might manipulate classes
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
