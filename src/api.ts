export type Market = 'US' | 'CN' | 'HK' | 'JP' | 'KR' | 'SG' | 'TW';
export type Verdict = 'buy' | 'watch' | 'sell';
export type SectorRecommendation = 'overweight' | 'neutral' | 'underweight';

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
  key:
    | 'strongestFactors'
    | 'sentimentImpact'
    | 'belowThreshold'
    | 'severePriceDrop'
    | 'weakPriceAction'
    | 'overheatedPriceAction'
    | 'pullbackRisk'
    | 'breakoutSetup'
    | 'clearsBuyThreshold'
    | 'notHighConviction'
    | 'rankedTopOpportunity';
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
    | 'breakoutSetup'
    | 'valuationSupport'
    | 'expensiveValuation'
    | 'watchValuation'
    | 'riskControlled'
    | 'riskHigh'
    | 'watchRisk'
    | 'priceActionSevereDrop'
    | 'priceActionWeak'
    | 'overheatedPriceAction'
    | 'pullbackRisk'
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
    | 'actionAvoidLimitDown'
    | 'actionWaitPriceStabilization'
    | 'actionWaitPullback'
    | 'actionRequireNewsEvidence'
    | 'tCandidateSummary'
    | 'tWatchSummary'
    | 'tAvoidSummary'
    | 'tLiquidityReady'
    | 'tLiquidityThin'
    | 'tVolatilityReady'
    | 'tVolatilityLow'
    | 'tSetupReady'
    | 'tTrendWeak'
    | 'tPullbackRiskHigh'
    | 'tDownsideRiskHigh'
    | 'tNoChase'
    | 'tUseBasePositionOnly'
    | 'tCutIfBreaksSupport';
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
  strength: number;
  score: number;
  evidence: string;
}

