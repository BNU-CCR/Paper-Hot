import type { NextConfig } from "next";

const basePath = process.env.GITHUB_ACTIONS === "true" ? "/Paper-Hot" : "";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath,
  assetPrefix: basePath,
  // Expose the basePath to client bundles so runtime URL helpers can build
  // correct paths. Without this NEXT_PUBLIC_BASE_PATH is always undefined and
  // any browser-side URL helper produces paths missing the repo prefix on
  // GitHub Pages.
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

export default nextConfig;
