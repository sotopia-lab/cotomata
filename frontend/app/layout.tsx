import type { Metadata } from "next";
import "./globals.css";
import { WebSocketProvider } from "@/context/loading-provider";

export const metadata: Metadata = {
  title: "Cotomata",
  description: "Research Prototype for Studying Cooperative Agents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <WebSocketProvider>
          {children}
        </WebSocketProvider>
      </body>
    </html>
  );
}