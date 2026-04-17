/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '*.googleusercontent.com' },
      { protocol: 'https', hostname: '*.googleapis.com' },
      { protocol: 'https', hostname: '*.google.com' },
      { protocol: 'https', hostname: '*.vercel.app' },
    ],
  },

};

module.exports = nextConfig;
