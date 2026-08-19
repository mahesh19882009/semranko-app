'use client'
import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import Modal from './Modal';
import Button from './Button';
import Input from './Input';
import Alert from './Alert';

const PRESET_RANGES = [
  { key: 'last_week', label: 'Last Week' },
  { key: 'last_month', label: 'Last Month' },
  { key: 'custom', label: 'Custom' },
];

function formatDateInput(date) {
  if (!date) return '';
  return date.toISOString().slice(0, 10);
}

function getDateRange(preset) {
  const now = new Date();
  if (preset === 'last_week') {
    const start = new Date(now);
    start.setDate(now.getDate() - 7);
    return { start: formatDateInput(start), end: formatDateInput(now) };
  }
  if (preset === 'last_month') {
    const start = new Date(now);
    start.setMonth(now.getMonth() - 1);
    return { start: formatDateInput(start), end: formatDateInput(now) };
  }
  return { start: '', end: '' };
}

export default function ExportReportModal({ open, onClose, projectId }) {
  const [preset, setPreset] = useState('last_week');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [exportFormat, setExportFormat] = useState('csv');
  const [emailRecipients, setEmailRecipients] = useState([]);
  const [emailInput, setEmailInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (!open) return;
    const range = getDateRange(preset);
    setStartDate(range.start);
    setEndDate(range.end);
    setEmailRecipients([]);
    setEmailInput('');
    setError(null);
    setSuccess(null);
    setExportFormat('csv');
  }, [open, preset]);

  const canAddEmail = emailRecipients.length < 3;

  const handleAddEmail = () => {
    const trimmed = emailInput.trim();
    if (!trimmed) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError('Please enter a valid email address');
      return;
    }
    if (emailRecipients.includes(trimmed)) {
      setError('This email is already added');
      return;
    }
    if (emailRecipients.length >= 3) {
      setError('Maximum 3 email recipients allowed');
      return;
    }
    setEmailRecipients((prev) => [...prev, trimmed]);
    setEmailInput('');
    setError(null);
  };

  const handleRemoveEmail = (index) => {
    setEmailRecipients((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!startDate || !endDate) {
      setError('Please select a date range');
      return;
    }
    if (new Date(startDate) > new Date(endDate)) {
      setError('Start date cannot be after end date');
      return;
    }
    if (emailRecipients.length > 3) {
      setError('Maximum 3 email recipients allowed');
      return;
    }

    setLoading(true);
    try {
      const { exportProjectReportApi } = await import('@/src/features/pricing/pricingApi');
      const result = await exportProjectReportApi(projectId, {
        start_date: startDate,
        end_date: endDate,
        export_format: exportFormat,
        email_recipients: emailRecipients,
      });

      setSuccess(`Report generated successfully${result?.email_queued ? ' and queued for email delivery' : ''}`);
      setTimeout(() => {
        onClose?.();
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const footer = (
    <>
      <Button variant="secondary" onClick={onClose} disabled={loading}>
        Cancel
      </Button>
      <Button type="submit" form="export-report-form" loading={loading} disabled={loading}>
        Generate Report
      </Button>
    </>
  );

  return (
    <Modal open={open} onClose={onClose} title="Export Project Report" footer={footer} size="lg">
      <form id="export-report-form" onSubmit={handleSubmit} className="space-y-5">
        {error && <Alert variant="error" message={error} onDismiss={() => setError(null)} />}
        {success && <Alert variant="success" message={success} onDismiss={() => setSuccess(null)} />}

        <div>
          <label className="text-sm font-medium text-slate-700">Date Range</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {PRESET_RANGES.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setPreset(item.key)}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  preset === item.key
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {preset === 'custom' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <Input
              label="End Date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        )}

        {preset !== 'custom' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Start Date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            <Input label="End Date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
        )}

        <div>
          <label className="text-sm font-medium text-slate-700">Export Format</label>
          <div className="mt-2 flex gap-2">
            {['csv', 'pdf'].map((fmt) => (
              <button
                key={fmt}
                type="button"
                onClick={() => setExportFormat(fmt)}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  exportFormat === fmt
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">
            Email Recipients <span className="text-slate-400">(max 3)</span>
          </label>
          <div className="mt-2 flex gap-2">
            <Input
              placeholder="recipient@example.com"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddEmail();
                }
              }}
              disabled={!canAddEmail}
              className="flex-1"
            />
            <Button
              type="button"
              variant="secondary"
              onClick={handleAddEmail}
              disabled={!canAddEmail}
            >
              Add
            </Button>
          </div>

          {emailRecipients.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {emailRecipients.map((email, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-700"
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => handleRemoveEmail(index)}
                    className="flex h-4 w-4 items-center justify-center rounded-full text-brand-400 hover:bg-brand-100 hover:text-brand-600 transition-colors"
                    aria-label={`Remove ${email}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <p className="mt-1.5 text-xs text-slate-500">
            {emailRecipients.length}/3 recipients added
          </p>
        </div>
      </form>
    </Modal>
  );
}
