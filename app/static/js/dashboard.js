function dashboard() {
  return {
    stocks: [],
    filtered: [],
    summary: {},
    sectors: [],
    loading: true,
    activeDirection: null,
    selectedTicker: null,
    panel: null,
    panelLoading: false,

    filters: {
      search: '',
      sector: '',
      minScore: '',
      minAdx: '',
      minVolRatio: '',
      entryOnly: false,
      watchlistOnly: false,
    },

    summaryList: [
      { key: 'STRONG UPTREND',   label: 'Strong Uptrend',   bg: 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800',   text: 'text-green-700 dark:text-green-400' },
      { key: 'UPTREND',          label: 'Uptrend',          bg: 'bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800', text: 'text-emerald-700 dark:text-emerald-400' },
      { key: 'SIDEWAYS',         label: 'Sideways',         bg: 'bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800', text: 'text-yellow-700 dark:text-yellow-400' },
      { key: 'DOWNTREND',        label: 'Downtrend',        bg: 'bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800', text: 'text-orange-700 dark:text-orange-400' },
      { key: 'STRONG DOWNTREND', label: 'Strong Downtrend', bg: 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800',           text: 'text-red-700 dark:text-red-400' },
    ],

    async init() {
      await this.fetchDashboard()
    },

    async fetchDashboard() {
      this.loading = true
      try {
        const params = new URLSearchParams({ active_only: true })
        if (this.filters.watchlistOnly) params.set('watchlist_only', true)
        const res = await fetch(`/api/dashboard?${params}`)
        const json = await res.json()
        this.stocks = json.stocks ?? []
        this.summary = json.summary ?? {}
        this.sectors = [...new Set(this.stocks.map(s => s.sector).filter(Boolean))].sort()
        this.applyFilters()
      } finally {
        this.loading = false
      }
    },

    applyFilters() {
      let data = [...this.stocks]
      if (this.activeDirection) data = data.filter(s => s.trend_direction === this.activeDirection)
      if (this.filters.search) {
        const q = this.filters.search.toUpperCase()
        data = data.filter(s => s.ticker?.includes(q) || s.company_name?.toUpperCase().includes(q))
      }
      if (this.filters.sector) data = data.filter(s => s.sector === this.filters.sector)
      if (this.filters.minScore !== '') data = data.filter(s => (s.trend_score ?? 0) >= Number(this.filters.minScore))
      if (this.filters.minAdx !== '') data = data.filter(s => (s.adx14 ?? 0) >= Number(this.filters.minAdx))
      if (this.filters.minVolRatio !== '') data = data.filter(s => (s.volume_ratio ?? 0) >= Number(this.filters.minVolRatio))
      if (this.filters.entryOnly) data = data.filter(s => s.entry_signal === true)
      this.filtered = data
    },

    toggleDirection(key) {
      this.activeDirection = this.activeDirection === key ? null : key
      this.applyFilters()
    },

    async openPanel(ticker) {
      this.selectedTicker = ticker
      this.panel = null
      this.panelLoading = true
      try {
        const [detailRes, brokerRes] = await Promise.all([
          fetch(`/api/detail/${ticker}`),
          fetch(`/api/broker/${ticker}/flow?days=30`),
        ])
        const detail = await detailRes.json()
        const broker = await brokerRes.json()
        this.panel = { ...detail.stock, ...detail.analysis, broker }
      } catch (_) {}
      this.panelLoading = false
    },

    closePanel() {
      this.selectedTicker = null
      this.panel = null
    },

    scoreBarWidth(val, max) {
      if (val == null || max === 0) return '0%'
      return Math.max(0, Math.min(100, (val / max) * 100)) + '%'
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

    trendLabel(d) {
      const map = {
        'STRONG UPTREND':   '↑↑ Strong Up',
        'UPTREND':          '↑ Uptrend',
        'SIDEWAYS':         '→ Sideways',
        'DOWNTREND':        '↓ Downtrend',
        'STRONG DOWNTREND': '↓↓ Strong Down',
      }
      return map[d] ?? d ?? '-'
    },

    rsiColor(v) {
      if (v == null) return 'text-gray-400'
      if (v >= 70) return 'text-red-500'
      if (v >= 50) return 'text-green-500'
      if (v <= 30) return 'text-blue-400'
      return 'text-yellow-500'
    },

    adxStrength(v) {
      if (v == null) return ''
      if (v >= 25) return 'Kuat'
      if (v >= 20) return 'Moderat'
      return 'Lemah'
    },

    fmt(v) {
      if (v == null) return '-'
      return Number(v).toLocaleString('id-ID')
    },

    fmtDec(v, d = 2) {
      if (v == null) return '-'
      return Number(v).toFixed(d)
    },

    fmtLot(v) {
      if (v == null) return '-'
      const n = Number(v)
      return (n >= 0 ? '+' : '') + n.toLocaleString('id-ID') + ' lot'
    },
  }
}
