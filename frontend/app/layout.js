import "./globals.css";

export const metadata = {
  title: "Paper HOT · 计算传播论文精选",
  description: "追踪计算传播研究的新论文，提供 AI 辅助整理的精选、摘要和主题标签。",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
