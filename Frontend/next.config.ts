import type { NextConfig } from "next";
import path from "path";

const nextConfig: any = {
  allowedDevOrigins: ["10.10.13.49", "localhost", "127.0.0.1"],
  experimental: {
    turbopack: {
      root: path.resolve(process.cwd(), "..")
    }
  }
};

export default nextConfig;
