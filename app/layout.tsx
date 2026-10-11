import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "AXXIBOTS HQ — Operations cockpit",
  description: "Private, read-only operations cockpit for AXXIBOTS",
  robots: { index: false, follow: false },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
