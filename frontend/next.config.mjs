/** @type {import('next').NextConfig} */
const basePath = process.env.GITHUB_ACTIONS === "true" ? "/Paper-Hot" : "";

const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath,
  assetPrefix: basePath,
};

export default nextConfig;
