import PublicLayout from '@/src/components/PublicLayout';
import { FaqPage } from '@/src/views/PublicPages';
export const metadata = { title: 'FAQ', description: 'Answers about RankCare plans, credits, keyword tracking, and billing.', alternates: { canonical: '/faq' } };
export default function Page() { return <PublicLayout><FaqPage /></PublicLayout>; }
