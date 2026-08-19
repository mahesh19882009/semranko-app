import PublicLayout from '@/src/components/PublicLayout';
import { LegalPage } from '@/src/views/PublicPages';
export const metadata = { title: 'Privacy Policy', description: 'Semranko privacy policy draft.', alternates: { canonical: '/privacy' } };
export default function Page() { return <PublicLayout><LegalPage kind="privacy" /></PublicLayout>; }
