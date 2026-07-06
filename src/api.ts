export type Market = 'US' | 'CN' | 'HK' | 'JP' | 'KR' | 'SG' | 'TW';
export type Verdict = 'buy' | 'watch' | 'sell';
export type SectorRecommendation = 'overweight' | 'neutral' | 'underweight';
export type InstrumentType = 'stock' | 'etf' | string;
export type DisplayMode = 'simple' | 'professional';

export interface StrategyWeights {
  momentum: number;
  value: number;
  sentiment: number;
  risk: number;
  quality: number;
}

export type DetailedStrategyWeights = Record<string, number>;

export interface StrategyRuleConfig {
  key: string;
  metric: string;
  min?: number;
  max?: number;
  cap?: number;
  direction?: string;
}

export interface StrategyBehavior {
  mode: string;
  buyFloor?: number;
  watchFloor?: number;
  entryGates?: StrategyRuleConfig[];
  vetoRules?: StrategyRuleConfig[];
  fitWeights?: Record<string, number>;
  sortWeights?: Record<string, number>;
  focusKeys?: string[];
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  weights: StrategyWeights;
  riskTolerance: number;
  sourceStrategyIds?: string[];
  detailedWeights?: DetailedStrategyWeights;
  behavior?: StrategyBehavior;
}

export interface StrategySource {
  id: string;
  title: string;
  url: string;
  urls?: string[];
  families?: string[];
  timeHorizon?: string;
  keywords?: string[];
  available?: boolean | null;
  usable?: boolean;
  fallback?: boolean;
  status?: string;
  matchedKeywords?: string[];
  error?: string;
}

export interface StrategyLibrary {
  refreshedAt: string;
  sources: StrategySource[];
  strategies: Strategy[];
  runtimeStrategies?: Strategy[];
  detailedWeightKeys: string[];
  detailedWeightLabels: Record<string, string>;
}

export interface MarketOption {
  id: Market;
  label: string;
  currency: string;
}

export interface MarketDataSource {
  id: string;
  label: string;
  kind: string;
  role: string;
  official?: boolean;
  licensed?: boolean;
}

export interface MarketProfile {
  market: Market | string;
  coverageTier: 'local-deep' | 'regional' | 'global' | 'basic' | string;
  sourceReliabilityScore: number;
  localPriority: boolean;
  preferred?: boolean;
  focusRank?: number;
  primarySources: MarketDataSource[];
  capabilities: Record<string, boolean>;
  limitations: string[];
  professionalAnchors?: string[];
}

export interface MarketRuleProfile {
  version: string;
  market: Market | string;
  ruleDepth: 'deep' | 'basic' | string;
  timezone: string;
  currency: string;
  sessionWindows: Array<{ label: string; start: string; end: string }>;
  lunchBreak?: { start: string; end: string } | null;
  openingConfirmationMinutes: number;
  settlement?: string | null;
  sellRule?: string | null;
  priceLimitPct?: number | null;
  enforcesBuySessionGate: boolean;
  nonRealtimeBuyPolicy: string;
  orderSizing?: MarketOrderSizing;
  etfRiskPolicy: string;
  sources: string[];
}

export interface MarketOrderSizing {
  boardLotSize?: number | null;
  buyLotSize?: number | null;
  sellLotSize?: number | null;
  minBuyQuantity?: number | null;
  allowsOddLotBuy?: boolean;
  allowsOddLotSell?: boolean;
  oddLotPolicy?: string;
  normalization?: string;
  maxOrderQuantity?: number | null;
  source?: string;
}

