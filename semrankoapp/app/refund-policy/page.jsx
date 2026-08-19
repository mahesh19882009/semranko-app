import PublicLayout from '@/src/components/PublicLayout';
import { LegalPage } from '@/src/views/PublicPages';
export const metadata = { title: 'Refund & Cancellation Policy', description: 'Semranko refund and cancellation policy draft.', alternates: { canonical: '/refund-policy' } };
export default function Page() { return <PublicLayout><LegalPage kind="refund" /></PublicLayout>; }
