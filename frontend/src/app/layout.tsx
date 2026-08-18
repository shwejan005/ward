import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'WARD — Autonomous Multi-Agent PR Review System',
  description: 'Parallel specialist reasoners over Git diffs with grounded codebase memory and HITL gating.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
