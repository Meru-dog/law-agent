import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LexRAG — Law Firm Intelligence",
  description: "Internal knowledge retrieval for legal matters",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
