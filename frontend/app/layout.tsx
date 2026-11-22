import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TenderMind — Global Tender Monitor",
  description: "AI-powered global tender monitoring for transformer and power equipment suppliers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
