import PublicLayout from '@/src/components/PublicLayout';
import { LegalPage } from '@/src/views/PublicPages';
export const metadata = { title: 'Terms of Service', description: 'RankCare terms of service draft.', alternates: { canonical: '/terms' } };
export default function Page() { return <PublicLayout><LegalPage kind="terms" /></PublicLayout>; }
