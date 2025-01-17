import type { Metadata } from "next";
import localFont from "next/font/local";
import "../globals.css";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/sidebar";
import { CSSProperties } from 'react';

const geistSans = localFont({
  src: "../fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "../fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Cotomata",
  description: "Research Prototype for Studying Cooperative Agents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
    >
      <SidebarProvider
        style={{
            "--sidebar-width": "3rem",
            "--sidebar-width-mobile": "3rem",
        } as CSSProperties}
      >
        
          <main className="h-full w-full">
              {children}
          </main>
      </SidebarProvider>
    </div>
  );
}
