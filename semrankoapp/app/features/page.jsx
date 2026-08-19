import PublicLayout from '@/src/components/PublicLayout';
import { FeaturesPage } from '@/src/views/PublicPages';
export const metadata = { title: 'Features', description: 'Explore Semranko keyword tracking, metrics, research, AIO visibility, and reports.', alternates: { canonical: '/features' } };
export default function Page() { return <PublicLayout><FeaturesPage /></PublicLayout>; }
