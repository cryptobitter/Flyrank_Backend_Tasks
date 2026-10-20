import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Decision Flow | Visual Workflow Engine with React Flow & Inngest',
  description:
    'Visual AI workflow system where each node represents an AI decision step returning YES or NO, executed via Inngest and visualized using React Flow.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        {children}
      </body>
    </html>
  );
}
