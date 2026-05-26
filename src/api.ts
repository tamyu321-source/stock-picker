export type Market = 'US' | 'CN' | 'HK' | 'SG' | 'TW';
export type Verdict = 'buy' | 'watch' | 'sell';

export interface StrategyWeights {
  momentum: number;
  value: number;
  sentiment: number;
  risk: number;
  quality: number;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  weights: StrategyWeights;
  riskTolerance: number;
}

export interface MarketOption {
  id: Market;
  label: string;
  currency: string;
}

export interface Signal {
  source: string;
  title: string;
  summary: string;
  link: string;
  sentiment: number;
  credibility: number;
  relevance: number;
  ageHours: number;
}

export interface ReasonCode {
  key: 'strongestFactors' | 'sentimentImpact' | 'belowThreshold' | 'clearsBuyThreshold' | 'notHighConviction' | 'rankedTopOpportunity';
  params: Record<string, string | number>;
}

export interface Pick {
  symbol: string;
  name: string;
  market: Market;
  sector: string;
  price: number;
  change: number;
  currency: string;
  score: number;
  verdict: Verdict;
  confidence: number;
  reasons: string[];
  reasonCodes?: ReasonCode[];
  signals: Signal[];
  metrics: StrategyWeights;
}

export interface AnalysisResponse {
  generatedAt: string;
  markets: MarketOption[];
  strategy: Strategy;
  picks: Pick[];
  errors: Array<{ symbol: string; error: string }>;
  scan?: {
    auto: boolean;
    source: string;
    requested: number;
    succeeded: number;
    failed: number;
    discoveryErrors: Array<{ market: string; query: string; error: string }>;
  };
}

export interface AppConfig {
  markets: MarketOption[];
  strategies: Strategy[];
  defaultSymbols: Record<Market, string[]>;
  scanUniverseSize: Record<Market, number | string>;
}

const headers = { 'Content-Type': 'application/json' };

export async function fetchConfig(): Promise<AppConfig> {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('Failed to load config');
  return response.json();
}

export async function analyzeStocks(payload: {
  markets: Market[];
  symbols?: string[];
  strategyId?: string;
  customWeights?: StrategyWeights;
}): Promise<AnalysisResponse> {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error('Failed to analyze stocks');
  return response.json();
}
