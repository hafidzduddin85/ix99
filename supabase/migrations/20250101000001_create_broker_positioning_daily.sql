-- Migration: create broker_positioning_daily
-- Tabel historical broker positioning, tidak boleh dihapus saat pipeline refresh.
-- UPSERT berdasarkan (trade_date, ticker, broker_code).

CREATE TABLE IF NOT EXISTS public.broker_positioning_daily (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  trade_date date NOT NULL,
  ticker character varying NOT NULL,
  broker_code character varying NOT NULL,
  buy_volume bigint DEFAULT 0,
  buy_value numeric DEFAULT 0,
  buy_avg numeric,
  sell_volume bigint DEFAULT 0,
  sell_value numeric DEFAULT 0,
  sell_avg numeric,
  net_volume bigint,
  net_value numeric,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT broker_positioning_daily_pkey PRIMARY KEY (id),
  CONSTRAINT broker_positioning_daily_unique UNIQUE (trade_date, ticker, broker_code)
);

CREATE INDEX IF NOT EXISTS idx_broker_positioning_daily_ticker_date
  ON public.broker_positioning_daily (ticker, trade_date DESC);

CREATE INDEX IF NOT EXISTS idx_broker_positioning_daily_date
  ON public.broker_positioning_daily (trade_date DESC);
