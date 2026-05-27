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

export interface ScoreComponent {
  factor: keyof StrategyWeights;
  score: number;
  weight: number;
  baseWeight?: number;
  available?: boolean;
  contribution: number;
}

export interface DecisionPoint {
  key:
    | 'buySummary'
    | 'watchSummary'
    | 'sellSummary'
    | 'newsSupport'
    | 'newsPressure'
    | 'insufficientNews'
    | 'freshNews'
    | 'momentumSupport'
    | 'weakMomentum'
    | 'watchBreakout'
    | 'valuationSupport'
    | 'expensiveValuation'
    | 'watchValuation'
    | 'riskControlled'
    | 'riskHigh'
    | 'watchRisk'
    | 'qualitySupport'
    | 'weakQuality'
    | 'watchNewsFlow'
    | 'newsBullishSummary'
    | 'newsBearishSummary'
    | 'newsMixedSummary'
    | 'newsNoEvidence'
    | 'financialStrongSummary'
    | 'financialWeakSummary'
    | 'financialMixedSummary'
    | 'financialDataMissing'
    | 'financialValuationReasonable'
    | 'financialValuationRich'
    | 'financialWatchValuation'
    | 'financialGrowthSupport'
    | 'financialGrowthWeak'
    | 'financialWatchNextReport'
    | 'financialProfitabilitySupport'
    | 'financialProfitabilityWeak'
    | 'financialDebtControlled'
    | 'financialDebtRisk'
    | 'financialLiquiditySupport'
    | 'financialLiquidityRisk'
    | 'financialAnalystUpside'
    | 'financialAnalystDownside'
    | 'financialDividendSupport'
    | 'financialWatchHighRange'
    | 'financialWatchLowRange'
    | 'actionAccumulate'
    | 'actionReduceOrExit'
    | 'actionWait'
    | 'actionBuyInBatches'
    | 'actionWaitNewsConfirmation'
    | 'actionUseSmallPosition'
    | 'actionReduceExposure'
    | 'actionDoNotAverageDown'
    | 'actionSetExitReview'
    | 'actionNoChase'
    | 'actionWatchNewsCatalyst'
    | 'actionWatchFinancialRepair'
    | 'actionWatchMomentumTurn'
    | 'actionRespectRisk'
    | 'actionRequireNewsEvidence';
  params: Record<string, string | number>;
}

export interface DecisionDetails {
  summary: DecisionPoint;
  positives: DecisionPoint[];
  negatives: DecisionPoint[];
  watchItems: DecisionPoint[];
}

export interface NewsEvent {
  key: string;
  impact: 'positive' | 'negative' | 'neutral';
  title: string;
  source: string;
  ageHours: number;
  weight: number;
}

export interface NewsAnalysis {
  summary: DecisionPoint;
  positiveCount: number;
  negativeCount: number;
  events: NewsEvent[];
}

export interface FinancialMetric {
  key: string;
  value: string;
  score: number;
}

export interface FinancialAnalysis {
  summary: DecisionPoint;
  metrics: FinancialMetric[];
  positives: DecisionPoint[];
  negatives: DecisionPoint[];
  watchItems: DecisionPoint[];
}

export interface ActionPlan {
  summary: DecisionPoint;
  steps: DecisionPoint[];
  watchItems: DecisionPoint[];
  riskControls: DecisionPoint[];
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
  scoreBreakdown?: ScoreComponent[];
  decision?: DecisionDetails;
  newsAnalysis?: NewsAnalysis;
  financialAnalysis?: FinancialAnalysis;
  actionPlan?: ActionPlan;
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
    discoveryErrors: Array<{ market: string; source?: string; query?: string; error: string }>;
  };
}

export interface AppConfig {
  markets: MarketOption[];
  strategies: Strategy[];
  defaultSymbols: Record<Market, string[]>;
  scanUniverseSize: Record<Market, number | string>;
}

export type AnalysisScan = NonNullable<AnalysisResponse['scan']>;

export type AnalysisStreamEvent =
  | {
      type: 'started';
      generatedAt: string;
      markets: MarketOption[];
      strategy: Strategy;
      scan: AnalysisScan;
    }
  | {
      type: 'pick';
      pick: Pick;
      rank: number;
      scan: AnalysisScan;
    }
  | {
      type: 'error';
      symbol: string;
      error: string;
      scan: AnalysisScan;
    }
  | AnalysisResponse & {
      type: 'complete';
      scan: AnalysisScan;
    };

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

export async function analyzeStocksStream(
  payload: {
    markets: Market[];
    symbols?: string[];
    strategyId?: string;
    customWeights?: StrategyWeights;
  },
  onEvent: (event: AnalysisStreamEvent) => void
): Promise<AnalysisResponse> {
  const response = await fetch('/api/analyze/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error('Failed to analyze stocks');
  if (!response.body) {
    const result = await analyzeStocks(payload);
    onEvent({ type: 'complete', ...result, scan: result.scan as AnalysisScan });
    return result;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResult: AnalysisResponse | null = null;

  const consumeLine = (line: string) => {
    if (!line.trim()) return;
    const event = JSON.parse(line) as AnalysisStreamEvent;
    onEvent(event);
    if (event.type === 'complete') {
      finalResult = event;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    lines.forEach(consumeLine);
  }

  buffer += decoder.decode();
  consumeLine(buffer);
  if (!finalResult) throw new Error('Analysis stream ended before completion');
  return finalResult;
}
