function stockDetail(ticker) {
  return {
    ticker,
    data: null,
    broker: { top_net_buying: [], top_net_selling: [], positions: [] },
    loading: true,
    priceChart: null,
    volumeChart: null,

    async init() {
      await Promise.all([
        this.fetchDetail(),
        this.fetchBroker(),
      ])
    },

    async fetchDetail() {
      this.loading = true
      try {
        const [detailRes, histRes] = await Promise.all([
          fetch(`/api/detail/${this.ticker}`),
          fetch(`/api/detail/${this.ticker}/ohlcv?limit=90`),
        ])
        const detail = await detailRes.json()
        const hist = await histRes.json()

        this.data = { ...detail.stock, ...detail.analysis }
        this.$nextTick(() => this.renderCharts(hist.reverse()))
      } finally {
        this.loading = false
      }
    },

    async fetchBroker() {
      try {
        const res = await fetch(`/api/broker/${this.ticker}/flow`)
        this.broker = await res.json()
      } catch (_) {}
    },

    renderCharts(hist) {
      const labels = hist.map(h => h.trade_date)
      const closes = hist.map(h => h.close)

      // fetch indicator history for EMA lines
      fetch(`/api/stocks/${this.ticker}/history?limit=90`)
        .then(r => r.json())
        .then(ind => {
          const indReversed = [...ind].reverse()
          const ema20 = indReversed.map(i => i.ema20)
          const ema50 = indReversed.map(i => i.ema50)
          const ema200 = indReversed.map(i => i.ema200)
          const volumes = hist.map(h => h.volume)

          const isDark = document.documentElement.classList.contains('dark')
          const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
          const textColor = isDark ? '#9ca3af' : '#6b7280'

          const commonScales = {
            x: {
              ticks: { color: textColor, maxTicksLimit: 6, font: { size: 11 } },
              grid: { color: gridColor },
            },
          }

          // Price chart
          const priceCtx = document.getElementById('priceChart')
          if (this.priceChart) this.priceChart.destroy()
          this.priceChart = new Chart(priceCtx, {
            type: 'line',
            data: {
              labels,
              datasets: [
                { label: 'Close', data: closes, borderColor: '#0ea5e9', borderWidth: 2, pointRadius: 0, tension: 0.3 },
                { label: 'EMA20', data: ema20, borderColor: '#f59e0b', borderWidth: 1.5, pointRadius: 0, tension: 0.3, borderDash: [] },
                { label: 'EMA50', data: ema50, borderColor: '#8b5cf6', borderWidth: 1.5, pointRadius: 0, tension: 0.3 },
                { label: 'EMA200', data: ema200, borderColor: '#ef4444', borderWidth: 1.5, pointRadius: 0, tension: 0.3 },
              ],
            },
            options: {
              responsive: true,
              interaction: { mode: 'index', intersect: false },
              plugins: { legend: { labels: { color: textColor, font: { size: 11 } } } },
              scales: {
                ...commonScales,
                y: { ticks: { color: textColor, font: { size: 11 } }, grid: { color: gridColor } },
              },
            },
          })

          // Volume chart
          const volCtx = document.getElementById('volumeChart')
          if (this.volumeChart) this.volumeChart.destroy()
          this.volumeChart = new Chart(volCtx, {
            type: 'bar',
            data: {
              labels,
              datasets: [{ label: 'Volume', data: volumes, backgroundColor: 'rgba(14,165,233,0.4)', borderRadius: 2 }],
            },
            options: {
              responsive: true,
              plugins: { legend: { display: false } },
              scales: {
                ...commonScales,
                y: { ticks: { color: textColor, font: { size: 11 }, callback: v => (v / 1e6).toFixed(1) + 'M' }, grid: { color: gridColor } },
              },
            },
          })
        })
    },

    trendClass(d) {
      const map = {
        'STRONG UPTREND':   'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
        'UPTREND':          'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
        'SIDEWAYS':         'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
        'DOWNTREND':        'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
        'STRONG DOWNTREND': 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
      }
      return map[d] ?? 'bg-gray-100 text-gray-500'
    },

    fmt(v) {
      if (v == null) return '-'
      return Number(v).toLocaleString('id-ID')
    },

    fmtDec(v) {
      if (v == null) return '-'
      return Number(v).toFixed(2)
    },

    fmtLot(v) {
      if (v == null) return '-'
      return Number(v).toLocaleString('id-ID') + ' lot'
    },
  }
}
