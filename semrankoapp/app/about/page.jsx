import PublicLayout from '@/src/components/PublicLayout';
import { AboutPage } from '@/src/views/PublicPages';
export const metadata = { title: 'About', description: 'Learn how Semranko keeps SEO tracking and search visibility practical.', alternates: { canonical: '/about' } };
export default function Page() { return <PublicLayout><AboutPage /></PublicLayout>; }
