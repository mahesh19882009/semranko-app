'use client'
import { useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

function RankHistoryChart({ data, keyword }) {
  const chartRef = useRef(null);

  const chartData = {
    labels: data.map((d) => d.date),
    datasets: [
      {
        label: `${keyword} Position`,
        data: data.map((d) => d.position),
        borderColor: 'rgb(79, 70, 229)',
        backgroundColor: 'rgba(79, 70, 229, 0.1)',
        tension: 0.3,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: 'rgb(79, 70, 229)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#fff',
        bodyColor: '#fff',
        padding: 12,
        cornerRadius: 8,
        displayColors: false,
        callbacks: {
          label: function (context) {
            const position = context.parsed.y;
            return position ? `Position: #${position}` : 'Not found';
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
          font: {
            size: 11,
          },
          color: '#64748b',
        },
      },
      y: {
        reverse: true, // Lower position is better, so reverse the axis
        min: 1,
        max: Math.max(...data.map((d) => d.position || 50)) + 5,
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          callback: function (value) {
            return `#${value}`;
          },
          color: '#64748b',
        },
      },
    },
  };

  return (
    <div className="h-64 w-full">
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  );
}

export default RankHistoryChart;
