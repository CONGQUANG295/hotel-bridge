import './globals.css';

export const metadata = { title: 'Hotel Bridge · Guest', description: 'Hotel services without an app download' };
export default function GuestLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
