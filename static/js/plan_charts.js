// Charts for the job search plan pages. Reads #plan-chart-data.
(function () {
  var holder = document.getElementById('plan-chart-data');
  if (!holder || !window.Chart) return;
  var data = JSON.parse(holder.textContent);
  var charts = [];

  function colors() {
    var dark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    return { text: dark ? '#9aa3b8' : '#6b7280', grid: dark ? 'rgba(255,255,255,.07)' : 'rgba(16,24,40,.06)' };
  }
  var c = colors();
  Chart.defaults.color = c.text;
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

  function targetLine(label, value, length) {
    return { type: 'line', label: label, data: new Array(length).fill(value), borderColor: '#f59e0b', borderDash: [6, 5],
             borderWidth: 2, pointRadius: 0, fill: false, order: 0 };
  }
  var scales = { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: c.grid } } };

  var dailyEl = document.getElementById('dailyChart');
  if (dailyEl) {
    charts.push(new Chart(dailyEl, {
      type: 'bar',
      data: {
        labels: data.daily.labels,
        datasets: [
          { label: 'Applications', data: data.daily.applications, backgroundColor: '#5b5bf0', borderRadius: 6, maxBarThickness: 26, order: 1 },
          { label: 'Networking', data: data.daily.networking, backgroundColor: '#38bdf8', borderRadius: 6, maxBarThickness: 26, order: 2 },
          targetLine('Daily target', data.daily.target, data.daily.labels.length)
        ]
      },
      options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true } } }, scales: scales }
    }));
  }

  var weekEl = document.getElementById('weekChart');
  if (weekEl) {
    charts.push(new Chart(weekEl, {
      type: 'bar',
      data: {
        labels: data.week.labels,
        datasets: [
          { label: 'Applications', data: data.week.applications, backgroundColor: '#8b5cf6', borderRadius: 8, maxBarThickness: 38, order: 1 },
          targetLine('Daily target', data.week.target, data.week.labels.length)
        ]
      },
      options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true } } }, scales: scales }
    }));
  }

  window.addEventListener('themechange', function () {
    var k = colors();
    Chart.defaults.color = k.text;
    charts.forEach(function (ch) {
      ch.options.scales.y.grid.color = k.grid;
      ch.update();
    });
  });
})();
