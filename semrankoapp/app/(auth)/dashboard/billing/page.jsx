import { redirect } from 'next/navigation'

export const metadata = {
  title: 'Billing & Invoices - Semranko',
  description: 'View transaction history, download invoices, and purchase credits.',
}

export default function Page() {
  redirect('/billing')
}
