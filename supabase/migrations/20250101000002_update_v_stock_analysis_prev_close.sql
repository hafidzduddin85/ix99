-- Migration: add prev_close to v_stock_analysis
-- Menggunakan LAG(close) dari stock_daily untuk menghitung perubahan harga harian.

CREATE OR REPLACE VIEW public.v_stock_analysis AS
SELECT
  s.id                    AS stock_id,
  s.ticker,
  s.company_name,
  s.sector,
  s.subsector,
  s.is_active,
  ti.trade_date,
  ti.close,
  -- prev_close: harga penutupan hari sebelumnya dari stock_daily
  (
    SELECT sd_prev.close
    FROM public.stock_daily sd_prev
    WHERE sd_prev.stock_id = s.id
      AND sd_prev.trade_date < ti.trade_date
    ORDER BY sd_prev.trade_date DESC
    LIMIT 1
  )                       AS prev_close,
  ti.ema20,
  ti.ema50,
  ti.ema200,
  ti.rsi14,
  ti.adx14,
  ti.plus_di,
  ti.minus_di,
  ti.atr14,
  ti.avg_volume20,
  ti.volume_ratio,
  ti.higher_high,
  ti.higher_low,
  ti.lower_high,
  ti.lower_low,
  ts.trend_direction,
  ts.trend_score,
  ts.trend_strength,
  ts.ema_signal,
  ts.adx_signal,
  ts.momentum_signal,
  ts.volume_signal,
  ts.structure_signal,
  ts.entry_signal
FROM public.stocks s
JOIN public.technical_indicators ti
  ON ti.stock_id = s.id
JOIN public.trend_signals ts
  ON ts.stock_id = s.id
 AND ts.signal_date = ti.trade_date
WHERE (ti.trade_date, ti.stock_id) IN (
  SELECT MAX(trade_date), stock_id
  FROM public.technical_indicators
  GROUP BY stock_id
);