export interface NewsAnalysis {
  summary: DecisionPoint;
  positiveCount: number;
  negativeCount: number;
  positiveScore: number;
  negativeScore: number;
  netScore: number;
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

export type HoldingAction = 'add' | 'hold' | 'reduce' | 'exit';
export type HoldingNoteSeverity = 'info' | 'warning' | 'danger';

export interface HoldingPosition {
  symbol: string;
  code: string;
  name: string;
  market: Market;
  exchange?: string;
  quantity: number;
  availableQuantity?: number | null;
  frozenQuantity?: number | null;
  costPrice?: number | null;
  lastPrice?: number | null;
  marketValue?: number | null;
  costAmount?: number | null;
  unrealizedPnl?: number | null;
  unrealizedPnlPct?: number | null;
  openDate?: string | null;
}

export interface HoldingNote {
  key: string;
  severity: HoldingNoteSeverity;
  params: Record<string, string | number>;
}

export interface HoldingAnalysis {
  action: HoldingAction;
  positionWeightPct: number;
  notes: HoldingNote[];
}

export interface PortfolioImportResponse {
  sourceName: string;
  sourceType: string;
  importedAt: string;
  positions: HoldingPosition[];
  symbols: string[];
  recognizedCount: number;
  ignoredRows: number;
  totalMarketValue: number;
  totalCostAmount: number;
  totalUnrealizedPnl: number;
  totalUnrealizedPnlPct?: number | null;
  warnings: HoldingNote[];
}

export interface PortfolioAnalysis extends PortfolioImportResponse {
  matchedCount: number;
  unmatchedSymbols: string[];
}

export type TTradeSuitability = 'candidate' | 'watch' | 'avoid';

export interface PriceZone {
  low: number;
  high: number;
}

export interface TTradePlan {
  suitability: TTradeSuitability;
  summary: DecisionPoint;
  score: number;
  components: {
    liquidityScore: number;
    volatilityScore: number;
    volatilityPct: number;
    turnoverScore: number;
    turnoverPct?: number | null;
  };
  entryZone: PriceZone;
  takeProfitZone: PriceZone;
  stopLoss: number;
  reasons: DecisionPoint[];
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
  opportunityScore?: number;
  downsideRiskScore?: number;
  breakoutSetupScore?: number;
  pullbackRiskScore?: number;
  tScore?: number;
  tPlan?: TTradePlan;
  prediction?: {
    opportunityScore: number;
    downsideRiskScore: number;
    breakoutSetupScore?: number;
    pullbackRiskScore?: number;
    tScore?: number;
    edge: number;
  };
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
  holding?: HoldingPosition;
  holdingAnalysis?: HoldingAnalysis;
}

export interface SectorConstituent {
  symbol: string;
  name: string;
  market: Market;
  score: number;
  verdict: Verdict;
  tScore?: number;
  tSuitability?: TTradeSuitability;
}

export interface SectorAnalysis {
  id: string;
  name: string;
  score: number;
  recommendation: SectorRecommendation;
  confidence: number;
  count: number;
  marketMix: Array<{ market: Market; count: number }>;
  verdictCounts: Record<Verdict, number>;
  tCandidateCount?: number;
  averageTScore?: number;
  averageOpportunityScore?: number;
  averageDownsideRiskScore?: number;
  metrics: StrategyWeights;
  leaders: SectorConstituent[];
  laggards: SectorConstituent[];
}

export interface AnalysisResponse {
  generatedAt: string;
  markets: MarketOption[];
  strategy: Strategy;
  picks: Pick[];
  sectors: SectorAnalysis[];
  errors: Array<{ symbol: string; error: string }>;
  portfolio?: PortfolioAnalysis;
  scan?: {
    auto: boolean;
    source: string;
    requested: number;
    succeeded: number;
    displayed?: number;
    actionable?: number;
    qualityBuys?: number;
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
      portfolio?: PortfolioAnalysis | null;
      scan: AnalysisScan;
    }
  | {
      type: 'pick';
      pick: Pick;
      picks?: Pick[];
      sectors?: SectorAnalysis[];
      portfolio?: PortfolioAnalysis | null;
      rank: number;
      scan: AnalysisScan;
    }
  | {
      type: 'error';
      symbol: string;
      error: string;
      sectors?: SectorAnalysis[];
      portfolio?: PortfolioAnalysis | null;
      scan: AnalysisScan;
    }
  | AnalysisResponse & {
      type: 'complete';
      scan: AnalysisScan;
    };

const headers = { 'Content-Type': 'application/json' };
let usingStaticFallback = false;
const staticDemoBuild = import.meta.env.PROD && import.meta.env.BASE_URL === '/stock-picker/';

export function currentDataMode(): 'demo' | 'live' {
  return staticDemoBuild || usingStaticFallback ? 'demo' : 'live';
}

function hasContentType(response: Response, expected: string) {
  return response.headers.get('content-type')?.toLowerCase().includes(expected) ?? false;
}

const fallbackConfig: AppConfig = {
  markets: [
    { id: 'CN', label: 'China A-shares', currency: 'CNY' },
    { id: 'HK', label: 'Hong Kong', currency: 'HKD' },
    { id: 'JP', label: 'Japan', currency: 'JPY' },
    { id: 'KR', label: 'South Korea', currency: 'KRW' },
    { id: 'SG', label: 'Singapore', currency: 'SGD' },
    { id: 'US', label: 'United States', currency: 'USD' },
    { id: 'TW', label: 'Taiwan', currency: 'TWD' }
  ],
  strategies: [
    {
      id: 'balanced',
      name: 'Balanced AI Core',
      description: 'News-led strategy balancing market sentiment with trend, valuation, risk, and quality.',
      weights: { momentum: 20, value: 15, sentiment: 40, risk: 10, quality: 15 },
      riskTolerance: 55
    },
    {
      id: 'growth',
      name: 'Growth Momentum',
      description: 'Favors accelerating revenue narratives, price momentum, and positive institutional coverage.',
      weights: { momentum: 30, value: 8, sentiment: 38, risk: 8, quality: 16 },
      riskTolerance: 68
    },
    {
      id: 'defensive',
      name: 'Defensive Value',
      description: 'Favors lower drawdown, strong cash flow, cheaper valuation, and stable signal quality.',
      weights: { momentum: 10, value: 24, sentiment: 30, risk: 22, quality: 14 },
      riskTolerance: 38
    }
  ],
  defaultSymbols: {
    US: ['AAPL', 'MSFT', 'NVDA'],
    CN: ['600519.SS', '300750.SZ'],
    HK: ['0700.HK', '9988.HK'],
    JP: ['7203.T', '6758.T'],
    KR: ['005930.KS', '000660.KS'],
    SG: ['D05.SI', 'C38U.SI'],
    TW: ['2330.TW', '2317.TW']
  },
  scanUniverseSize: {
    CN: 'dynamic',
    HK: 'dynamic',
    JP: 'dynamic',
    KR: 'dynamic',
    SG: 'dynamic',
    US: 'dynamic',
    TW: 'dynamic'
  }
};

function fallbackStrategy(payload: { strategyId?: string; customWeights?: StrategyWeights }) {
  if (payload.customWeights) {
    return {
      id: 'custom',
      name: 'Custom AI Strategy',
      description: 'User-defined scoring weights from the web interface.',
      weights: payload.customWeights,
      riskTolerance: 55
    };
  }
  return fallbackConfig.strategies.find((strategy) => strategy.id === payload.strategyId) ?? fallbackConfig.strategies[0];
}

function fallbackAnalysis(payload: { markets: Market[]; strategyId?: string; customWeights?: StrategyWeights }): AnalysisResponse {
  const markets: Market[] = payload.markets.length ? payload.markets : ['US', 'CN', 'HK', 'JP', 'KR', 'SG', 'TW'];
  const strategy = fallbackStrategy(payload);
  const demoPicks: Pick[] = [
    {
      symbol: '2330.TW',
      name: 'Taiwan Semiconductor Manufacturing',
      market: 'TW',
      sector: 'Technology',
      price: 865,
      change: 1.8,
      currency: 'TWD',
      score: 86,
      opportunityScore: 82,
      downsideRiskScore: 24,
      breakoutSetupScore: 78,
      pullbackRiskScore: 28,
      tScore: 74,
      tPlan: {
        suitability: 'candidate',
        summary: { key: 'tCandidateSummary', params: { score: 74 } },
        score: 74,
        components: { liquidityScore: 82, volatilityScore: 71, volatilityPct: 4.2, turnoverScore: 76, turnoverPct: 5.8 },
        entryZone: { low: 852.5, high: 861.4 },
        takeProfitZone: { low: 876.1, high: 891.2 },
        stopLoss: 842.5,
        reasons: [
          { key: 'tLiquidityReady', params: { score: 82 } },
          { key: 'tVolatilityReady', params: { score: 71, range: 4.2 } },
          { key: 'tSetupReady', params: { score: 78 } }
        ],
        riskControls: [
          { key: 'tUseBasePositionOnly', params: {} },
          { key: 'tCutIfBreaksSupport', params: {} }
        ]
      },
      verdict: 'buy',
      confidence: 82,
      reasons: ['Demo mode: quality, momentum, and fresh news signals are supportive.'],
      reasonCodes: [
        { key: 'strongestFactors', params: { first: 'quality', second: 'sentiment' } },
        { key: 'clearsBuyThreshold', params: {} }
      ],
      prediction: {
        opportunityScore: 82,
        downsideRiskScore: 24,
        breakoutSetupScore: 78,
        pullbackRiskScore: 28,
        tScore: 74,
        edge: 58
      },
      signals: [
        {
          source: 'Static demo',
          title: 'Chip demand and AI infrastructure spending remain supportive',
          summary: 'This is a GitHub Pages preview sample; connect the Python API for live crawling.',
          link: 'https://github.com/tamyu321-source/stock-picker',
          sentiment: 0.72,
          credibility: 0.9,
          relevance: 0.92,
          ageHours: 2
        }
      ],
      metrics: { momentum: 82, value: 68, sentiment: 88, risk: 74, quality: 92 },
      scoreBreakdown: [
        { factor: 'momentum', score: 82, weight: 20, contribution: 16.4 },
        { factor: 'value', score: 68, weight: 15, contribution: 10.2 },
        { factor: 'sentiment', score: 88, weight: 40, contribution: 35.2 },
        { factor: 'risk', score: 74, weight: 10, contribution: 7.4 },
        { factor: 'quality', score: 92, weight: 15, contribution: 13.8 }
      ],
      decision: {
        summary: { key: 'buySummary', params: { score: 86 } },
        positives: [
          { key: 'qualitySupport', params: { score: 92 } },
          { key: 'newsBullishSummary', params: { positiveScore: 88, negativeScore: 12, netScore: 76, total: 1 } }
        ],
        negatives: [],
        watchItems: [{ key: 'watchValuation', params: {} }]
      },
      newsAnalysis: {
        summary: { key: 'newsBullishSummary', params: { positiveScore: 88, negativeScore: 12, netScore: 76, total: 1 } },
        positiveCount: 1,
        negativeCount: 0,
        positiveScore: 88,
        negativeScore: 12,
        netScore: 76,
        events: [
          {
            key: 'demandPositive',
            impact: 'positive',
            title: 'Static demo signal: AI infrastructure demand remains supportive',
            source: 'Static demo',
            ageHours: 2,
            weight: 0.82,
            strength: 0.72,
            score: 31,
            evidence: 'GitHub Pages preview sample'
          }
        ]
      },
      financialAnalysis: {
        summary: { key: 'financialStrongSummary', params: { count: 4 } },
        metrics: [
          { key: 'forwardPE', value: '22.4', score: 68 },
          { key: 'profitMargins', value: '43.0%', score: 90 },
          { key: 'revenueGrowth', value: '28.0%', score: 86 },
          { key: 'debtToEquity', value: '24.0', score: 78 }
        ],
        positives: [{ key: 'financialProfitabilitySupport', params: { score: 90 } }],
        negatives: [],
        watchItems: [{ key: 'financialWatchHighRange', params: { position: 72 } }]
      },
      actionPlan: {
        summary: { key: 'actionAccumulate', params: { score: 86 } },
        steps: [{ key: 'actionBuyInBatches', params: {} }],
        watchItems: [{ key: 'actionWatchNewsCatalyst', params: {} }],
        riskControls: [{ key: 'actionRespectRisk', params: { risk: 74 } }]
      }
    },
    {
      symbol: 'AAPL',
      name: 'Apple',
      market: 'US',
      sector: 'Consumer Technology',
      price: 192.4,
      change: -0.4,
      currency: 'USD',
      score: 64,
      opportunityScore: 52,
      downsideRiskScore: 44,
      breakoutSetupScore: 42,
      pullbackRiskScore: 36,
      tScore: 48,
      tPlan: {
        suitability: 'avoid',
        summary: { key: 'tAvoidSummary', params: { score: 48 } },
        score: 48,
        components: { liquidityScore: 74, volatilityScore: 36, volatilityPct: 1.4, turnoverScore: 48, turnoverPct: null },
        entryZone: { low: 189.1, high: 191.6 },
        takeProfitZone: { low: 194.8, high: 197.4 },
        stopLoss: 187.8,
        reasons: [{ key: 'tLiquidityReady', params: { score: 74 } }],
        riskControls: [
          { key: 'tVolatilityLow', params: { range: 1.4 } },
          { key: 'tUseBasePositionOnly', params: {} }
        ]
      },
      verdict: 'watch',
      confidence: 61,
      reasons: ['Demo mode: quality remains strong, but momentum confirmation is still pending.'],
      reasonCodes: [{ key: 'belowThreshold', params: { factor: 'momentum' } }],
      prediction: {
        opportunityScore: 52,
        downsideRiskScore: 44,
        breakoutSetupScore: 42,
        pullbackRiskScore: 36,
        tScore: 48,
        edge: 8
      },
      signals: [],
      metrics: { momentum: 52, value: 58, sentiment: 62, risk: 70, quality: 84 },
      scoreBreakdown: [
        { factor: 'momentum', score: 52, weight: 20, contribution: 10.4 },
        { factor: 'value', score: 58, weight: 15, contribution: 8.7 },
        { factor: 'sentiment', score: 62, weight: 40, contribution: 24.8 },
        { factor: 'risk', score: 70, weight: 10, contribution: 7 },
        { factor: 'quality', score: 84, weight: 15, contribution: 12.6 }
      ],
      decision: {
        summary: { key: 'watchSummary', params: { score: 64 } },
        positives: [{ key: 'qualitySupport', params: { score: 84 } }],
        negatives: [{ key: 'weakMomentum', params: { score: 52 } }],
        watchItems: [{ key: 'watchBreakout', params: {} }]
      }
    }
  ];
  const picks = demoPicks.filter((pick) => markets.includes(pick.market));
  const scan: AnalysisScan = {
    auto: true,
    source: 'static-github-pages-demo',
    requested: markets.length,
    succeeded: picks.length,
    displayed: picks.length,
    failed: 0,
    discoveryErrors: []
  };
  return {
    generatedAt: new Date().toISOString(),
    markets: fallbackConfig.markets,
    strategy,
    picks,
    sectors: [
      {
        id: 'technology',
        name: 'Technology',
        score: 78,
        recommendation: 'overweight',
        confidence: 74,
        count: picks.length,
        marketMix: markets.map((market) => ({ market, count: picks.filter((pick) => pick.market === market).length })).filter((item) => item.count > 0),
        verdictCounts: {
          buy: picks.filter((pick) => pick.verdict === 'buy').length,
          watch: picks.filter((pick) => pick.verdict === 'watch').length,
          sell: picks.filter((pick) => pick.verdict === 'sell').length
        },
        tCandidateCount: picks.filter((pick) => pick.tPlan?.suitability === 'candidate').length,
        averageTScore: Math.round((picks.reduce((total, pick) => total + Number(pick.tScore ?? 0), 0) / Math.max(1, picks.length)) * 10) / 10,
        averageOpportunityScore: Math.round((picks.reduce((total, pick) => total + Number(pick.opportunityScore ?? 0), 0) / Math.max(1, picks.length)) * 10) / 10,
        averageDownsideRiskScore: Math.round((picks.reduce((total, pick) => total + Number(pick.downsideRiskScore ?? 0), 0) / Math.max(1, picks.length)) * 10) / 10,
        metrics: { momentum: 67, value: 63, sentiment: 75, risk: 72, quality: 88 },
        leaders: picks.slice(0, 1).map((pick) => ({ symbol: pick.symbol, name: pick.name, market: pick.market, score: pick.score, verdict: pick.verdict, tScore: pick.tScore, tSuitability: pick.tPlan?.suitability })),
        laggards: picks.slice(1, 2).map((pick) => ({ symbol: pick.symbol, name: pick.name, market: pick.market, score: pick.score, verdict: pick.verdict, tScore: pick.tScore, tSuitability: pick.tPlan?.suitability }))
      }
    ],
    errors: [],
    scan
  };
}

export async function fetchConfig(): Promise<AppConfig> {
  if (staticDemoBuild) {
    usingStaticFallback = true;
    return fallbackConfig;
  }
  try {
    const response = await fetch('/api/config');
    if (!response.ok) throw new Error('Failed to load config');
    if (!hasContentType(response, 'application/json')) throw new Error('Static preview fallback');
    return response.json();
  } catch {
    usingStaticFallback = true;
    return fallbackConfig;
  }
}

export async function analyzeStocks(payload: {
  markets: Market[];
  symbols?: string[];
  strategyId?: string;
  customWeights?: StrategyWeights;
  refresh?: boolean;
  portfolio?: PortfolioImportResponse | PortfolioAnalysis;
}): Promise<AnalysisResponse> {
  if (staticDemoBuild || usingStaticFallback) {
    return fallbackAnalysis(payload);
  }
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error('Failed to analyze stocks');
    if (!hasContentType(response, 'application/json')) throw new Error('Static preview fallback');
    return response.json();
  } catch {
    usingStaticFallback = true;
    return fallbackAnalysis(payload);
  }
}

export async function analyzeStocksStream(
  payload: {
    markets: Market[];
    symbols?: string[];
    strategyId?: string;
    customWeights?: StrategyWeights;
    refresh?: boolean;
    portfolio?: PortfolioImportResponse | PortfolioAnalysis;
  },
  onEvent: (event: AnalysisStreamEvent) => void,
  options: { signal?: AbortSignal } = {}
): Promise<AnalysisResponse> {
  const ensureNotAborted = () => {
    if (!options.signal?.aborted) return;
    const error = new Error('Analysis cancelled');
    error.name = 'AbortError';
    throw error;
  };

  ensureNotAborted();
  if (staticDemoBuild || usingStaticFallback) {
    const result = fallbackAnalysis(payload);
    onEvent({ type: 'started', generatedAt: result.generatedAt, markets: result.markets, strategy: result.strategy, scan: result.scan as AnalysisScan });
    result.picks.forEach((pick, index) => {
      ensureNotAborted();
      onEvent({ type: 'pick', pick, picks: result.picks.slice(0, index + 1), sectors: result.sectors, rank: index + 1, scan: result.scan as AnalysisScan });
    });
    ensureNotAborted();
    onEvent({ type: 'complete', ...result, scan: result.scan as AnalysisScan });
    return result;
  }
  let response: Response;
  try {
    response = await fetch('/api/analyze/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: options.signal
    });
    if (!response.ok) throw new Error('Failed to analyze stocks');
    if (!hasContentType(response, 'application/x-ndjson')) throw new Error('Static preview fallback');
  } catch (cause) {
    if (cause instanceof Error && cause.name === 'AbortError') throw cause;
    usingStaticFallback = true;
    ensureNotAborted();
    const result = fallbackAnalysis(payload);
    onEvent({ type: 'started', generatedAt: result.generatedAt, markets: result.markets, strategy: result.strategy, scan: result.scan as AnalysisScan });
    result.picks.forEach((pick, index) => {
      ensureNotAborted();
      onEvent({ type: 'pick', pick, picks: result.picks.slice(0, index + 1), sectors: result.sectors, rank: index + 1, scan: result.scan as AnalysisScan });
    });
    ensureNotAborted();
    onEvent({ type: 'complete', ...result, scan: result.scan as AnalysisScan });
    return result;
  }
  if (!response.body) {
    ensureNotAborted();
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
    ensureNotAborted();
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

export async function importPortfolioFile(file: File): Promise<PortfolioImportResponse> {
  if (staticDemoBuild || usingStaticFallback) {
    throw new Error('Holdings import requires the live Python backend.');
  }
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch('/api/portfolio/import', {
    method: 'POST',
    body: formData
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.error || 'Failed to import holdings file');
  }
  if (!hasContentType(response, 'application/json')) throw new Error('Holdings import requires the live Python backend.');
  return response.json();
}
