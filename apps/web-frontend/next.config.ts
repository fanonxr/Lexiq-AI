import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for Azure Static Web Apps
  output: 'export',
  
  // Disable image optimization (required for static export)
  images: {
    unoptimized: true,
  },
  
  // Optional: Set trailing slash for better compatibility
  trailingSlash: true,
};

export default nextConfig;
