import PublicLayout from '@/src/components/PublicLayout';
import { ContactPage } from '@/src/views/PublicPages';
export const metadata = { title: 'Contact', description: 'Contact Semranko for product support or a tailored plan discussion.', alternates: { canonical: '/contact' } };
export default function Page() { return <PublicLayout><ContactPage /></PublicLayout>; }
