import type { Metadata } from "next";
import "./globals.css";
import "./library.css";
import "./masonry.css";
import { AppSidebar, MobileBar } from "../components/app-sidebar";
import { SidebarInset, SidebarProvider } from "../components/ui/sidebar";

export const metadata: Metadata = {
  title: "Paper HOT",
  description: "追踪计算传播研究的新论文，提供 AI 辅助整理的精选、摘要和主题标签。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>
        <SidebarProvider>
          <AppSidebar />
          <SidebarInset>
            <MobileBar />
            {children}
          </SidebarInset>
        </SidebarProvider>
      </body>
    </html>
  );
}
