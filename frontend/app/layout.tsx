import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Trialogue",
  description: "Three models, one answer.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen relative">
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
