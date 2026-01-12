const path = require('path');

const LOADER = path.resolve(__dirname, 'src/visual-edits/component-tagger-loader.js');

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
      { protocol: 'http', hostname: '**' },
    ],
  },

  typescript: {
    ignoreBuildErrors: true,
  },

  eslint: {
    ignoreDuringBuilds: true,
  },

  // Turbopack configuration (only affects dev mode)
  turbopack: {
    rules: {
      '*.{jsx,tsx}': {
        loaders: [LOADER],
      },
    },
  },
};

module.exports = nextConfig;
