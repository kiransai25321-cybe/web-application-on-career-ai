// Dashboard Interactive Charts and Tabs Initialization (Warm Palette Edition)

document.addEventListener('DOMContentLoaded', () => {
  // --- Tab Navigation ---
  const tabButtons = document.querySelectorAll('.dashboard-tab-btn');
  const tabPanels = document.querySelectorAll('.dashboard-tab-panel');

  function switchTab(targetTab) {
    tabButtons.forEach(btn => {
      const tabName = btn.getAttribute('data-tab');
      if (tabName === targetTab) {
        btn.classList.add('border-[#F4728B]', 'text-[#E11D48]', 'bg-[#FFF1E8]', 'font-bold');
        btn.classList.remove('border-transparent', 'text-[#797386]', 'hover:text-[#29243A]');
      } else {
        btn.classList.remove('border-[#F4728B]', 'text-[#E11D48]', 'bg-[#FFF1E8]', 'font-bold');
        btn.classList.add('border-transparent', 'text-[#797386]', 'hover:text-[#29243A]');
      }
    });

    tabPanels.forEach(panel => {
      if (panel.id === `tab-panel-${targetTab}`) {
        panel.classList.remove('hidden');
      } else {
        panel.classList.add('hidden');
      }
    });

    // Update URL query parameter without full reload
    const url = new URL(window.location);
    url.searchParams.set('tab', targetTab);
    window.history.replaceState({}, '', url);
  }

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      switchTab(tabName);
    });
  });

  // Check URL query param for default tab
  const urlParams = new URLSearchParams(window.location.search);
  const initialTab = urlParams.get('tab') || 'overview';
  if (document.getElementById(`tab-panel-${initialTab}`)) {
    switchTab(initialTab);
  }

  // --- Mistakes Severity Filter ---
  const filterBtns = document.querySelectorAll('.severity-filter-btn');
  const mistakeCards = document.querySelectorAll('.mistake-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const filter = btn.getAttribute('data-filter');
      
      filterBtns.forEach(b => {
        b.classList.remove('bg-[#E11D48]', 'text-white');
        b.classList.add('bg-white', 'text-[#797386]');
      });
      btn.classList.remove('bg-white', 'text-[#797386]');
      btn.classList.add('bg-[#E11D48]', 'text-white');

      mistakeCards.forEach(card => {
        const severity = card.getAttribute('data-severity');
        if (filter === 'all' || severity === filter) {
          card.classList.remove('hidden');
        } else {
          card.classList.add('hidden');
        }
      });
    });
  });

  // --- Initialize Chart.js Charts with Warm Theme ---
  if (typeof Chart !== 'undefined' && window.DASHBOARD_DATA) {
    const data = window.DASHBOARD_DATA;

    // 1. Doughnut Match Score Chart
    const matchCtx = document.getElementById('matchDoughnutChart');
    if (matchCtx) {
      const matchScore = data.matchScore || 0;
      const remainder = Math.max(0, 100 - matchScore);
      new Chart(matchCtx, {
        type: 'doughnut',
        data: {
          labels: ['Matched Fit', 'Gap'],
          datasets: [{
            data: [matchScore, remainder],
            backgroundColor: ['#F4728B', '#FFF1E8'],
            borderWidth: 2,
            borderColor: '#FFFCF8',
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '78%',
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return ` ${context.label}: ${context.raw}%`;
                }
              }
            }
          }
        }
      });
    }

    // 2. Horizontal Bar Chart: Recommended Roles Fit
    const rolesCtx = document.getElementById('rolesBarChart');
    if (rolesCtx && data.recommendedRoles && data.recommendedRoles.length > 0) {
      const topRoles = data.recommendedRoles.slice(0, 5);
      new Chart(rolesCtx, {
        type: 'bar',
        data: {
          labels: topRoles.map(r => r.title),
          datasets: [{
            label: 'Fit Score (%)',
            data: topRoles.map(r => r.fit_percentage),
            backgroundColor: topRoles.map((r, i) => i === 0 ? '#F4728B' : '#FDBA9A'),
            borderRadius: 8,
            barThickness: 18,
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              min: 0,
              max: 100,
              grid: { color: '#F0E5DE' },
              ticks: { color: '#797386' }
            },
            y: {
              grid: { display: false },
              ticks: { color: '#29243A', font: { weight: '600' } }
            }
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return ` Fit Score: ${context.raw}%`;
                }
              }
            }
          }
        }
      });
    }

    // 3. Category Skills Count Bar Chart
    const catCtx = document.getElementById('skillsCategoryChart');
    if (catCtx && data.categorizedSkills) {
      const labels = Object.keys(data.categorizedSkills);
      const counts = labels.map(k => data.categorizedSkills[k].length);
      new Chart(catCtx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Skills Count',
            data: counts,
            backgroundColor: '#FB923C',
            borderRadius: 8,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: '#797386', font: { size: 10, weight: '500' } }
            },
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, color: '#797386' },
              grid: { color: '#F0E5DE' }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    // 4. Radar Chart: Role Alignment
    const radarCtx = document.getElementById('matchRadarChart');
    if (radarCtx && data.radarMetrics) {
      new Chart(radarCtx, {
        type: 'radar',
        data: {
          labels: data.radarMetrics.labels,
          datasets: [
            {
              label: 'Your Resume Profile',
              data: data.radarMetrics.candidate,
              backgroundColor: 'rgba(244, 114, 139, 0.25)',
              borderColor: '#F4728B',
              pointBackgroundColor: '#F4728B',
              borderWidth: 2,
            },
            {
              label: 'Target Role Benchmark',
              data: data.radarMetrics.target,
              backgroundColor: 'rgba(253, 186, 154, 0.15)',
              borderColor: '#FB923C',
              pointBackgroundColor: '#FB923C',
              borderWidth: 2,
              borderDash: [4, 4]
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              angleLines: { color: '#F0E5DE' },
              grid: { color: '#F0E5DE' },
              pointLabels: { color: '#29243A', font: { size: 11, weight: '600' } },
              ticks: { display: false, maxTicksLimit: 5 },
              min: 0,
              max: 100
            }
          },
          plugins: {
            legend: {
              position: 'top',
              labels: { color: '#29243A', boxWidth: 12, padding: 14, font: { weight: '600' } }
            }
          }
        }
      });
    }
  }
});
