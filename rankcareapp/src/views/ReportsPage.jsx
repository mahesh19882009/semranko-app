'use client'
import { useEffect, useMemo, useState } from 'react';
import { useSelector } from 'react-redux';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { faFilePdf, faSpinner } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Alert from '../components/ui/Alert';
import { apiRequest } from '../lib/api';

const COLORS = {
  brand700: '#0e7490',
  brand600: '#0891b2',
  brand500: '#06b6d4',
  brand100: '#cffafe',
  brand50: '#ecfeff',
  slate900: '#0f172a',
  slate700: '#334155',
  slate500: '#64748b',
  slate400: '#94a3b8',
  slate200: '#e2e8f0',
  slate100: '#f1f5f9',
  slate50: '#f8fafc',
  success: '#10b981',
  successLight: '#d1fae5',
  warning: '#f59e0b',
  warningLight: '#fef3c7',
  danger: '#ef4444',
  info: '#3b82f6',
  infoLight: '#dbeafe',
  purple: '#8b5cf6',
  purpleLight: '#ede9fe',
};

function ReportsPage() {
  const projects = useSelector((state) => state.projects.list);
  const projectsLoading = useSelector((state) => state.projects.loading);
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

  const [selectedProject, setSelectedProject] = useState(selectedProjectId || '');
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (selectedProjectId && !selectedProject) {
      setSelectedProject(selectedProjectId);
    }
  }, [selectedProjectId, selectedProject]);

  const fetchKeywords = async () => {
    if (!selectedProject) return;
    setLoading(true);
    setError('');
    try {
      const json = await apiRequest(`/keywords/${selectedProject}/table`);
      setKeywords(json.data?.rows || []);
    } catch (err) {
      setError(err.message || 'Failed to load keywords');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeywords();
  }, [selectedProject]);

  const summaryStats = useMemo(() => {
    const total = keywords.length;
    const withPosition = keywords.filter((r) => r.position != null);
    const avgPosition = withPosition.length
      ? withPosition.reduce((a, b) => a + b.position, 0) / withPosition.length
      : null;
    const aioCount = keywords.filter((r) => r.hasAIOverview).length;
    const withCPC = keywords.filter((r) => r.cpc != null);
    const avgCPC = withCPC.length
      ? withCPC.reduce((a, b) => a + b.cpc, 0) / withCPC.length
      : null;
    return { total, avgPosition, aioCount, avgCPC };
  }, [keywords]);

  const positionDistribution = useMemo(() => {
    const top3 = keywords.filter((r) => r.position != null && r.position <= 3).length;
    const top10 = keywords.filter((r) => r.position != null && r.position > 3 && r.position <= 10).length;
    const top50 = keywords.filter((r) => r.position != null && r.position > 10 && r.position <= 50).length;
    const top100 = keywords.filter((r) => r.position != null && r.position > 50 && r.position <= 100).length;
    const notRanking = keywords.filter((r) => r.position == null || r.position === undefined).length;
    const total = keywords.length || 1;
    return [
      { label: 'Top 3', count: top3, color: COLORS.success, pct: Math.round((top3 / total) * 100) },
      { label: 'Top 10', count: top10, color: COLORS.info, pct: Math.round((top10 / total) * 100) },
      { label: '11-50', count: top50, color: '#6366F1', pct: Math.round((top50 / total) * 100) },
      { label: '51-100', count: top100, color: COLORS.warning, pct: Math.round((top100 / total) * 100) },
      { label: 'Not Ranking', count: notRanking, color: COLORS.slate400, pct: Math.round((notRanking / total) * 100) },
    ];
  }, [keywords]);

  const generatePDF = async () => {
    if (!keywords.length) return;
    setGenerating(true);
    setError('');
    try {
      await apiRequest(`/projects/${selectedProject}/reports/keyword-pdf`, {
        method: 'POST',
      });
    } catch (err) {
      setError(err.message || 'Failed to deduct credits for PDF report.');
      setGenerating(false);
      return;
    }

    try {
      const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const margin = 15;
      const usableWidth = pageWidth - margin * 2;
      let yPos = margin;

      const project = projects.find((p) => String(p.id) === String(selectedProject));
      const projectName = project?.name || 'Unknown Project';
      const generatedAt = new Date().toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });

      doc.setFillColor(COLORS.brand700);
      doc.rect(0, 0, pageWidth, 36, 'F');

      doc.setTextColor(255, 255, 255);
      doc.setFontSize(18);
      doc.setFont('helvetica', 'bold');
      doc.text('Keyword Report', margin, 16);

      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(`Project: ${projectName}`, margin, 25);
      doc.text(`Generated: ${generatedAt}`, margin, 32);

      yPos = 44;

      const statBoxWidth = (usableWidth - 12) / 2;
      const statBoxHeight = 26;
      const stats = [
        { label: 'Total Keywords', value: summaryStats.total.toLocaleString(), color: COLORS.brand500, bg: COLORS.brand50 },
        { label: 'Avg Position', value: summaryStats.avgPosition ? `#${summaryStats.avgPosition.toFixed(1)}` : '—', color: COLORS.success, bg: COLORS.successLight },
        { label: 'AIO Keywords', value: summaryStats.aioCount.toLocaleString(), color: COLORS.warning, bg: COLORS.warningLight },
        { label: 'Avg CPC', value: summaryStats.avgCPC ? `₹${summaryStats.avgCPC.toFixed(2)}` : '—', color: COLORS.purple, bg: COLORS.purpleLight },
      ];

      stats.forEach((stat, index) => {
        const col = index % 2;
        const row = Math.floor(index / 2);
        const x = margin + col * (statBoxWidth + 12);
        const y = yPos + row * (statBoxHeight + 8);
        doc.setFillColor(stat.bg);
        doc.rect(x, y, statBoxWidth, statBoxHeight, 'F');
        doc.setDrawColor(COLORS.slate200);
        doc.rect(x, y, statBoxWidth, statBoxHeight, 'S');

        doc.setTextColor(COLORS.slate500);
        doc.setFontSize(8);
        doc.setFont('helvetica', 'normal');
        doc.text(stat.label, x + 4, y + 7);

        doc.setTextColor(COLORS.slate900);
        doc.setFontSize(12);
        doc.setFont('helvetica', 'bold');
        doc.text(stat.value, x + 4, y + 18);
      });

      yPos += statBoxHeight * 2 + 16;

      doc.setFontSize(11);
      doc.setTextColor(COLORS.slate900);
      doc.setFont('helvetica', 'bold');
      doc.text('Ranking Distribution', margin, yPos);
      yPos += 2;

      const barMaxWidth = usableWidth - 55;
      const barHeight = 4;
      const barGap = 6;
      const labelX = margin;
      const barX = margin + 32;

      positionDistribution.forEach((item) => {
        const barWidth = item.count > 0 ? (item.count / summaryStats.total) * barMaxWidth : 0;

        doc.setFontSize(8);
        doc.setTextColor(COLORS.slate700);
        doc.setFont('helvetica', 'normal');
        doc.text(item.label, labelX, yPos + 3);

        doc.setFillColor(COLORS.slate100);
        doc.rect(barX, yPos, barMaxWidth, barHeight, 'F');

        if (barWidth > 0) {
          doc.setFillColor(item.color);
          doc.rect(barX, yPos, barWidth, barHeight, 'F');
        }

        doc.setFontSize(7);
        doc.setTextColor(COLORS.slate500);
        doc.text(`${item.count} (${item.pct}%)`, barX + barMaxWidth + 2, yPos + 3);

        yPos += barGap;
      });

      yPos += 8;

      const tableHeaders = [
        'Keyword', 'Volume', 'KD', 'CPC (₹)', 'Competition',
        'Backlinks', 'Domains', 'Intent', 'Position', 'Visibility',
        'Ranking URL', 'AI Overview'
      ];

      const tableRows = keywords.map((kw) => [
        kw.keyword || '—',
        kw.volume != null ? kw.volume.toLocaleString() : '—',
        kw.kd != null ? kw.kd : '—',
        kw.cpc != null ? `₹${kw.cpc.toFixed(2)}` : '—',
        kw.competition != null ? kw.competition.toFixed(2) : '—',
        kw.backlinks != null ? Math.round(kw.backlinks).toLocaleString() : '—',
        kw.domains != null ? Math.round(kw.domains).toLocaleString() : '—',
        kw.intent || '—',
        kw.position != null ? `#${kw.position}` : '—',
        kw.visibility != null ? `${(kw.visibility * 100).toFixed(0)}%` : '—',
        kw.check_url || '—',
        kw.hasAIOverview ? 'AIO' : '—',
      ]);

      autoTable(doc, {
        startY: yPos,
        head: [tableHeaders],
        body: tableRows,
        theme: 'grid',
        headStyles: {
          fillColor: COLORS.brand700,
          textColor: [255, 255, 255],
          fontStyle: 'bold',
          fontSize: 8,
          cellPadding: 2.5,
        },
        bodyStyles: {
          fontSize: 7,
          cellPadding: 2,
          textColor: COLORS.slate700,
        },
        alternateRowStyles: {
          fillColor: COLORS.slate50,
        },
        styles: {
          cellPadding: 2,
          fontSize: 7,
          textColor: COLORS.slate700,
          lineColor: COLORS.slate200,
          lineWidth: 0.2,
          overflow: 'linebreak',
        },
        margin: { left: margin, right: margin },
        tableWidth: 'wrap',
        didDrawPage: (data) => {
          const pageCount = doc.getNumberOfPages();
          doc.setFontSize(7);
          doc.setTextColor(COLORS.slate400);
          doc.text(
            `Page ${data.pageNumber} of ${pageCount}`,
            pageWidth / 2,
            pageHeight - 10,
            { align: 'center' }
          );
        },
      });

      doc.save(`keyword-report-${projectName.replace(/\s+/g, '-').toLowerCase()}-${Date.now()}.pdf`);
    } catch {
      setError('Failed to generate PDF. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  if (!selectedProjectId) {
    return (
      <section className="rounded-xs border border-slate-200 bg-white p-6 shadow-soft">
        <p className="text-sm text-slate-500">Select a project first to generate reports.</p>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Reports</h2>
          <p className="mt-1 text-sm text-slate-500">
            Generate and download keyword reports for your projects.
          </p>
        </div>
      </div>

      <Card padding="p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-700 mb-1">Select Project</label>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              disabled={projectsLoading}
              className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 disabled:bg-slate-50 disabled:cursor-not-allowed"
            >
              <option value="">-- Select a project --</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
          <Button
            onClick={generatePDF}
            disabled={!keywords.length || generating || loading}
            loading={generating}
          >
            <FontAwesomeIcon icon={generating ? faSpinner : faFilePdf} />
            {generating ? 'Generating...' : ' Download PDF Report'}
          </Button>
        </div>
      </Card>

      {error && <Alert variant="error" message={error} />}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <FontAwesomeIcon icon={faSpinner} className="animate-spin text-2xl text-brand-600" />
          <span className="ml-3 text-sm text-slate-600">Loading keywords...</span>
        </div>
      )}

      {!loading && keywords.length === 0 && !error && (
        <Card padding="p-8 text-center">
          <FontAwesomeIcon icon={faFilePdf} className="text-4xl text-slate-300 mb-3" />
          <p className="text-sm text-slate-500">No keywords found for the selected project.</p>
        </Card>
      )}

      {!loading && keywords.length > 0 && (
        <Card padding="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Preview</h3>
            <span className="text-sm text-slate-500">{keywords.length} keywords</span>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Ranking Distribution</h4>
              <div className="space-y-2">
                {positionDistribution.map((item) => (
                  <div key={item.label} className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 w-16 shrink-0">{item.label}</span>
                    <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${item.pct}%`, backgroundColor: item.color }}
                      />
                    </div>
                    <span className="text-xs text-slate-500 w-20 text-right">{item.count} ({item.pct}%)</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-slate-200 bg-brand-50 p-3">
                <p className="text-xs font-medium text-brand-700">Total Keywords</p>
                <p className="mt-1 text-lg font-bold text-brand-900">{summaryStats.total.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-emerald-50 p-3">
                <p className="text-xs font-medium text-emerald-700">Avg Position</p>
                <p className="mt-1 text-lg font-bold text-emerald-900">
                  {summaryStats.avgPosition ? `#${summaryStats.avgPosition.toFixed(1)}` : '—'}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-amber-50 p-3">
                <p className="text-xs font-medium text-amber-700">AIO Keywords</p>
                <p className="mt-1 text-lg font-bold text-amber-900">{summaryStats.aioCount.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-purple-50 p-3">
                <p className="text-xs font-medium text-purple-700">Avg CPC</p>
                <p className="mt-1 text-lg font-bold text-purple-900">
                  {summaryStats.avgCPC ? `₹${summaryStats.avgCPC.toFixed(2)}` : '—'}
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

export default ReportsPage;