export interface MarketRuleState {
  version: string;
  profile: MarketRuleProfile;
  market: Market | string;
  ruleDepth: 'deep' | 'basic' | string;
  status: 'regular' | 'opening_confirmation' | 'lunch_break' | 'closed' | 'unknown' | string;
  trading: boolean;
  openConfirmed: boolean;
  allowNewBuy: boolean;
  enforcedBuyGate: boolean;
  reason?: string;
  localTime?: string;
  dataFreshness: 'realtime' | 'delayed_or_fallback' | 'unknown' | string;
  priceSource?: string;
  settlement?: string | null;
  sellRule?: string | null;
  priceLimitPct?: number | null;
  orderSizing?: MarketOrderSizing;
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
    | 'nextSessionSupport'
    | 'nextSessionRisk'
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
    | 'fundFlowSupport'
    | 'fundFlowPressure'
    | 'fundFlowWatch'
    | 'newsHeatHotPositiveSummary'
    | 'newsHeatHotNegativeSummary'
    | 'newsHeatHotMixedSummary'
    | 'newsHeatColdSummary'
    | 'newsHeatSupport'
    | 'newsHeatRisk'
    | 'newsHeatWatch'
    | 'newsHeatFresh'
    | 'newsHeatStale'
    | 'overallStrongBuySummary'
    | 'overallBuySummary'
    | 'overallWatchSummary'
    | 'overallAvoidSummary'
    | 'overallSellSummary'
    | 'overallTodayBuySupport'
    | 'overallTodayBuyWeak'
    | 'overallTodayBuyWatch'
    | 'overallFutureRiseSupport'
    | 'overallFutureRiseWeak'
    | 'overallFutureRiseWatch'
    | 'overallProfitableExitSupport'
    | 'overallProfitableExitWeak'
    | 'overallProfitableExitWatch'
    | 'overallNewsHeatSupport'
    | 'overallNewsHeatRisk'
    | 'overallNewsHeatWatch'
    | 'overallRiskTooHigh'
    | 'trendBullishSummary'
    | 'trendConstructiveSummary'
    | 'trendNeutralSummary'
    | 'trendRiskSummary'
    | 'trendContinuationSupport'
    | 'trendContinuationWeak'
    | 'trendContinuationWatch'
    | 'trendStructureSupport'
    | 'trendStructureWeak'
    | 'trendRsiHealthy'
    | 'trendOverextended'
    | 'trendMacdSupport'
    | 'trendMacdPressure'
    | 'trendVolumeConfirm'
    | 'trendVolumeDivergence'
    | 'trendNearResistance'
    | 'trendNearSupport'
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

export interface NewsHeatAnalysis {
  summary: DecisionPoint;
  heatScore: number;
  impactScore: number;
  freshnessScore: number;
  sourceCount: number;
  eventIntensityScore: number;
  metrics: FinancialMetric[];
  positives: DecisionPoint[];
  negatives: DecisionPoint[];
  watchItems: DecisionPoint[];
}

export type TrendRegime = 'bullish' | 'constructive' | 'neutral' | 'fragile' | 'bearish' | 'overheated' | 'insufficient';

export interface TrendAnalysis {
  summary: DecisionPoint;
  regime: TrendRegime;
  continuationScore: number;
  reversalRiskScore: number;
  metrics: FinancialMetric[];
  positives: DecisionPoint[];
  negatives: DecisionPoint[];
  watchItems: DecisionPoint[];
  profile?: Record<string, string | number | null | boolean>;
}

export interface ActionPlan {
  summary: DecisionPoint;
  steps: DecisionPoint[];
  watchItems: DecisionPoint[];
  riskControls: DecisionPoint[];
}

export type OverallSuitability = 'strongBuy' | 'buy' | 'watch' | 'avoid' | 'sell';

export interface OverallAssessment {
  summary: DecisionPoint;
  suitability: OverallSuitability;
  totalScore: number;
  components: {
    todayBuyScore: number;
    futureRiseScore: number;
    profitableExitScore: number;
    newsHeatImpactScore: number;
  };
  componentWeights?: Record<string, number>;
  metrics: FinancialMetric[];
  positives: DecisionPoint[];
  negatives: DecisionPoint[];
  watchItems: DecisionPoint[];
}

export interface StrategyCheckResult {
  key: string;
  metric: string;
  actual: number;
  threshold: number;
  operator: string;
  passed?: boolean;
  triggered?: boolean;
  gap?: number;
  cap?: number | null;
}

export interface StrategyFocusResult {
  key: string;
  metric: string;
  score: number;
}

export interface StrategyAssessment {
  mode: string;
  fitScore: number;
  sortScore: number;
  baseScore: number;
  adjustedScore: number;
  horizons?: {
    shortTermScore: number;
    midLongTermScore: number;
    stabilityScore: number;
    qualityCompositeScore: number;
    scoreGap: number;
    classification: string;
    shortTermTradable: boolean;
    midLongInvestable: boolean;
  };
  recommendation: 'aligned' | 'watch' | 'avoid' | 'blocked' | string;
  failedGateCount: number;
  triggeredVetoCount: number;
  gates: StrategyCheckResult[];
  vetoes: StrategyCheckResult[];
  focus: StrategyFocusResult[];
}

export interface StockChartPoint {
  time: string;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close: number;
  volume?: number | null;
  ma5?: number | null;
  ma10?: number | null;
  ma20?: number | null;
  limitUpPrice?: number | null;
  isLimitUp?: boolean;
}

export interface StockChartResponse {
  symbol: string;
  name: string;
  currency: string;
  exchangeTimezoneName?: string;
  regularMarketPrice?: number | null;
  source: string;
  refreshedAt: string;
  intraday: StockChartPoint[];
  daily: StockChartPoint[];
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
  brokerLastPrice?: number | null;
  livePriceDriftPct?: number | null;
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
  targetWeightPct?: number;
  availableQuantity?: number;
  blockedQuantity?: number;
  plannedQuantityChange?: number;
  suggestedQuantityChange?: number;
  rawQuantityChange?: number;
  orderSizing?: MarketOrderSizing;
  executionStatus?: 'executable' | 'blocked_today' | 'partial_t1_locked' | string;
  stopLossPrice?: number | null;
  takeProfitPrice?: number | null;
  buyScore?: number;
  sellScore?: number;
  notes: HoldingNote[];
}

export interface HoldingActionItem {
  symbol: string;
  name: string;
  market?: Market | string;
  action: HoldingAction | string;
  bucket: 'risk_action' | 't1_locked' | 'sellable_today' | 'observe' | 'rebalance' | string;
  executionStatus: 'executable' | 'blocked_today' | 'partial_t1_locked' | string;
  plannedQuantityChange: number;
  executableQuantityChange: number;
  rawQuantityChange?: number | null;
  orderSizing?: MarketOrderSizing;
  availableQuantity?: number | null;
  blockedQuantity?: number | null;
  quantity?: number | null;
  costPrice?: number | null;
  lastPrice?: number | null;
  unrealizedPnl?: number | null;
  unrealizedPnlPct?: number | null;
  stopLossPrice?: number | null;
  takeProfitPrice?: number | null;
  finalAction?: string;
  tradableNow?: boolean;
  primaryNoteKeys?: string[];
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
  actionItems?: HoldingActionItem[];
}

export interface PortfolioAnalysis extends PortfolioImportResponse {
  matchedCount: number;
  unmatchedSymbols: string[];
}

export interface PortfolioMemoryDiff {
  added: number;
  removed: number;
  quantityChanged: number;
  costChanged: number;
  pnlChange?: number | null;
}

export interface PortfolioMemoryItem {
  id: string;
  savedAt: string;
  title: string;
  sourceName: string;
  sourceType: string;
  recognizedCount: number;
  symbols: string[];
  totalMarketValue: number;
  totalUnrealizedPnl: number;
  totalUnrealizedPnlPct?: number | null;
  diff?: PortfolioMemoryDiff | null;
  portfolio: PortfolioImportResponse | PortfolioAnalysis;
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

export interface FundFlowProfile {
  available: boolean;
  source?: string;
  score: number;
  positiveScore: number;
  negativeScore: number;
  mainNet?: number | null;
  mainRatio?: number | null;
  superLargeNet?: number | null;
  superLargeRatio?: number | null;
  largeNet?: number | null;
  largeRatio?: number | null;
  mediumNet?: number | null;
  mediumRatio?: number | null;
  smallNet?: number | null;
  smallRatio?: number | null;
}

export interface CompositeModel {
  instrumentType: InstrumentType;
  buyScore: number;
  sellScore: number;
  holdScore: number;
  rankScore: number;
  decision: 'accumulate' | 'hold' | 'reduce' | 'exit' | string;
  weights: Record<string, number>;
  financialScore?: number;
  newsFreshnessScore?: number;
}

export interface ProfessionalFactorExposure {
  key: string;
  label: string;
  score: number;
  tone: string;
}

export interface ProfessionalFactorModel {
  version: string;
  style: string;
  exposures: ProfessionalFactorExposure[];
  dominantExposures: string[];
  coverageScore: number;
  financialScore: number;
}

export interface BenchmarkRelativeScore {
  benchmark: {
    market: Market | string;
    symbol: string;
    name: string;
    baselineReturnPct: number;
  };
  relativeScore: number;
  rank: 'outperforming' | 'in-line' | 'lagging' | string;
  returns: Record<string, number>;
  peerPercentileEstimate: number;
}

export interface RecommendationCheckpoint {
  horizon: string;
  targetReturnPct: number;
  maxDrawdownPct: number;
}

export interface RecommendationTracker {
  version?: string;
  trackingId: string;
  status: string;
  openedAt: string;
  entryPrice: number;
  entryChangePct?: number | null;
  action: string;
  source?: string;
  sourceRole?: string;
  dataQualityScore?: number;
  gateKeys?: string[];
  expectedEdgePct: number;
  checkpoints: RecommendationCheckpoint[];
  reviewTriggers: string[];
}

export interface AttributionDriver {
  key: string;
  label: string;
  contribution: number;
}

export interface AttributionEngine {
  version: string;
  netContribution: number;
  drivers: AttributionDriver[];
  supportDrivers: AttributionDriver[];
  dragDrivers: AttributionDriver[];
  factorDrivers: string[];
}

export interface PortfolioOptimizer {
  version: string;
  targetWeightPct: number;
  currentWeightPct?: number | null;
  suggestedChangePct?: number | null;
  maxWeightPct: number;
  marginalRiskScore: number;
  concentrationAction: string;
  overlapTags: string[];
}

export interface AlertRule {
  key: string;
  severity: string;
  condition: string;
}

export interface AlertMonitor {
  priority: string;
  rules: AlertRule[];
  nextReview: string;
}

export interface ProfessionalAnalytics {
  factorModel: ProfessionalFactorModel;
  benchmarkRelative: BenchmarkRelativeScore;
  recommendationTracker: RecommendationTracker;
  attribution: AttributionEngine;
  portfolioOptimizer?: PortfolioOptimizer | null;
  alertMonitor: AlertMonitor;
}

export interface DecisionEngineGate {
  kind: 'blockBuy' | 'forceReduce' | 'exitCandidate' | string;
  key: string;
  severity: 'info' | 'warning' | 'danger' | string;
  value?: number | null;
  threshold?: number | null;
}

export interface DecisionEngineDataQuality {
  score: number;
  level: 'strong' | 'usable' | 'thin' | 'weak' | string;
  priceHistoryScore: number;
  fundamentalCoverageScore: number;
  financialCoverageScore: number;
  newsCoverageScore: number;
  factorCoverageScore: number;
  marketSupportScore?: number;
  marketCoverageTier?: string;
  priceSource?: string;
  sourcePenalty?: number;
  sourceWarnings?: string[];
  issues: string[];
  strengths: string[];
}

export interface DecisionEngineMarketSupport {
  market?: Market | string;
  coverageTier: string;
  score: number;
  sourceReliabilityScore: number;
  capabilityScore: number;
  localPriority: boolean;
  preferred?: boolean;
  focusRank?: number;
  capabilities: Record<string, boolean>;
  sources: string[];
  limitations: string[];
  professionalAnchors?: string[];
}

export interface DecisionEngineRegime {
  name: string;
  confidence: number;
  signals: Record<string, number>;
}

export interface MarketSessionProfile {
  market: Market | string;
  state: string;
  priceSource?: string;
  gated: boolean;
  regularSession: boolean;
  openConfirmed: boolean;
  allowNewBuy: boolean;
  localTime?: string;
  reason?: string;
}

export interface InstrumentRiskProfile {
  instrumentType: InstrumentType;
  category: string;
  riskTier: string;
  highBeta?: boolean;
  blockBuyDropPct?: number;
  forceReduceDropPct?: number;
  maxWeightPct?: number;
  market?: Market | string;
}

export interface DiscoveryContext {
  source: string;
  role: string;
  hotSource: boolean;
  confirmationPassed: boolean;
  volumeConfirmationScore?: number;
}

export interface DecisionEngine {
  version: string;
  instrumentType: InstrumentType;
  market: Market;
  price: number;
  regime: DecisionEngineRegime;
  dataQuality: DecisionEngineDataQuality;
  marketSupport?: DecisionEngineMarketSupport;
  marketSession?: MarketSessionProfile;
  marketRuleState?: MarketRuleState;
  instrumentProfile?: InstrumentRiskProfile;
  discoveryContext?: DiscoveryContext;
  gates: DecisionEngineGate[];
  caseEvidence: Record<string, number>;
  buyScore: number;
  sellScore: number;
  holdScore: number;
  rankScore: number;
  riskRewardScore: number;
  confidenceScore: number;
  action: 'accumulate' | 'hold' | 'reduce' | 'exit' | string;
  verdict: Verdict;
  primaryReasons: string[];
  legacyScore: number;
  legacyWeightRole: 'secondary' | string;
}

export interface TradeExecutionProfile {
  status: 'not_applicable' | 'executable' | 'blocked_today' | 'partial_t1_locked' | string;
  tradableNow: boolean;
  availableQuantity?: number | null;
  blockedQuantity?: number | null;
  plannedQuantityChange?: number | null;
  executableQuantityChange?: number | null;
  rawQuantityChange?: number | null;
  orderSizing?: MarketOrderSizing;
}

export interface FinalDecision {
  version: string;
  action: 'accumulate' | 'hold' | 'reduce' | 'exit' | string;
  verdict: Verdict;
  source: string;
  confidence: number;
  execution: TradeExecutionProfile;
  primaryReasons: string[];
}

export interface QuoteObservation {
  source: string;
  price: number;
  role: 'primary' | 'backup' | 'broker' | string;
  freshness: 'live' | 'delayed' | 'user-snapshot' | 'unknown' | string;
}

export interface QuoteConsensus {
  version: string;
  status: 'aligned' | 'delayed' | 'fallback' | 'divergent' | 'conflict' | string;
  primarySource: string;
  primaryPrice?: number | null;
  observationCount: number;
  maxDeviationPct: number;
  confidence: number;
  conflict: boolean;
  severeConflict?: boolean;
  observations: QuoteObservation[];
}

export interface RecommendationAudit {
  version: string;
  trackingId?: string;
  openedAt: string;
  entryPrice: number;
  entryChangePct?: number | null;
  action: string;
  verdict: Verdict;
  status: string;
  source?: string;
  sourceRole?: string;
  dataQualityScore?: number;
  confidenceScore?: number;
  gateKeys: string[];
  failureReviewTriggers: string[];
  checkpoints: RecommendationCheckpoint[];
}

export interface Pick {
  symbol: string;
  name: string;
  market: Market;
  sector: string;
  instrumentType?: InstrumentType;
  price: number;
  change: number;
  currency: string;
  score: number;
  opportunityScore?: number;
  downsideRiskScore?: number;
  breakoutSetupScore?: number;
  pullbackRiskScore?: number;
  nextSessionContinuationScore?: number;
  nextSessionReversalRiskScore?: number;
  tScore?: number;
  tPlan?: TTradePlan;
  fundFlow?: FundFlowProfile | null;
  discoverySource?: string;
  discoveryRole?: string;
  compositeModel?: CompositeModel;
  decisionEngine?: DecisionEngine;
  marketRuleState?: MarketRuleState;
  finalDecision?: FinalDecision;
  quoteConsensus?: QuoteConsensus;
  recommendationAudit?: RecommendationAudit;
  professionalAnalytics?: ProfessionalAnalytics;
  prediction?: {
    opportunityScore: number;
    downsideRiskScore: number;
    breakoutSetupScore?: number;
    pullbackRiskScore?: number;
    nextSessionContinuationScore?: number;
    nextSessionReversalRiskScore?: number;
    overallScore?: number;
    todayBuyScore?: number;
    futureRiseScore?: number;
    profitableExitScore?: number;
    newsHeatImpactScore?: number;
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
  newsHeatAnalysis?: NewsHeatAnalysis;
  trendAnalysis?: TrendAnalysis;
  overallAssessment?: OverallAssessment;
  strategyAssessment?: StrategyAssessment;
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
    marketProfiles?: Record<Market | string, MarketProfile>;
    marketRuleProfiles?: Record<Market | string, MarketRuleProfile>;
    universe?: ScanUniverse;
  };
}

export interface ScanSourceBreakdown {
  source: string;
  label: string;
  role: string;
  count: number;
  markets: Record<string, number>;
}

export interface ScanUniverse {
  mode: 'market-wide-scan' | 'portfolio-holdings' | 'manual-symbols' | string;
  scope: 'market-wide-candidate-pool' | 'user-supplied-symbols' | string;
  candidatePoolSize: number;
  deepAnalysisCount: number;
  displayedCount: number;
  failedCount: number;
  requestedMarkets: Array<Market | string>;
  marketCounts: Record<string, number>;
  sourceBreakdown: ScanSourceBreakdown[];
  fallbackActive: boolean;
  fullMarketSourceActive: boolean;
  discoveryLimitPerMarket?: number | null;
  displayLimit?: number | null;
}

export interface AuthUser {
  id: string;
  label: string;
  enabled?: boolean;
  keyFingerprint?: string;
  notes?: string;
  createdAt?: string | null;
  updatedAt?: string | null;
  lastLoginAt?: string | null;
  stateUpdatedAt?: string | null;
}

export interface AuthSession {
  token: string;
  user: AuthUser;
  role: 'user' | 'admin' | string;
  expiresAt: number;
}

export interface UserState {
  settings?: Record<string, unknown>;
  savedScans?: unknown[];
  portfolio?: unknown;
  portfolioMemory?: PortfolioMemoryItem[];
  recommendationHistory?: unknown[];
  createdAt?: string;
  updatedAt?: string;
}

export interface AdminUser extends AuthUser {}

export interface AppConfig {
  markets: MarketOption[];
  strategies: Strategy[];
  strategyLibrary?: StrategyLibrary;
  defaultSymbols: Record<Market, string[]>;
  scanUniverseSize: Record<Market, number | string>;
  marketProfiles?: Record<Market, MarketProfile>;
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

const AUTH_SESSION_STORAGE_KEY = 'open-stock-picker.auth-session.v1';
let usingStaticFallback = false;
const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const staticDemoBuild = import.meta.env.PROD && import.meta.env.BASE_URL === '/stock-picker/' && !configuredApiBaseUrl;
let authSession: AuthSession | null = readStoredAuthSession();

function apiUrl(path: string) {
  return configuredApiBaseUrl ? `${configuredApiBaseUrl}${path}` : path;
}

function apiHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  return authSession?.token ? { ...extraHeaders, Authorization: `Bearer ${authSession.token}` } : extraHeaders;
}

async function errorMessage(response: Response, fallback: string) {
  try {
    const payload = await response.json();
    if (payload?.error) return String(payload.error);
  } catch {
    // Ignore non-JSON errors.
  }
  return fallback;
}

function readStoredAuthSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(AUTH_SESSION_STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as AuthSession;
    if (!session?.token || !session?.user?.id || Number(session.expiresAt || 0) * 1000 <= Date.now()) {
      localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function getAuthSession(): AuthSession | null {
  authSession = authSession ?? readStoredAuthSession();
  return authSession;
}

export function setAuthSession(session: AuthSession | null) {
  authSession = session;
  try {
    if (session) localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
    else localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
}

export function clearAuthSession() {
  setAuthSession(null);
}

export function currentDataMode(): 'demo' | 'live' {
  return staticDemoBuild || usingStaticFallback ? 'demo' : 'live';
}

function hasContentType(response: Response, expected: string) {
  return response.headers.get('content-type')?.toLowerCase().includes(expected) ?? false;
}

export async function loginWithAccessKey(key: string): Promise<AuthSession> {
  const response = await fetch(apiUrl('/api/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key })
  });
  if (!response.ok) throw new Error(await errorMessage(response, 'Invalid access key'));
  const session = await response.json() as AuthSession;
  setAuthSession(session);
  return session;
}

export async function loginAdmin(username: string, password: string): Promise<AuthSession> {
  const response = await fetch(apiUrl('/api/admin/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!response.ok) throw new Error(await errorMessage(response, 'Invalid administrator credentials'));
  const session = await response.json() as AuthSession;
  setAuthSession(session);
  return session;
}

export async function fetchCurrentSession(): Promise<AuthSession | null> {
  if (!authSession?.token) return null;
  const response = await fetch(apiUrl('/api/auth/me'), { headers: apiHeaders() });
  if (!response.ok) {
    clearAuthSession();
    return null;
  }
  const payload = await response.json();
  if (!payload?.authenticated) {
    clearAuthSession();
    return null;
  }
  return authSession;
}

export async function fetchUserState(): Promise<UserState> {
  const response = await fetch(apiUrl('/api/user/state'), { headers: apiHeaders() });
  if (!response.ok) throw new Error(await errorMessage(response, 'Failed to load user state'));
  return response.json();
}

export async function saveUserState(state: UserState): Promise<UserState> {
  const response = await fetch(apiUrl('/api/user/state'), {
    method: 'PUT',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(state)
  });
  if (!response.ok) throw new Error(await errorMessage(response, 'Failed to save user state'));
  return response.json();
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  const response = await fetch(apiUrl('/api/admin/users'), { headers: apiHeaders() });
  if (!response.ok) throw new Error(await errorMessage(response, 'Failed to load users'));
  const payload = await response.json();
  return Array.isArray(payload.users) ? payload.users : [];
}

export async function createAdminUser(payload: { accessKey: string; label?: string; notes?: string; enabled?: boolean }): Promise<AdminUser> {
  const response = await fetch(apiUrl('/api/admin/users'), {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await errorMessage(response, 'Failed to create user'));
  return (await response.json()).user as AdminUser;
}

export async function updateAdminUser(userId: string, payload: { accessKey?: string; label?: string; notes?: string; enabled?: boolean }): Promise<AdminUser> {
  const response = await fetch(apiUrl(`/api/admin/users/${encodeURIComponent(userId)}`), {
    method: 'PATCH',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await errorMessage(response, 'Failed to update user'));
  return (await response.json()).user as AdminUser;
}

export async function resetAdminUserState(userId: string): Promise<UserState> {
  const response = await fetch(apiUrl(`/api/admin/users/${encodeURIComponent(userId)}/reset-state`), {
    method: 'POST',
    headers: apiHeaders()
  });
  if (!response.ok) throw new Error(await errorMessage(response, 'Failed to reset user state'));
  return (await response.json()).state as UserState;
}

const fallbackStrategyLibrary: StrategyLibrary = {
  refreshedAt: new Date().toISOString(),
  sources: [
    {
      id: 'fidelity-indicator-guide',
      title: 'Fidelity Technical Indicator Guide',
      url: 'https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/overview',
      families: ['trend', 'momentum', 'volume', 'supportResistance', 'risk'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'fidelity-rsi',
      title: 'Fidelity RSI guide',
      url: 'https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI',
      families: ['rsi', 'momentum', 'reversal'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'fidelity-macd',
      title: 'Fidelity MACD guide',
      url: 'https://www.fidelity.com/viewpoints/active-investor/how-to-use-macd',
      families: ['macd', 'momentum', 'trend'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'schwab-momentum-strength',
      title: 'Schwab momentum strength indicators',
      url: 'https://www.schwab.com/learn/story/3-strength-indicators-assessing-stock-momentum',
      families: ['momentum', 'trend', 'rsi', 'macd'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'schwab-moving-averages',
      title: 'Schwab moving averages',
      url: 'https://www.schwab.com/learn/story/simple-vs-exponential-moving-averages',
      families: ['ma', 'trend', 'supportResistance'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'schwab-vwap-volume',
      title: 'Schwab VWAP and volume-weighted indicators',
      url: 'https://www.schwab.com/learn/story/how-to-use-volume-weighted-indicators-trading',
      families: ['volume', 'intraday', 'exit'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'schwab-bollinger-bands',
      title: 'Schwab Bollinger Bands',
      url: 'https://www.schwab.com/learn/story/bollinger-bands-what-they-are-and-how-to-use-them',
      families: ['volatility', 'meanReversion', 'entryExit'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'investopedia-moving-average',
      title: 'Investopedia moving averages',
      url: 'https://www.investopedia.com/articles/active-trading/052014/how-use-moving-average-buy-stocks.asp',
      families: ['ma', 'trend', 'supportResistance'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'investopedia-golden-cross',
      title: 'Investopedia golden cross',
      url: 'https://www.investopedia.com/terms/g/goldencross.asp',
      families: ['ma', 'breakout', 'trend'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'investopedia-macd',
      title: 'Investopedia MACD strategies',
      url: 'https://www.investopedia.com/articles/forex/05/macddiverge.asp',
      families: ['macd', 'momentum', 'divergence'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'investopedia-rsi-signals',
      title: 'Investopedia RSI buy and sell signals',
      url: 'https://www.investopedia.com/articles/active-trading/042114/overbought-or-oversold-use-relative-strength-index-find-out.asp',
      families: ['rsi', 'meanReversion', 'macd'],
      available: null,
      matchedKeywords: []
    },
    {
      id: 'fidelity-trading-central-methodology',
      title: 'Trading Central technical views on Fidelity',
      url: 'https://research2.fidelity.com/fidelity/research/reports/release2/Research/TradingCentral.asp',
      families: ['intraday', 'shortTerm', 'mediumTerm', 'supportResistance'],
      available: null,
      matchedKeywords: []
    }
  ],
  detailedWeightKeys: [
    'todayBuy',
    'futureRise',
    'profitableExit',
    'newsHeat',
    'trendContinuation',
    'maStructure',
    'momentum',
    'volumeConfirmation',
    'rsiHealth',
    'macdConfirmation',
    'supportResistance',
    'fundFlow',
    'valuation',
    'quality',
    'riskControl',
    'tTrade'
  ],
  detailedWeightLabels: {
    todayBuy: 'Worth buying today',
    futureRise: 'Future rise potential',
    profitableExit: 'Profitable exit later',
    newsHeat: 'News heat',
    trendContinuation: 'Trend continuation',
    maStructure: 'Moving-average structure',
    momentum: 'Momentum',
    volumeConfirmation: 'Volume confirmation',
    rsiHealth: 'RSI health',
    macdConfirmation: 'MACD confirmation',
    supportResistance: 'Support / resistance',
    fundFlow: 'Fund flow',
    valuation: 'Valuation',
    quality: 'Fundamental quality',
    riskControl: 'Risk control',
    tTrade: 'T / exit tradability'
  },
  strategies: [
    {
      id: 'ai_smart_blend',
      name: 'AI Smart Blend',
      description: 'Auto-blends the refreshed online strategy library across buy-today quality, future rise, profitable exit, news heat, trend, and risk.',
      weights: { momentum: 34, value: 6, sentiment: 14, risk: 10, quality: 6 },
      riskTolerance: 55,
      sourceStrategyIds: [
        'fidelity-indicator-guide',
        'fidelity-rsi',
        'fidelity-macd',
        'schwab-momentum-strength',
        'schwab-moving-averages',
        'schwab-vwap-volume',
        'schwab-bollinger-bands',
        'investopedia-moving-average',
        'investopedia-golden-cross',
        'investopedia-macd',
        'investopedia-rsi-signals',
        'fidelity-trading-central-methodology'
      ],
      detailedWeights: {
        todayBuy: 10.5,
        futureRise: 11.4,
        profitableExit: 8.8,
        newsHeat: 7,
        trendContinuation: 8.8,
        maStructure: 6.1,
        momentum: 7,
        volumeConfirmation: 6.1,
        rsiHealth: 4.4,
        macdConfirmation: 5.3,
        supportResistance: 4.4,
        fundFlow: 3.5,
        valuation: 2.6,
        quality: 3.5,
        riskControl: 6.1,
        tTrade: 4.4
      }
    },
    {
      id: 'today_breakout_volume',
      name: 'Today Breakout + Volume',
      description: 'Focuses on whether the current price break has volume and enough same-day entry quality.',
      weights: { momentum: 32, value: 5, sentiment: 14, risk: 9, quality: 3 },
      riskTolerance: 55,
      sourceStrategyIds: ['investopedia-golden-cross', 'schwab-vwap-volume', 'fidelity-indicator-guide'],
      detailedWeights: { todayBuy: 14.1, futureRise: 7.8, profitableExit: 6.3, newsHeat: 4.7, trendContinuation: 6.3, maStructure: 5.5, momentum: 7.8, volumeConfirmation: 12.5, rsiHealth: 2.3, macdConfirmation: 3.9, supportResistance: 7, fundFlow: 3.9, valuation: 1.6, quality: 1.6, riskControl: 4.7, tTrade: 3.9 }
    },
    {
      id: 'next_session_continuation',
      name: 'Next-Session Continuation',
      description: 'Prioritizes whether today\'s edge can continue tomorrow without immediate reversal risk.',
      weights: { momentum: 42, value: 4, sentiment: 9, risk: 9, quality: 4 },
      riskTolerance: 55,
      sourceStrategyIds: ['schwab-momentum-strength', 'fidelity-macd', 'fidelity-rsi'],
      detailedWeights: { todayBuy: 5.8, futureRise: 14.5, profitableExit: 8, newsHeat: 4.3, trendContinuation: 12.3, maStructure: 7.2, momentum: 8.7, volumeConfirmation: 5.1, rsiHealth: 5.8, macdConfirmation: 7.2, supportResistance: 3.6, fundFlow: 2.9, valuation: 1.4, quality: 2.9, riskControl: 5.8, tTrade: 2.9 }
    },
    {
      id: 'news_heat_catalyst',
      name: 'News Heat Catalyst',
      description: 'Looks for strong, fresh, broad news attention that still aligns with trend and exit quality.',
      weights: { momentum: 31, value: 4, sentiment: 25, risk: 7, quality: 3 },
      riskTolerance: 55,
      sourceStrategyIds: ['fidelity-indicator-guide', 'schwab-momentum-strength'],
      detailedWeights: { todayBuy: 7.8, futureRise: 9.4, profitableExit: 5.5, newsHeat: 17.2, trendContinuation: 6.3, maStructure: 3.9, momentum: 6.3, volumeConfirmation: 5.5, rsiHealth: 3.1, macdConfirmation: 3.9, supportResistance: 3.1, fundFlow: 6.3, valuation: 1.6, quality: 2.3, riskControl: 5.5, tTrade: 3.1 }
    }
  ]
};

const fallbackMarketProfiles: Record<Market, MarketProfile> = {
  CN: {
    market: 'CN',
    coverageTier: 'local-deep',
    sourceReliabilityScore: 88,
    localPriority: true,
    preferred: true,
    focusRank: 2,
    primarySources: [
      { id: 'eastmoney', label: 'Eastmoney', kind: 'market-data', role: 'A-share quote, turnover, flow and news context' },
      { id: 'sina-finance', label: 'Sina Finance', kind: 'market-data', role: 'A-share quote fallback' },
      { id: 'sse-market-data', label: 'SSE market data products', kind: 'exchange-licensed', role: 'official Shanghai exchange data path', official: true, licensed: true },
      { id: 'szse-market-data', label: 'SZSE / SZSI market data', kind: 'exchange-licensed', role: 'official Shenzhen market data path', official: true, licensed: true }
    ],
    capabilities: { priceHistory: true, officialExchange: true, localNews: true, fundamentals: true, valuation: true, institutionFlow: true, fundFlow: true, marginShort: true, haltWatch: true, etfCoverage: true },
    limitations: ['Official real-time SSE/SZSE redistribution is licensed; public providers use conservative confidence.'],
    professionalAnchors: ['source-transparency', 'factor-attribution', 'liquidity-risk']
  },
  HK: {
    market: 'HK',
    coverageTier: 'regional',
    sourceReliabilityScore: 78,
    localPriority: true,
    focusRank: 3,
    primarySources: [
      { id: 'yahoo-finance', label: 'Yahoo Finance', kind: 'market-data', role: 'price, fundamentals and history' },
      { id: 'google-news', label: 'Google News', kind: 'news', role: 'English and Chinese catalyst discovery' }
    ],
    capabilities: { priceHistory: true, officialExchange: false, localNews: true, fundamentals: true, valuation: true, institutionFlow: false, fundFlow: false, marginShort: false, haltWatch: false, etfCoverage: true },
    limitations: ['HKEX official and connect-flow adapters are not wired yet.'],
    professionalAnchors: ['source-transparency', 'portfolio-risk']
  },
  JP: {
    market: 'JP',
    coverageTier: 'basic',
    sourceReliabilityScore: 70,
    localPriority: false,
    focusRank: 5,
    primarySources: [
      { id: 'yahoo-finance', label: 'Yahoo Finance', kind: 'market-data', role: 'price, fundamentals and history' },
      { id: 'google-news', label: 'Google News', kind: 'news', role: 'Japanese and English news fallback' }
    ],
    capabilities: { priceHistory: true, officialExchange: false, localNews: true, fundamentals: true, valuation: true, institutionFlow: false, fundFlow: false, marginShort: false, haltWatch: false, etfCoverage: true },
    limitations: ['TSE official, margin and shareholder-flow adapters are not yet integrated.'],
    professionalAnchors: ['source-transparency', 'gics-industry']
  },
  KR: {
    market: 'KR',
    coverageTier: 'basic',
    sourceReliabilityScore: 68,
    localPriority: false,
    focusRank: 6,
    primarySources: [
      { id: 'yahoo-finance', label: 'Yahoo Finance', kind: 'market-data', role: 'price, fundamentals and history' },
      { id: 'google-news', label: 'Google News', kind: 'news', role: 'Korean and English news fallback' }
    ],
    capabilities: { priceHistory: true, officialExchange: false, localNews: true, fundamentals: true, valuation: true, institutionFlow: false, fundFlow: false, marginShort: false, haltWatch: false, etfCoverage: true },
    limitations: ['KRX official and investor-flow adapters are not yet integrated.'],
    professionalAnchors: ['source-transparency', 'gics-industry']
  },
  SG: {
    market: 'SG',
    coverageTier: 'basic',
    sourceReliabilityScore: 66,
    localPriority: false,
    focusRank: 7,
    primarySources: [
      { id: 'yahoo-finance', label: 'Yahoo Finance', kind: 'market-data', role: 'price, fundamentals and history' },
      { id: 'google-news', label: 'Google News', kind: 'news', role: 'English news fallback' }
    ],
    capabilities: { priceHistory: true, officialExchange: false, localNews: true, fundamentals: true, valuation: true, institutionFlow: false, fundFlow: false, marginShort: false, haltWatch: false, etfCoverage: true },
    limitations: ['SGX official and REIT-specific adapters are not yet integrated.'],
    professionalAnchors: ['source-transparency', 'portfolio-risk']
  },
  US: {
    market: 'US',
    coverageTier: 'global',
    sourceReliabilityScore: 76,
    localPriority: false,
    focusRank: 4,
    primarySources: [
      { id: 'yahoo-finance', label: 'Yahoo Finance', kind: 'market-data', role: 'price, fundamentals and ETF profile' },
      { id: 'google-news', label: 'Google News', kind: 'news', role: 'company catalyst discovery' }
    ],
    capabilities: { priceHistory: true, officialExchange: false, localNews: true, fundamentals: true, valuation: true, institutionFlow: false, fundFlow: false, marginShort: false, haltWatch: false, etfCoverage: true },
    limitations: ['Current open stack is broad but not a paid institutional consolidated feed.'],
    professionalAnchors: ['economic-moat', 'factor-attribution', 'portfolio-risk', 'gics-industry']
  },
  TW: {
    market: 'TW',
    coverageTier: 'local-deep',
    sourceReliabilityScore: 91,
    localPriority: true,
    preferred: true,
    focusRank: 1,
    primarySources: [
      { id: 'twse-openapi', label: 'TWSE OpenAPI', kind: 'exchange-openapi', role: 'listed prices, valuations, halt and margin data', official: true },
      { id: 'taipei-exchange', label: 'Taipei Exchange', kind: 'exchange-site', role: 'OTC market, ETF, institutional and margin context', official: true },
      { id: 'yahoo-finance', label: 'Yahoo Finance', kind: 'market-data', role: 'fallback fundamentals and history' },
      { id: 'local-news', label: 'MoneyDJ / Cnyes', kind: 'local-news', role: 'local market news and company catalysts' }
    ],
    capabilities: { priceHistory: true, officialExchange: true, localNews: true, fundamentals: true, valuation: true, institutionFlow: true, fundFlow: true, marginShort: true, haltWatch: true, etfCoverage: true },
    limitations: ['TWSE-listed equities have the deepest open coverage; TPEX and full intraday depth still need dedicated adapters.'],
    professionalAnchors: ['source-transparency', 'factor-attribution', 'portfolio-risk', 'local-market-microstructure']
  }
};

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
  strategies: fallbackStrategyLibrary.strategies,
  strategyLibrary: fallbackStrategyLibrary,
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
  },
  marketProfiles: fallbackMarketProfiles
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
  return fallbackConfig.strategies.find((strategy) => strategy.id === payload.strategyId) ?? fallbackConfig.strategies.find((strategy) => strategy.id === 'ai_smart_blend') ?? fallbackConfig.strategies[0];
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
      symbol: '7203.T',
      name: 'Toyota Motor',
      market: 'JP',
      sector: 'Automobiles',
      price: 3186,
      change: 1.2,
      currency: 'JPY',
      score: 78,
      opportunityScore: 74,
      downsideRiskScore: 31,
      breakoutSetupScore: 66,
      pullbackRiskScore: 34,
      tScore: 68,
      tPlan: {
        suitability: 'candidate',
        summary: { key: 'tCandidateSummary', params: { score: 68 } },
        score: 68,
        components: { liquidityScore: 80, volatilityScore: 63, volatilityPct: 3.1, turnoverScore: 70, turnoverPct: 4.2 },
        entryZone: { low: 3148, high: 3180 },
        takeProfitZone: { low: 3232, high: 3290 },
        stopLoss: 3102,
        reasons: [
          { key: 'tLiquidityReady', params: { score: 80 } },
          { key: 'tVolatilityReady', params: { score: 63, range: 3.1 } },
          { key: 'tSetupReady', params: { score: 66 } }
        ],
        riskControls: [{ key: 'tUseBasePositionOnly', params: {} }]
      },
      verdict: 'buy',
      confidence: 76,
      reasons: ['Demo mode: Japan-market sample with quality, momentum, and local-news support.'],
      reasonCodes: [
        { key: 'strongestFactors', params: { first: 'quality', second: 'momentum' } },
        { key: 'clearsBuyThreshold', params: {} }
      ],
      prediction: {
        opportunityScore: 74,
        downsideRiskScore: 31,
        breakoutSetupScore: 66,
        pullbackRiskScore: 34,
        tScore: 68,
        edge: 43
      },
      signals: [
        {
          source: 'Static demo',
          title: 'トヨタ、電動化投資と円安効果が業績を支える',
          summary: 'GitHub Pages preview sample for Japan-market coverage; connect the Python API for live local-news crawling.',
          link: 'https://github.com/tamyu321-source/stock-picker',
          sentiment: 0.58,
          credibility: 0.82,
          relevance: 0.86,
          ageHours: 3
        }
      ],
      metrics: { momentum: 76, value: 64, sentiment: 78, risk: 72, quality: 83 },
      scoreBreakdown: [
        { factor: 'momentum', score: 76, weight: 20, contribution: 15.2 },
        { factor: 'value', score: 64, weight: 15, contribution: 9.6 },
        { factor: 'sentiment', score: 78, weight: 40, contribution: 31.2 },
        { factor: 'risk', score: 72, weight: 10, contribution: 7.2 },
        { factor: 'quality', score: 83, weight: 15, contribution: 12.45 }
      ],
      decision: {
        summary: { key: 'buySummary', params: { score: 78 } },
        positives: [
          { key: 'momentumSupport', params: { score: 76 } },
          { key: 'newsBullishSummary', params: { positiveScore: 74, negativeScore: 18, netScore: 56, total: 1 } }
        ],
        negatives: [],
        watchItems: [{ key: 'watchValuation', params: {} }]
      },
      newsAnalysis: {
        summary: { key: 'newsBullishSummary', params: { positiveScore: 74, negativeScore: 18, netScore: 56, total: 1 } },
        positiveCount: 1,
        negativeCount: 0,
        positiveScore: 74,
        negativeScore: 18,
        netScore: 56,
        events: [
          {
            key: 'demandPositive',
            impact: 'positive',
            title: 'Static demo signal: Japan-market local-news sample remains supportive',
            source: 'Static demo',
            ageHours: 3,
            weight: 0.78,
            strength: 0.58,
            score: 24,
            evidence: 'GitHub Pages preview sample'
          }
        ]
      },
      financialAnalysis: {
        summary: { key: 'financialStrongSummary', params: { count: 3 } },
        metrics: [
          { key: 'forwardPE', value: '10.8', score: 74 },
          { key: 'profitMargins', value: '10.4%', score: 72 },
          { key: 'revenueGrowth', value: '12.0%', score: 70 }
        ],
        positives: [{ key: 'financialValuationReasonable', params: { value: 10.8 } }],
        negatives: [],
        watchItems: [{ key: 'financialWatchHighRange', params: { position: 66 } }]
      },
      actionPlan: {
        summary: { key: 'actionAccumulate', params: { score: 78 } },
        steps: [{ key: 'actionBuyInBatches', params: {} }],
        watchItems: [{ key: 'actionWatchNewsCatalyst', params: {} }],
        riskControls: [{ key: 'actionRespectRisk', params: { risk: 72 } }]
      }
    },
    {
      symbol: '005930.KS',
      name: 'Samsung Electronics',
      market: 'KR',
      sector: 'Semiconductors',
      price: 80200,
      change: 0.9,
      currency: 'KRW',
      score: 73,
      opportunityScore: 68,
      downsideRiskScore: 38,
      breakoutSetupScore: 61,
      pullbackRiskScore: 40,
      tScore: 62,
      tPlan: {
        suitability: 'watch',
        summary: { key: 'tWatchSummary', params: { score: 62 } },
        score: 62,
        components: { liquidityScore: 86, volatilityScore: 57, volatilityPct: 2.8, turnoverScore: 66, turnoverPct: 3.6 },
        entryZone: { low: 79000, high: 79900 },
        takeProfitZone: { low: 81600, high: 83200 },
        stopLoss: 77800,
        reasons: [{ key: 'tLiquidityReady', params: { score: 86 } }],
        riskControls: [
          { key: 'tVolatilityLow', params: { range: 2.8 } },
          { key: 'tUseBasePositionOnly', params: {} }
        ]
      },
      verdict: 'watch',
      confidence: 70,
      reasons: ['Demo mode: Korea-market sample with improving semiconductor cycle but pending confirmation.'],
      reasonCodes: [{ key: 'belowThreshold', params: { factor: 'momentum' } }],
      prediction: {
        opportunityScore: 68,
        downsideRiskScore: 38,
        breakoutSetupScore: 61,
        pullbackRiskScore: 40,
        tScore: 62,
        edge: 30
      },
      signals: [
        {
          source: 'Static demo',
          title: '삼성전자, 메모리 업황 회복 기대가 투자심리 개선',
          summary: 'GitHub Pages preview sample for Korea-market coverage; connect the Python API for live local-news crawling.',
          link: 'https://github.com/tamyu321-source/stock-picker',
          sentiment: 0.46,
          credibility: 0.8,
          relevance: 0.84,
          ageHours: 4
        }
      ],
      metrics: { momentum: 63, value: 66, sentiment: 72, risk: 68, quality: 80 },
      scoreBreakdown: [
        { factor: 'momentum', score: 63, weight: 20, contribution: 12.6 },
        { factor: 'value', score: 66, weight: 15, contribution: 9.9 },
        { factor: 'sentiment', score: 72, weight: 40, contribution: 28.8 },
        { factor: 'risk', score: 68, weight: 10, contribution: 6.8 },
        { factor: 'quality', score: 80, weight: 15, contribution: 12 }
      ],
      decision: {
        summary: { key: 'watchSummary', params: { score: 73 } },
        positives: [
          { key: 'qualitySupport', params: { score: 80 } },
          { key: 'newsBullishSummary', params: { positiveScore: 68, negativeScore: 24, netScore: 44, total: 1 } }
        ],
        negatives: [{ key: 'weakMomentum', params: { score: 63 } }],
        watchItems: [{ key: 'watchBreakout', params: { score: 61 } }]
      },
      newsAnalysis: {
        summary: { key: 'newsBullishSummary', params: { positiveScore: 68, negativeScore: 24, netScore: 44, total: 1 } },
        positiveCount: 1,
        negativeCount: 0,
        positiveScore: 68,
        negativeScore: 24,
        netScore: 44,
        events: [
          {
            key: 'demandPositive',
            impact: 'positive',
            title: 'Static demo signal: Korea-market semiconductor cycle sample improves',
            source: 'Static demo',
            ageHours: 4,
            weight: 0.74,
            strength: 0.46,
            score: 19,
            evidence: 'GitHub Pages preview sample'
          }
        ]
      },
      financialAnalysis: {
        summary: { key: 'financialMixedSummary', params: { positive: 2, negative: 1 } },
        metrics: [
          { key: 'forwardPE', value: '14.6', score: 68 },
          { key: 'profitMargins', value: '18.0%', score: 76 },
          { key: 'revenueGrowth', value: '8.0%', score: 62 }
        ],
        positives: [{ key: 'financialProfitabilitySupport', params: { score: 76 } }],
        negatives: [],
        watchItems: [{ key: 'financialWatchNextReport', params: {} }]
      },
      actionPlan: {
        summary: { key: 'actionWait', params: { score: 73 } },
        steps: [{ key: 'actionWaitNewsConfirmation', params: {} }],
        watchItems: [{ key: 'actionWatchMomentumTurn', params: {} }],
        riskControls: [{ key: 'actionRespectRisk', params: { risk: 68 } }]
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
    discoveryErrors: [],
    marketProfiles: fallbackMarketProfiles,
    universe: {
      mode: 'market-wide-scan',
      scope: 'market-wide-candidate-pool',
      candidatePoolSize: markets.length * 96,
      deepAnalysisCount: picks.length,
      displayedCount: picks.length,
      failedCount: 0,
      requestedMarkets: markets,
      marketCounts: Object.fromEntries(markets.map((market) => [market, picks.filter((pick) => pick.market === market).length])),
      sourceBreakdown: [
        {
          source: 'static-github-pages-demo',
          label: 'Static demo candidate pool',
          role: 'provider',
          count: picks.length,
          markets: Object.fromEntries(markets.map((market) => [market, picks.filter((pick) => pick.market === market).length]))
        }
      ],
      fallbackActive: false,
      fullMarketSourceActive: false,
      discoveryLimitPerMarket: 96,
      displayLimit: 48
    }
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
    const response = await fetch(apiUrl('/api/config'), { headers: apiHeaders() });
    if (!response.ok) throw new Error('Failed to load config');
    if (!hasContentType(response, 'application/json')) throw new Error('Static preview fallback');
    return response.json();
  } catch (cause) {
    if (staticDemoBuild) {
      usingStaticFallback = true;
      return fallbackConfig;
    }
    throw cause;
  }
}

export async function refreshStrategyLibrary(): Promise<StrategyLibrary> {
  if (staticDemoBuild || usingStaticFallback) {
    return { ...fallbackStrategyLibrary, refreshedAt: new Date().toISOString(), runtimeStrategies: fallbackConfig.strategies };
  }
  try {
    const response = await fetch(apiUrl('/api/strategies/refresh'), { headers: apiHeaders() });
    if (!response.ok) throw new Error('Failed to refresh strategy library');
    if (!hasContentType(response, 'application/json')) throw new Error('Static preview fallback');
    return response.json();
  } catch (cause) {
    if (staticDemoBuild) {
      usingStaticFallback = true;
      return { ...fallbackStrategyLibrary, refreshedAt: new Date().toISOString(), runtimeStrategies: fallbackConfig.strategies };
    }
    throw cause;
  }
}

function fallbackStockChart(symbol: string): StockChartResponse {
  const normalized = symbol.toUpperCase();
  const now = Date.now();
  const base = normalized.includes('2330') ? 865 : normalized.includes('NVDA') ? 122 : 100;
  const intraday: StockChartPoint[] = Array.from({ length: 42 }, (_, index) => {
    const wave = Math.sin(index / 4) * 1.2 + index * 0.08;
    const close = Number((base + wave).toFixed(2));
    return {
      time: new Date(now - (41 - index) * 5 * 60 * 1000).toISOString(),
      open: Number((close - 0.2).toFixed(2)),
      high: Number((close + 0.8).toFixed(2)),
      low: Number((close - 0.9).toFixed(2)),
      close,
      volume: 120000 + index * 2600
    };
  });
  const daily: StockChartPoint[] = Array.from({ length: 90 }, (_, index) => {
    const trend = index * 0.22;
    const wave = Math.sin(index / 6) * 4.5;
    const close = Number((base * 0.86 + trend + wave).toFixed(2));
    return {
      time: new Date(now - (89 - index) * 24 * 60 * 60 * 1000).toISOString(),
      open: Number((close - 1.1).toFixed(2)),
      high: Number((close + 2.6).toFixed(2)),
      low: Number((close - 2.3).toFixed(2)),
      close,
      volume: 420000 + index * 3800
    };
  });
  daily.forEach((point, index) => {
    const average = (windowSize: number) => {
      if (index + 1 < windowSize) return null;
      const values = daily.slice(index + 1 - windowSize, index + 1).map((item) => item.close);
      return Number((values.reduce((sum, value) => sum + value, 0) / windowSize).toFixed(2));
    };
    point.ma5 = average(5);
    point.ma10 = average(10);
    point.ma20 = average(20);
    if (index > 0 && index % 29 === 0) {
      point.limitUpPrice = Number((daily[index - 1].close * 1.1).toFixed(2));
      point.isLimitUp = true;
      point.high = point.limitUpPrice;
      point.close = point.limitUpPrice;
    }
  });
  return {
    symbol: normalized,
    name: normalized,
    currency: normalized.endsWith('.TW') ? 'TWD' : 'USD',
    source: 'Static demo chart',
    refreshedAt: new Date().toISOString(),
    intraday,
    daily
  };
}

export async function fetchStockChart(symbol: string): Promise<StockChartResponse> {
  if (staticDemoBuild || usingStaticFallback) {
    return fallbackStockChart(symbol);
  }
  const response = await fetch(apiUrl(`/api/stocks/${encodeURIComponent(symbol)}/chart`), { headers: apiHeaders() });
  if (!response.ok) {
    const payload = hasContentType(response, 'application/json') ? await response.json().catch(() => ({})) : {};
    throw new Error(payload.error || 'Failed to load stock chart');
  }
  if (!hasContentType(response, 'application/json')) throw new Error('Failed to load stock chart');
  return response.json();
}

export async function analyzeStocks(payload: {
  markets: Market[];
  symbols?: string[];
  strategyId?: string;
  customWeights?: StrategyWeights;
  refreshStrategies?: boolean;
  refresh?: boolean;
  portfolio?: PortfolioImportResponse | PortfolioAnalysis;
}): Promise<AnalysisResponse> {
  if (staticDemoBuild || usingStaticFallback) {
    return fallbackAnalysis(payload);
  }
  try {
    const response = await fetch(apiUrl('/api/analyze'), {
      method: 'POST',
      headers: apiHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error('Failed to analyze stocks');
    if (!hasContentType(response, 'application/json')) throw new Error('Static preview fallback');
    return response.json();
  } catch (cause) {
    if (staticDemoBuild) {
      usingStaticFallback = true;
      return fallbackAnalysis(payload);
    }
    throw cause;
  }
}

export async function analyzeStocksStream(
  payload: {
    markets: Market[];
    symbols?: string[];
    strategyId?: string;
    customWeights?: StrategyWeights;
    refreshStrategies?: boolean;
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
    response = await fetch(apiUrl('/api/analyze/stream'), {
      method: 'POST',
      headers: apiHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
      signal: options.signal
    });
    if (!response.ok) throw new Error('Failed to analyze stocks');
    if (!hasContentType(response, 'application/x-ndjson')) throw new Error('Static preview fallback');
  } catch (cause) {
    if (cause instanceof Error && cause.name === 'AbortError') throw cause;
    if (!staticDemoBuild) throw cause;
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
  const response = await fetch(apiUrl('/api/portfolio/import'), {
    method: 'POST',
    headers: apiHeaders(),
    body: formData
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.error || 'Failed to import holdings file');
  }
  if (!hasContentType(response, 'application/json')) throw new Error('Holdings import requires the live Python backend.');
  return response.json();
}
