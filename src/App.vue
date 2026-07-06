<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { analyzeStocksStream, clearAuthSession, createAdminUser, currentDataMode, fetchAdminUsers, fetchConfig, fetchCurrentSession, fetchStockChart, fetchUserState, getAuthSession, importPortfolioFile, loginAdmin, loginWithAccessKey, refreshStrategyLibrary, resetAdminUserState, saveUserState, setAuthSession, updateAdminUser, type AdminUser, type AnalysisScan, type AnalysisStreamEvent, type AppConfig, type AuthSession, type DecisionPoint, type DisplayMode, type FinancialMetric, type FundFlowProfile, type HoldingAction, type HoldingActionItem, type HoldingNote, type HoldingPosition, type Market, type MarketProfile, type NewsEvent, type OverallSuitability, type Pick, type PortfolioAnalysis, type PortfolioImportResponse, type PortfolioMemoryItem, type ReasonCode, type SectorAnalysis, type SectorRecommendation, type StockChartPoint, type StockChartResponse, type Strategy, type StrategyCheckResult, type StrategyFocusResult, type StrategyLibrary, type StrategyWeights, type UserState } from './api';
import { messages, strategyText, type Locale } from './i18n';
import ugoodaysLogo from './assets/ugoodays-logo.jpg';

type StandardLocale = Exclude<Locale, 'nan-TW'>;
type LocalizedText = Partial<Record<StandardLocale, string>> & { en: string };
type YogurtSoundCue = 'appear' | 'tap';
type ResultMarketFilter = 'all' | Market;
type ResultVerdictFilter = 'all' | Pick['verdict'] | 't';
type InvestmentTask = 'discover' | 'portfolio' | 'etf' | 'shortTerm';
type WorkbenchBucket = 'all' | 'buy' | 'hold' | 'risk' | 'etf' | 'holdings';
type PortfolioDashboardMetricKey = 'marketValue' | 'pnl' | 'sellable' | 'locked' | 'risk' | 'observe';
type ResultSortKey =
  | 'recommended'
  | 'overall'
  | 'decision'
  | 'score'
  | 'todayBuy'
  | 'futureRise'
  | 'profitableExit'
  | 'newsHeat'
  | 'continuation'
  | 'riskLow'
  | 'tScore'
  | 'change'
  | 'confidence';
type SortDirection = 'desc' | 'asc';
type DataMode = ReturnType<typeof currentDataMode>;
type DataIssue = { symbol: string; error: string };
type ChartTab = 'intraday' | 'daily';
type SavedScan = {
  id: string;
  title: string;
  savedAt: string;
  generatedAt: string;
  dataMode: DataMode;
  locale: Locale;
  markets: Market[];
  symbols: string[];
  strategyId: string;
  strategyName: string;
  useCustom: boolean;
  customWeights: StrategyWeights;
  picks: Pick[];
  sectors: SectorAnalysis[];
  errors: DataIssue[];
  scanInfo: AnalysisScan | null;
  portfolio: PortfolioAnalysis | PortfolioImportResponse | null;
};
type RecommendationHistoryItem = {
  id: string;
  symbol: string;
  name: string;
  market: Market;
  openedAt: string;
  scanGeneratedAt: string;
  entryPrice: number;
  action: string;
  verdict: Pick['verdict'];
  confidence: number;
  source?: string;
};
type HoldingRowView = {
  symbol: string;
  name: string;
  market?: Market | string;
  currency?: string;
  quantity: number | null;
  availableQuantity: number | null;
  blockedQuantity: number | null;
  costPrice: number | null;
  lastPrice: number | null;
  unrealizedPnl: number | null;
  unrealizedPnlPct: number | null;
  action: HoldingAction | string;
  executionStatus?: string;
  plannedQuantityChange: number | null;
  executableQuantityChange: number | null;
  stopLossPrice: number | null;
  takeProfitPrice: number | null;
  orderSizing?: HoldingActionItem['orderSizing'];
  livePriceDriftPct?: number | null;
  quoteStatus?: string | null;
  notes: HoldingNote[];
  pick?: Pick;
};

const locale = ref<Locale>('en');
const languageMenuOpen = ref(false);
const languageMenuRef = ref<HTMLElement | null>(null);
const config = ref<AppConfig | null>(null);
const selectedMarkets = ref<Market[]>(['US', 'CN', 'HK', 'JP', 'KR', 'SG', 'TW']);
const selectedStrategyId = ref('ai_smart_blend');
const useCustom = ref(false);
const loading = ref(false);
const error = ref('');
const generatedAt = ref('');
const symbolText = ref('');
const picks = ref<Pick[]>([]);
const sectors = ref<SectorAnalysis[]>([]);
const activeView = ref<'stocks' | 'sectors'>('stocks');
const activeInvestmentTask = ref<InvestmentTask>('discover');
const activeWorkbenchBucket = ref<WorkbenchBucket>('all');
const resultMarketFilter = ref<ResultMarketFilter>('all');
const resultVerdictFilter = ref<ResultVerdictFilter>('all');
const resultSortKey = ref<ResultSortKey>('recommended');
const resultSortDirection = ref<SortDirection>('desc');
const displayMode = ref<DisplayMode>('simple');
const dataIssues = ref<DataIssue[]>([]);
const scanInfo = ref<AnalysisScan | null>(null);
const loadingStartedAt = ref(0);
const loadingElapsedSeconds = ref(0);
const loadingStepIndex = ref(0);
const scanRunId = ref(0);
const signalRefreshStartedAt = ref('');
const dataMode = ref(currentDataMode());
const savedScans = ref<SavedScan[]>([]);
const recommendationHistory = ref<RecommendationHistoryItem[]>([]);
const portfolioFileInput = ref<HTMLInputElement | null>(null);
const importedPortfolio = ref<PortfolioImportResponse | null>(null);
const analysisPortfolio = ref<PortfolioAnalysis | null>(null);
const portfolioMemory = ref<PortfolioMemoryItem[]>([]);
const importingPortfolio = ref(false);
const portfolioImportError = ref('');
const manualHoldingText = ref('');
const refreshingStrategies = ref(false);
const strategyRefreshError = ref('');
const detailPick = ref<Pick | null>(null);
const detailChart = ref<StockChartResponse | null>(null);
const detailChartTab = ref<ChartTab>('intraday');
const detailChartLoading = ref(false);
const detailChartError = ref('');
const chartSvgRef = ref<SVGSVGElement | null>(null);
const chartPointerIndex = ref<number | null>(null);
const yogurtSecretPrimed = ref(false);
const yogurtSecretOpen = ref(false);
let loadingTimer: number | undefined;
let loadingRunId = 0;
let analysisAbortController: AbortController | undefined;
let yogurtSecretTimer: number | undefined;
let yogurtAudioContext: AudioContext | undefined;
const yogurtAudioDataUris: Partial<Record<YogurtSoundCue, string>> = {};

const SETTINGS_STORAGE_KEY = 'open-stock-picker.settings.v1';
const SAVED_SCANS_STORAGE_KEY = 'open-stock-picker.saved-scans.v1';
const SAVED_SCAN_LIMIT = 6;
const PORTFOLIO_MEMORY_LIMIT = 5;
const RECOMMENDATION_HISTORY_LIMIT = 50;
const defaultMarkets: Market[] = ['US', 'CN', 'HK', 'JP', 'KR', 'SG', 'TW'];
const weightKeys: Array<keyof StrategyWeights> = ['momentum', 'value', 'sentiment', 'risk', 'quality'];
const verdictFilterOptions: ResultVerdictFilter[] = ['all', 'buy', 't', 'watch', 'sell'];
const resultSortOptions: ResultSortKey[] = ['recommended', 'decision', 'overall', 'score', 'todayBuy', 'futureRise', 'profitableExit', 'newsHeat', 'continuation', 'riskLow', 'tScore', 'change', 'confidence'];
const investmentTasks: InvestmentTask[] = ['discover', 'portfolio', 'etf', 'shortTerm'];
const workbenchBuckets: WorkbenchBucket[] = ['all', 'buy', 'hold', 'risk', 'etf', 'holdings'];
const languageOptions: Array<{ id: Locale; label: string; shortLabel: string; flagClass: string }> = [
  { id: 'en', label: 'English', shortLabel: 'EN', flagClass: 'flag-uk' },
  { id: 'zh-CN', label: '简体中文', shortLabel: '简', flagClass: 'flag-cn' },
  { id: 'zh-TW', label: '繁體中文', shortLabel: '繁', flagClass: 'flag-tw' },
  { id: 'nan-TW', label: '臺語', shortLabel: '臺', flagClass: 'flag-nan' },
  { id: 'ja', label: '日本語', shortLabel: '日', flagClass: 'flag-jp' },
  { id: 'ko', label: '한국어', shortLabel: '한', flagClass: 'flag-kr' }
];
const authSession = ref<AuthSession | null>(getAuthSession());
const authMode = ref<'user' | 'admin'>('user');
const accessKeyInput = ref('');
const adminUsernameInput = ref('');
const adminPasswordInput = ref('');
const authLoading = ref(false);
const authError = ref('');
const userStateReady = ref(false);
const userStateSaving = ref(false);
const userStateError = ref('');
const adminUsers = ref<AdminUser[]>([]);
const adminLoading = ref(false);
const adminError = ref('');
const newUserKey = ref('');
const newUserLabel = ref('');
const newUserNotes = ref('');
const newUserEnabled = ref(true);
let userStateSyncTimer: number | undefined;

const strategyLibraryText: Record<Locale, {
  refreshStrategies: string;
  refreshingStrategies: string;
  onlineStrategies: string;
  sources: string;
  availableSources: string;
  usableSources: string;
  detailedWeights: string;
  aiBlendHint: string;
  updated: string;
  sourceLibrary: string;
  sourcePending: string;
  sourceAvailable: string;
  sourceFailed: string;
  matchedKeywords: string;
  openDetail: string;
  stockDetail: string;
  intraday: string;
  dailyK: string;
  loadingChart: string;
  chartUnavailable: string;
  chartSource: string;
  limitUp: string;
  closeDetail: string;
  decisionModel: string;
  modelFit: string;
  shortTermScore: string;
  midLongTermScore: string;
  stableQualityScore: string;
  horizonType: string;
  baseScore: string;
  adjustedScore: string;
  sortScore: string;
  entryGates: string;
  vetoRules: string;
  focusItems: string;
  passed: string;
  failed: string;
  triggered: string;
  clear: string;
  modelAligned: string;
  modelWatch: string;
  modelAvoid: string;
  modelBlocked: string;
  sourceFallback: string;
}> = {
  en: {
    refreshStrategies: 'Refresh online strategies',
    refreshingStrategies: 'Refreshing strategies',
    onlineStrategies: 'online strategies',
    sources: 'sources',
    availableSources: 'available sources',
    usableSources: 'usable sources',
    detailedWeights: 'Detailed weights',
    aiBlendHint: 'AI Smart Blend will rebalance after the online source crawl refreshes.',
    updated: 'Updated',
    sourceLibrary: 'Source library',
    sourcePending: 'pending',
    sourceAvailable: 'live',
    sourceFailed: 'failed',
    matchedKeywords: 'matched',
    openDetail: 'Intraday / daily K',
    stockDetail: 'Stock detail',
    intraday: 'Intraday',
    dailyK: 'Daily K',
    loadingChart: 'Loading chart',
    chartUnavailable: 'Chart temporarily unavailable',
    chartSource: 'Chart source',
    limitUp: 'Limit up',
    closeDetail: 'Close',
    decisionModel: 'Strategy decision model',
    modelFit: 'Fit score',
    shortTermScore: 'Short-term fit',
    midLongTermScore: 'Mid/long fit',
    stableQualityScore: 'Quality stability',
    horizonType: 'Horizon',
    baseScore: 'Base final',
    adjustedScore: 'Strategy final',
    sortScore: 'Sort score',
    entryGates: 'Entry gates',
    vetoRules: 'Veto rules',
    focusItems: 'Strategy focus',
    passed: 'passed',
    failed: 'failed',
    triggered: 'triggered',
    clear: 'clear',
    modelAligned: 'aligned',
    modelWatch: 'watch',
    modelAvoid: 'avoid',
    modelBlocked: 'blocked',
    sourceFallback: 'fallback'
  },
  'zh-CN': {
    refreshStrategies: '刷新网上策略',
    refreshingStrategies: '正在刷新策略',
    onlineStrategies: '网上策略',
    sources: '来源',
    availableSources: '可用来源',
    usableSources: '可用策略源',
    detailedWeights: '细分权重',
    aiBlendHint: 'AI 智慧策略会在刷新网上来源后自动重新平衡。',
    updated: '更新时间',
    sourceLibrary: '策略来源库',
    sourcePending: '待刷新',
    sourceAvailable: '可用',
    sourceFailed: '失败',
    matchedKeywords: '命中',
    openDetail: '分时 / 日K',
    stockDetail: '个股详情',
    intraday: '分时',
    dailyK: '日K',
    loadingChart: '正在加载图表',
    chartUnavailable: '图表暂时不可用',
    chartSource: '图表来源',
    limitUp: '涨停价',
    closeDetail: '关闭',
    decisionModel: '策略决策模型',
    modelFit: '策略适配',
    shortTermScore: '短线适配',
    midLongTermScore: '中长线适配',
    stableQualityScore: '稳定优质',
    horizonType: '周期类型',
    baseScore: '原始总评',
    adjustedScore: '策略总评',
    sortScore: '排序分',
    entryGates: '入场门槛',
    vetoRules: '否决规则',
    focusItems: '策略重点',
    passed: '通过',
    failed: '未过',
    triggered: '触发',
    clear: '未触发',
    modelAligned: '匹配',
    modelWatch: '观察',
    modelAvoid: '规避',
    modelBlocked: '阻断',
    sourceFallback: '内置回退'
  },
  'zh-TW': {
    refreshStrategies: '刷新網上策略',
    refreshingStrategies: '正在刷新策略',
    onlineStrategies: '網上策略',
    sources: '來源',
    availableSources: '可用來源',
    usableSources: '可用策略源',
    detailedWeights: '細分權重',
    aiBlendHint: 'AI 智慧策略會在刷新網上來源後自動重新平衡。',
    updated: '更新時間',
    sourceLibrary: '策略來源庫',
    sourcePending: '待刷新',
    sourceAvailable: '可用',
    sourceFailed: '失敗',
    matchedKeywords: '命中',
    openDetail: '分時 / 日K',
    stockDetail: '個股詳情',
    intraday: '分時',
    dailyK: '日K',
    loadingChart: '正在載入圖表',
    chartUnavailable: '圖表暫時不可用',
    chartSource: '圖表來源',
    limitUp: '漲停價',
    closeDetail: '關閉',
    decisionModel: '策略決策模型',
    modelFit: '策略適配',
    shortTermScore: '短線適配',
    midLongTermScore: '中長線適配',
    stableQualityScore: '穩定優質',
    horizonType: '週期類型',
    baseScore: '原始總評',
    adjustedScore: '策略總評',
    sortScore: '排序分',
    entryGates: '入場門檻',
    vetoRules: '否決規則',
    focusItems: '策略重點',
    passed: '通過',
    failed: '未過',
    triggered: '觸發',
    clear: '未觸發',
    modelAligned: '匹配',
    modelWatch: '觀察',
    modelAvoid: '規避',
    modelBlocked: '阻斷',
    sourceFallback: '內建回退'
  },
  'nan-TW': {
    refreshStrategies: '刷新網路策略',
    refreshingStrategies: '策略刷新中',
    onlineStrategies: '網路策略',
    sources: '來源',
    availableSources: '會用的來源',
    usableSources: '會用的策略源',
    detailedWeights: '細分權重',
    aiBlendHint: 'AI 智慧策略會照新抓著的來源自動重排權重。',
    updated: '更新時間',
    sourceLibrary: '策略來源庫',
    sourcePending: '等待刷新',
    sourceAvailable: '會用',
    sourceFailed: '失敗',
    matchedKeywords: '命中',
    openDetail: '分時 / 日K',
    stockDetail: '個股詳情',
    intraday: '分時',
    dailyK: '日K',
    loadingChart: '圖表載入中',
    chartUnavailable: '圖表暫時無法度用',
    chartSource: '圖表來源',
    limitUp: '漲停價',
    closeDetail: '關閉',
    decisionModel: '策略決策模型',
    modelFit: '策略適配',
    shortTermScore: '短線適配',
    midLongTermScore: '中長線適配',
    stableQualityScore: '穩定優質',
    horizonType: '週期類型',
    baseScore: '原始總評',
    adjustedScore: '策略總評',
    sortScore: '排序分',
    entryGates: '入場門檻',
    vetoRules: '否決規則',
    focusItems: '策略重點',
    passed: '通過',
    failed: '未過',
    triggered: '觸發',
    clear: '未觸發',
    modelAligned: '匹配',
    modelWatch: '觀察',
    modelAvoid: '規避',
    modelBlocked: '阻斷',
    sourceFallback: '內建回退'
  },
  ja: {
    refreshStrategies: 'オンライン戦略を更新',
    refreshingStrategies: '戦略を更新中',
    onlineStrategies: 'オンライン戦略',
    sources: 'ソース',
    availableSources: '利用可能ソース',
    usableSources: '利用可能な戦略ソース',
    detailedWeights: '詳細ウェイト',
    aiBlendHint: 'AI Smart Blend はオンラインソース更新後に自動で再調整します。',
    updated: '更新',
    sourceLibrary: '戦略ソース',
    sourcePending: '未更新',
    sourceAvailable: '有効',
    sourceFailed: '失敗',
    matchedKeywords: '一致',
    openDetail: '分足 / 日足',
    stockDetail: '銘柄詳細',
    intraday: '分足',
    dailyK: '日足',
    loadingChart: 'チャート読込中',
    chartUnavailable: 'チャートを一時的に取得できません',
    chartSource: 'チャートソース',
    limitUp: 'ストップ高',
    closeDetail: '閉じる',
    decisionModel: '戦略判断モデル',
    modelFit: '適合スコア',
    shortTermScore: '短期適合',
    midLongTermScore: '中長期適合',
    stableQualityScore: '品質安定性',
    horizonType: '時間軸',
    baseScore: '基礎総合',
    adjustedScore: '戦略総合',
    sortScore: '並び替えスコア',
    entryGates: 'エントリー条件',
    vetoRules: '除外条件',
    focusItems: '戦略の重点',
    passed: '通過',
    failed: '未通過',
    triggered: '発動',
    clear: '未発動',
    modelAligned: '適合',
    modelWatch: '注視',
    modelAvoid: '回避',
    modelBlocked: 'ブロック',
    sourceFallback: '内蔵フォールバック'
  },
  ko: {
    refreshStrategies: '온라인 전략 새로고침',
    refreshingStrategies: '전략 새로고침 중',
    onlineStrategies: '온라인 전략',
    sources: '출처',
    availableSources: '사용 가능한 출처',
    usableSources: '사용 가능한 전략 출처',
    detailedWeights: '세부 가중치',
    aiBlendHint: 'AI Smart Blend는 온라인 출처를 새로 수집한 뒤 자동으로 재조정됩니다.',
    updated: '업데이트',
    sourceLibrary: '전략 출처',
    sourcePending: '대기',
    sourceAvailable: '사용 가능',
    sourceFailed: '실패',
    matchedKeywords: '일치',
    openDetail: '분시 / 일봉',
    stockDetail: '종목 상세',
    intraday: '분시',
    dailyK: '일봉',
    loadingChart: '차트 로딩 중',
    chartUnavailable: '차트를 일시적으로 사용할 수 없습니다',
    chartSource: '차트 출처',
    limitUp: '상한가',
    closeDetail: '닫기',
    decisionModel: '전략 의사결정 모델',
    modelFit: '적합 점수',
    shortTermScore: '단기 적합',
    midLongTermScore: '중장기 적합',
    stableQualityScore: '품질 안정성',
    horizonType: '기간 유형',
    baseScore: '기본 종합',
    adjustedScore: '전략 종합',
    sortScore: '정렬 점수',
    entryGates: '진입 조건',
    vetoRules: '차단 규칙',
    focusItems: '전략 중점',
    passed: '통과',
    failed: '미통과',
    triggered: '발동',
    clear: '미발동',
    modelAligned: '적합',
    modelWatch: '관찰',
    modelAvoid: '회피',
    modelBlocked: '차단',
    sourceFallback: '내장 fallback'
  }
};

const detailedWeightText: Record<Locale, Record<string, string>> = {
  en: {},
  'zh-CN': {
    todayBuy: '今日值得买入',
    futureRise: '未来上涨潜力',
    profitableExit: '之后盈利卖出',
    newsHeat: '新闻热度',
    trendContinuation: '趋势延续',
    maStructure: '均线结构',
    momentum: '动能',
    volumeConfirmation: '量能确认',
    rsiHealth: 'RSI 健康度',
    macdConfirmation: 'MACD 确认',
    supportResistance: '支撑 / 压力',
    fundFlow: '资金流',
    valuation: '估值',
    quality: '基本面质量',
    riskControl: '风险控制',
    tTrade: '做T / 卖出窗口'
  },
  'zh-TW': {
    todayBuy: '今日值得買入',
    futureRise: '未來上漲潛力',
    profitableExit: '之後盈利賣出',
    newsHeat: '新聞熱度',
    trendContinuation: '趨勢延續',
    maStructure: '均線結構',
    momentum: '動能',
    volumeConfirmation: '量能確認',
    rsiHealth: 'RSI 健康度',
    macdConfirmation: 'MACD 確認',
    supportResistance: '支撐 / 壓力',
    fundFlow: '資金流',
    valuation: '估值',
    quality: '基本面品質',
    riskControl: '風險控制',
    tTrade: '做T / 賣出窗口'
  },
  'nan-TW': {
    todayBuy: '今仔日敢好買',
    futureRise: '後勢上漲',
    profitableExit: '後擺賣有趁',
    newsHeat: '新聞熱度',
    trendContinuation: '趨勢延續',
    maStructure: '均線結構',
    momentum: '動能',
    volumeConfirmation: '量能確認',
    rsiHealth: 'RSI 健康',
    macdConfirmation: 'MACD 確認',
    supportResistance: '支撐 / 壓力',
    fundFlow: '資金流',
    valuation: '估值',
    quality: '基本面品質',
    riskControl: '風險控制',
    tTrade: '做T / 賣出窗口'
  },
  ja: {
    todayBuy: '本日買い適性',
    futureRise: '将来上昇余地',
    profitableExit: '利益確定余地',
    newsHeat: 'ニュース熱量',
    trendContinuation: 'トレンド継続',
    maStructure: '移動平均構造',
    momentum: 'モメンタム',
    volumeConfirmation: '出来高確認',
    rsiHealth: 'RSI 健全性',
    macdConfirmation: 'MACD 確認',
    supportResistance: '支持 / 抵抗',
    fundFlow: '資金フロー',
    valuation: 'バリュエーション',
    quality: 'ファンダメンタル品質',
    riskControl: 'リスク管理',
    tTrade: 'T取引 / 売却窓'
  },
  ko: {
    todayBuy: '오늘 매수 적합도',
    futureRise: '향후 상승 잠재력',
    profitableExit: '수익 매도 가능성',
    newsHeat: '뉴스 열기',
    trendContinuation: '추세 지속',
    maStructure: '이동평균 구조',
    momentum: '모멘텀',
    volumeConfirmation: '거래량 확인',
    rsiHealth: 'RSI 건강도',
    macdConfirmation: 'MACD 확인',
    supportResistance: '지지 / 저항',
    fundFlow: '자금 흐름',
    valuation: '밸류에이션',
    quality: '펀더멘털 품질',
    riskControl: '리스크 관리',
    tTrade: 'T 매매 / 매도 창'
  }
};

type PersistedSettings = {
  locale?: Locale;
  selectedMarkets?: Market[];
  selectedStrategyId?: string;
  useCustom?: boolean;
  customWeights?: Partial<StrategyWeights>;
  symbolText?: string;
  manualHoldingText?: string;
  displayMode?: DisplayMode;
  defaultTaskMode?: InvestmentTask;
  defaultResultView?: 'stocks' | 'sectors';
  resultSortKey?: ResultSortKey;
  resultSortDirection?: SortDirection;
};

const customWeights = reactive<StrategyWeights>({
  momentum: 24,
  value: 20,
  sentiment: 24,
  risk: 16,
  quality: 16
});

const marketLabels: Record<Locale, Record<Market, string>> = {
  en: {
    CN: 'China A-shares',
    HK: 'Hong Kong',
    JP: 'Japan',
    KR: 'South Korea',
    SG: 'Singapore',
    US: 'United States',
    TW: 'Taiwan'
  },
  'zh-CN': {
    CN: '中国 A 股',
    HK: '香港',
    JP: '日本',
    KR: '韩国',
    SG: '新加坡',
    US: '美国',
    TW: '台湾'
  },
  'zh-TW': {
    CN: '中國 A 股',
    HK: '香港',
    JP: '日本',
    KR: '韓國',
    SG: '新加坡',
    US: '美國',
    TW: '台灣'
  },
  'nan-TW': {
    CN: '中國 A 股',
    HK: '香港',
    JP: '日本',
    KR: '韓國',
    SG: '新加坡',
    US: '美國',
    TW: '臺灣'
  },
  ja: {
    CN: '中国 A 株',
    HK: '香港',
    JP: '日本',
    KR: '韓国',
    SG: 'シンガポール',
    US: '米国',
    TW: '台湾'
  },
  ko: {
    CN: '중국 A주',
    HK: '홍콩',
    JP: '일본',
    KR: '한국',
    SG: '싱가포르',
    US: '미국',
    TW: '대만'
  }
};

const t = computed(() => messages[locale.value]);
const strategyUi = computed(() => strategyLibraryText[locale.value]);
const activeLanguageOption = computed(() => languageOptions.find((option) => option.id === locale.value) ?? languageOptions[0]);
const strategies = computed<Strategy[]>(() => config.value?.strategies ?? []);
const selectedStrategy = computed(() => strategies.value.find((item) => item.id === selectedStrategyId.value));
const strategyLibrary = computed(() => config.value?.strategyLibrary ?? null);
const strategySources = computed(() => strategyLibrary.value?.sources ?? []);
const selectedDetailedWeightEntries = computed(() => {
  const weights = selectedStrategy.value?.detailedWeights;
  if (!weights) return [];
  const keys = strategyLibrary.value?.detailedWeightKeys?.length ? strategyLibrary.value.detailedWeightKeys : Object.keys(weights);
  return keys
    .filter((key) => weights[key] !== undefined)
    .map((key) => ({ key, value: Number(weights[key] ?? 0) }))
    .sort((left, right) => right.value - left.value);
});
const selectedStrategySources = computed(() => {
  const ids = new Set(selectedStrategy.value?.sourceStrategyIds ?? []);
  if (!ids.size) return [];
  return strategySources.value.filter((source) => ids.has(source.id));
});
const strategySourceSummary = computed(() => {
  const total = strategySources.value.length;
  const available = strategySources.value.filter((source) => source.available === true).length;
  const usable = strategySources.value.filter((source) => source.available === true || source.usable === true).length;
  const selected = selectedStrategySources.value.length;
  if (!total) return '';
  if (available) return `${selected || total}/${total} ${strategyUi.value.onlineStrategies} · ${available} ${strategyUi.value.availableSources} · ${usable} ${strategyUi.value.usableSources}`;
  if (usable) return `${selected || total}/${total} ${strategyUi.value.onlineStrategies} · ${usable} ${strategyUi.value.usableSources}`;
  return `${selected || total}/${total} ${strategyUi.value.onlineStrategies}`;
});
const strategyUpdatedLabel = computed(() => {
  const refreshedAt = strategyLibrary.value?.refreshedAt;
  if (!refreshedAt) return '';
  return `${strategyUi.value.updated} ${new Date(refreshedAt).toLocaleString()}`;
});
const visibleChartPoints = computed<StockChartPoint[]>(() => {
  const chart = detailChart.value;
  if (!chart) return [];
  const points = detailChartTab.value === 'intraday' ? chart.intraday : chart.daily;
  return points.slice(detailChartTab.value === 'intraday' ? -90 : -110);
});
const chartRange = computed(() => {
  const points = visibleChartPoints.value;
  const values = points.flatMap((point) => [
    point.open,
    point.high,
    point.low,
    point.close,
    point.ma5,
    point.ma10,
    point.ma20,
    point.limitUpPrice
  ]).filter((value): value is number => Number.isFinite(value));
  if (!values.length) return { min: 0, max: 1 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = Math.max((max - min) * 0.08, Math.abs(max) * 0.004, 0.01);
  return { min: min - padding, max: max + padding };
});
const chartLinePath = computed(() => makeChartLinePath(visibleChartPoints.value));
const chartAreaPath = computed(() => makeChartAreaPath(visibleChartPoints.value));
const chartMa5Path = computed(() => makeChartValuePath(visibleChartPoints.value, 'ma5'));
const chartMa10Path = computed(() => makeChartValuePath(visibleChartPoints.value, 'ma10'));
const chartMa20Path = computed(() => makeChartValuePath(visibleChartPoints.value, 'ma20'));
const activeChartPoint = computed(() => {
  const points = visibleChartPoints.value;
  const index = chartPointerIndex.value;
  if (index === null || !points[index]) return null;
  return { point: points[index], index };
});
const activeChartX = computed(() => {
  const active = activeChartPoint.value;
  if (!active) return 40;
  return chartX(active.index, Math.max(1, visibleChartPoints.value.length - 1));
});
const activeChartY = computed(() => {
  const active = activeChartPoint.value;
  if (!active) return 220;
  return detailChartTab.value === 'daily' && active.point.isLimitUp ? 28 : chartY(active.point.close);
});
const chartTooltipStyle = computed(() => {
  const x = activeChartX.value;
  return {
    left: `${Math.min(74, Math.max(16, (x / 720) * 100))}%`,
    transform: x > 520 ? 'translateX(-100%)' : 'translateX(0)'
  };
});
const chartCandles = computed(() => {
  const points = visibleChartPoints.value;
  if (detailChartTab.value !== 'daily') return [];
  const total = Math.max(1, points.length - 1);
  const candleWidth = Math.max(3, Math.min(8, 640 / Math.max(1, points.length) * 0.55));
  return points.map((point, index) => {
    const open = point.open ?? point.close;
    const close = point.close;
    const high = point.high ?? Math.max(open, close);
    const low = point.low ?? Math.min(open, close);
    const x = chartX(index, total);
    const yOpen = chartY(open);
    const yClose = chartY(close);
    return {
      x,
      width: candleWidth,
      yHigh: chartY(high),
      yLow: chartY(low),
      yBody: Math.min(yOpen, yClose),
      bodyHeight: Math.max(2, Math.abs(yClose - yOpen)),
      rising: close >= open
    };
  });
});
const marketOptions = computed(() => config.value?.markets ?? []);
const marketProfiles = computed<Partial<Record<Market, MarketProfile>>>(() => config.value?.marketProfiles ?? {});
const scanUniverse = computed(() => scanInfo.value?.universe ?? null);
const isProfessionalMode = computed(() => displayMode.value === 'professional');
const preferredMarketsLabel = computed(() => {
  const preferred = selectedMarkets.value
    .filter((market) => marketProfiles.value[market]?.preferred || marketProfiles.value[market]?.localPriority)
    .sort((left, right) => (marketProfiles.value[left]?.focusRank ?? 99) - (marketProfiles.value[right]?.focusRank ?? 99))
    .map((market) => `${market} ${marketCoverageTierLabel(marketProfiles.value[market]?.coverageTier)}`);
  if (!preferred.length) return marketCoverageTierLabel('global');
  return preferred.slice(0, 2).join(' · ');
});
const filteredPicks = computed(() => picks.value.filter((pick) => {
  if (!pickMatchesWorkbenchBucket(pick, activeWorkbenchBucket.value)) return false;
  const marketMatches = resultMarketFilter.value === 'all' || pick.market === resultMarketFilter.value;
  const verdictMatches = resultVerdictFilter.value === 'all'
    || (resultVerdictFilter.value === 't' ? pick.tPlan?.suitability === 'candidate' : finalVerdictBucket(pick) === resultVerdictFilter.value);
  return marketMatches && verdictMatches;
}).map((pick, index) => ({ pick, index }))
  .sort((left, right) => compareSortedPicks(left, right))
  .map((item) => item.pick));
const decisionBucketItems = computed(() => workbenchBuckets.map((bucket) => ({
  bucket,
  label: workbenchBucketLabel(bucket),
  count: picks.value.filter((pick) => pickMatchesWorkbenchBucket(pick, bucket)).length,
  tone: bucket === 'buy' ? 'buy' : bucket === 'risk' ? 'sell' : bucket === 'etf' ? 'etf' : bucket === 'holdings' ? 'holding' : 'watch'
})));
const activeTaskMode = computed(() => activeInvestmentTask.value);
const topHoldingPicks = computed(() => picks.value.filter((pick) => pick.holding && pick.holdingAnalysis).slice(0, 4));
const topEtfPicks = computed(() => picks.value.filter((pick) => pick.instrumentType === 'etf').slice(0, 4));
const holdingPicks = computed(() => picks.value.filter((pick) => pick.holding && pick.holdingAnalysis));
const holdingCommandSummary = computed(() => {
  const plannedSell = holdingPicks.value.reduce((sum, pick) => sum + Math.min(0, Number(pick.holdingAnalysis?.plannedQuantityChange ?? 0)), 0);
  const executableSell = holdingPicks.value.reduce((sum, pick) => sum + Math.min(0, Number(pick.holdingAnalysis?.suggestedQuantityChange ?? 0)), 0);
  return {
    count: holdingPicks.value.length,
    reduceCount: holdingPicks.value.filter((pick) => pick.holdingAnalysis?.action === 'reduce').length,
    exitCount: holdingPicks.value.filter((pick) => pick.holdingAnalysis?.action === 'exit').length,
    blockedCount: holdingPicks.value.filter((pick) => pick.holdingAnalysis?.executionStatus === 'blocked_today').length,
    plannedSell,
    executableSell
  };
});
const holdingActionItems = computed<HoldingActionItem[]>(() => {
  const apiItems = activePortfolio.value?.actionItems;
  if (apiItems?.length) return apiItems.slice(0, 12);
  return picks.value
    .filter((pick) => pick.holding && pick.holdingAnalysis)
    .map((pick) => ({
    symbol: pick.symbol,
    name: pick.name,
    market: pick.market,
    action: pick.holdingAnalysis?.action ?? 'hold',
    bucket: pick.holdingAnalysis?.executionStatus === 'blocked_today'
      ? 't1_locked'
      : pick.holdingAnalysis?.action === 'exit' || pick.holdingAnalysis?.action === 'reduce'
        ? 'risk_action'
        : pick.holdingAnalysis?.action === 'hold'
          ? 'observe'
          : 'rebalance',
    executionStatus: pick.holdingAnalysis?.executionStatus ?? 'executable',
    plannedQuantityChange: pick.holdingAnalysis?.plannedQuantityChange ?? 0,
    executableQuantityChange: pick.holdingAnalysis?.suggestedQuantityChange ?? 0,
    unrealizedPnlPct: pick.holding?.unrealizedPnlPct ?? null,
    finalAction: pick.finalDecision?.action ?? pick.decisionEngine?.action ?? 'hold'
  }))
  .sort((left, right) => {
    const severity = (item: typeof left) => (item.action === 'exit' ? 4 : item.action === 'reduce' ? 3 : item.executionStatus === 'blocked_today' ? 2 : 1);
    return severity(right) - severity(left);
  })
    .slice(0, 8);
});
const recommendationReview = computed(() => {
  const currentBySymbol = new Map(picks.value.map((pick) => [pick.symbol, pick]));
  const reviewed = recommendationHistory.value
    .map((item) => {
      const current = currentBySymbol.get(item.symbol);
      const entry = Number(item.entryPrice ?? 0);
      const currentPrice = Number(current?.price ?? 0);
      const returnPct = entry > 0 && currentPrice > 0 ? (currentPrice - entry) / entry * 100 : null;
      return { ...item, currentPrice, returnPct };
    })
    .filter((item) => item.returnPct !== null);
  const wins = reviewed.filter((item) => Number(item.returnPct) > 0).length;
  const averageReturn = reviewed.length ? reviewed.reduce((sum, item) => sum + Number(item.returnPct), 0) / reviewed.length : 0;
  const worstReturn = reviewed.length ? Math.min(...reviewed.map((item) => Number(item.returnPct))) : 0;
  return {
    reviewed,
    count: reviewed.length,
    wins,
    hitRate: reviewed.length ? wins / reviewed.length * 100 : 0,
    averageReturn,
    worstReturn,
  };
});
const flattenedSignals = computed(() => filteredPicks.value.flatMap((pick) => pick.signals.map((signal) => ({ ...signal, symbol: pick.symbol }))));
const resultFiltersActive = computed(() => activeWorkbenchBucket.value !== 'all' || resultMarketFilter.value !== 'all' || resultVerdictFilter.value !== 'all' || resultSortKey.value !== 'recommended' || resultSortDirection.value !== 'desc');
const isDemoDataMode = computed(() => dataMode.value === 'demo');
const dataModeLabel = computed(() => (isDemoDataMode.value ? t.value.demoPreview : t.value.liveBackend));
const dataModeDescription = computed(() => (isDemoDataMode.value ? t.value.demoPreviewDetail : t.value.liveBackendDetail));
const canSaveScan = computed(() => picks.value.length > 0 && !loading.value);
const activePortfolio = computed(() => analysisPortfolio.value ?? importedPortfolio.value);
const isUserSession = computed(() => authSession.value?.role === 'user');
const isAdminSession = computed(() => authSession.value?.role === 'admin');
const authUserLabel = computed(() => authSession.value?.user.label || authSession.value?.user.id || '');
const portfolioSymbols = computed(() => importedPortfolio.value?.symbols ?? []);
const primaryActionDisabled = computed(() => activeTaskMode.value === 'portfolio' && !activePortfolio.value);
const primaryActionLabel = computed(() => {
  if (loading.value) return t.value.loading;
  const labels: Record<InvestmentTask, LocalizedText> = {
    discover: { en: 'Scan full market', 'zh-CN': '开始全市场扫描', 'zh-TW': '開始全市場掃描', ja: '市場全体をスキャン', ko: '전체 시장 스캔' },
    portfolio: { en: 'Check current holdings', 'zh-CN': '检查目前持仓', 'zh-TW': '檢查目前持倉', ja: '現在の保有を点検', ko: '현재 보유 점검' },
    etf: { en: 'Screen ETFs', 'zh-CN': '筛选 ETF', 'zh-TW': '篩選 ETF', ja: 'ETFを選別', ko: 'ETF 선별' },
    shortTerm: { en: 'Build short-term watchlist', 'zh-CN': '生成短线观察', 'zh-TW': '生成短線觀察', ja: '短期ウォッチを作成', ko: '단기 관찰 생성' }
  };
  return localeText(labels[activeTaskMode.value]);
});
const portfolioDashboardStats = computed(() => {
  const portfolio = activePortfolio.value;
  const positions = portfolio?.positions ?? [];
  const items = holdingActionItems.value;
  const sellableQuantity = items.length
    ? items.reduce((sum, item) => sum + (item.availableQuantity !== undefined && item.availableQuantity !== null ? nonNegativeQuantity(item.availableQuantity) : quantityMagnitude(item.executableQuantityChange)), 0)
    : positions.reduce((sum, position) => sum + nonNegativeQuantity(position.availableQuantity ?? position.quantity), 0);
  const lockedQuantity = items.length
    ? items.reduce((sum, item) => sum + nonNegativeQuantity(item.blockedQuantity ?? (item.executionStatus === 'blocked_today' ? item.quantity ?? item.plannedQuantityChange : 0)), 0)
    : positions.reduce((sum, position) => sum + Math.max(0, Number(position.quantity ?? 0) - Number(position.availableQuantity ?? position.quantity ?? 0)), 0);
  const riskActionCount = items.filter((item) => item.action === 'reduce' || item.action === 'exit' || item.bucket === 'risk_action').length || holdingCommandSummary.value.reduceCount + holdingCommandSummary.value.exitCount;
  const observeCount = items.filter((item) => item.action === 'hold' || item.bucket === 'observe').length;
  return {
    positions: holdingPicks.value.length || portfolio?.recognizedCount || positions.length || 0,
    marketValue: portfolio?.totalMarketValue ?? 0,
    pnl: portfolio?.totalUnrealizedPnl ?? 0,
    pnlPct: portfolio?.totalUnrealizedPnlPct ?? null,
    sellableQuantity,
    lockedQuantity,
    riskActionCount,
    observeCount
  };
});
const portfolioDashboardMetrics = computed(() => {
  const stats = portfolioDashboardStats.value;
  return [
    { key: 'marketValue' as const, tone: 'neutral', value: moneyLabel(stats.marketValue), detail: `${stats.positions} ${portfolioPositionUnitLabel()}` },
    { key: 'pnl' as const, tone: Number(stats.pnl) < 0 ? 'danger' : 'positive', value: signedMoneyLabel(stats.pnl), detail: percentLabel(stats.pnlPct) },
    { key: 'sellable' as const, tone: 'positive', value: quantityAbsLabel(stats.sellableQuantity), detail: holdingCommandMetricLabel('executable') },
    { key: 'locked' as const, tone: stats.lockedQuantity > 0 ? 'danger' : 'neutral', value: quantityAbsLabel(stats.lockedQuantity), detail: 'T+1' },
    { key: 'risk' as const, tone: stats.riskActionCount > 0 ? 'danger' : 'neutral', value: String(stats.riskActionCount), detail: holdingCommandMetricLabel('risk') },
    { key: 'observe' as const, tone: 'neutral', value: String(stats.observeCount), detail: portfolioObserveDetailLabel() }
  ];
});
const holdingRows = computed<HoldingRowView[]>(() => {
  const actionBySymbol = new Map(holdingActionItems.value.map((item) => [item.symbol, item]));
  const rows: HoldingRowView[] = [];
  const seen = new Set<string>();
  holdingPicks.value.forEach((pick) => {
    if (!pick.holding || !pick.holdingAnalysis) return;
    const item = actionBySymbol.get(pick.symbol);
    rows.push({
      symbol: pick.symbol,
      name: pick.holding.name || pick.name,
      market: pick.market,
      currency: pick.currency,
      quantity: pick.holding.quantity ?? null,
      availableQuantity: item?.availableQuantity ?? pick.holdingAnalysis.availableQuantity ?? pick.holding.availableQuantity ?? null,
      blockedQuantity: item?.blockedQuantity ?? pick.holdingAnalysis.blockedQuantity ?? null,
      costPrice: pick.holding.costPrice ?? null,
      lastPrice: pick.holding.brokerLastPrice ?? pick.holding.lastPrice ?? pick.price ?? null,
      unrealizedPnl: pick.holding.unrealizedPnl ?? null,
      unrealizedPnlPct: pick.holding.unrealizedPnlPct ?? null,
      action: item?.action ?? pick.holdingAnalysis.action,
      executionStatus: item?.executionStatus ?? pick.holdingAnalysis.executionStatus,
      plannedQuantityChange: item?.plannedQuantityChange ?? pick.holdingAnalysis.plannedQuantityChange ?? null,
      executableQuantityChange: item?.executableQuantityChange ?? pick.holdingAnalysis.suggestedQuantityChange ?? null,
      stopLossPrice: item?.stopLossPrice ?? pick.holdingAnalysis.stopLossPrice ?? null,
      takeProfitPrice: item?.takeProfitPrice ?? pick.holdingAnalysis.takeProfitPrice ?? null,
      orderSizing: item?.orderSizing ?? pick.holdingAnalysis.orderSizing,
      livePriceDriftPct: pick.holding.livePriceDriftPct ?? null,
      quoteStatus: pick.quoteConsensus?.status ?? null,
      notes: pick.holdingAnalysis.notes ?? [],
      pick
    });
    seen.add(pick.symbol);
  });
  (activePortfolio.value?.positions ?? []).forEach((position) => {
    if (seen.has(position.symbol)) return;
    const item = actionBySymbol.get(position.symbol);
    rows.push({
      symbol: position.symbol,
      name: position.name || position.symbol,
      market: position.market,
      currency: marketCurrency(position.market),
      quantity: position.quantity ?? null,
      availableQuantity: item?.availableQuantity ?? position.availableQuantity ?? null,
      blockedQuantity: item?.blockedQuantity ?? Math.max(0, Number(position.quantity ?? 0) - Number(position.availableQuantity ?? position.quantity ?? 0)),
      costPrice: position.costPrice ?? null,
      lastPrice: position.brokerLastPrice ?? position.lastPrice ?? null,
      unrealizedPnl: position.unrealizedPnl ?? null,
      unrealizedPnlPct: position.unrealizedPnlPct ?? null,
      action: item?.action ?? 'hold',
      executionStatus: item?.executionStatus ?? 'executable',
      plannedQuantityChange: item?.plannedQuantityChange ?? 0,
      executableQuantityChange: item?.executableQuantityChange ?? 0,
      stopLossPrice: item?.stopLossPrice ?? null,
      takeProfitPrice: item?.takeProfitPrice ?? null,
      orderSizing: item?.orderSizing,
      livePriceDriftPct: position.livePriceDriftPct ?? null,
      quoteStatus: null,
      notes: []
    });
  });
  return rows.sort((left, right) => holdingRowSeverity(right) - holdingRowSeverity(left));
});
const yogurtSecretLocalized = computed(() => locale.value === 'zh-TW' || locale.value === 'nan-TW');
const yogurtSecretTriggerLabel = computed(() => (locale.value === 'nan-TW' ? '活菌雷達' : '菌群雷達'));
const yogurtSecretClueLabel = computed(() => {
  if (locale.value === 'nan-TW') return '揣著 8 種乳酸菌 · 閣點一下';
  if (locale.value === 'zh-TW') return '偵測到 8 種乳酸菌 · 再點一下';
  return '4億/g';
});
const yogurtSecretNote = computed(() => {
  if (locale.value === 'nan-TW') return '你佇選股器內底揣著台南的發酵補給站，閣有 4 億/g 活菌藏咧。';
  if (locale.value === 'zh-TW') return '你在選股器裡找到一個台南發酵補給站，還藏著 4 億/g 活性乳酸菌。';
  return '';
});
const signalStatusLabel = computed(() => {
  if (loading.value) return signalRefreshStartedAt.value ? `${t.value.signalRefreshing} · ${signalRefreshStartedAt.value}` : t.value.signalRefreshing;
  if (generatedAt.value) return `${t.value.signalUpdated} · ${generatedAt.value}`;
  return t.value.signalEmpty;
});
const symbols = computed(() => symbolText.value.split(/[\s,;]+/).map((symbol) => symbol.trim()).filter(Boolean));
const isAutoScan = computed(() => symbols.value.length === 0);
const scanLabel = computed(() => {
  if (!scanInfo.value) {
    if (activeTaskMode.value === 'portfolio' && activePortfolio.value?.recognizedCount) return portfolioScanLabel(activePortfolio.value.recognizedCount);
    if (isAutoScan.value) return t.value.autoScan;
    if (locale.value === 'en') return `${symbols.value.length} narrowed`;
    if (locale.value === 'zh-CN') return `限定 ${symbols.value.length} 只`;
    if (locale.value === 'ja') return `${symbols.value.length} 件に絞り込み`;
    if (locale.value === 'ko') return `${symbols.value.length}개로 제한`;
    if (locale.value === 'nan-TW') return `限定 ${symbols.value.length} 檔`;
    return `限定 ${symbols.value.length} 檔`;
  }
  if (locale.value === 'en') return `${scanInfo.value.succeeded}/${scanInfo.value.requested} scanned`;
  if (locale.value === 'zh-CN') return `已扫 ${scanInfo.value.succeeded}/${scanInfo.value.requested}`;
  if (locale.value === 'ja') return `${scanInfo.value.succeeded}/${scanInfo.value.requested} 件スキャン済み`;
  if (locale.value === 'ko') return `${scanInfo.value.succeeded}/${scanInfo.value.requested}개 스캔 완료`;
  if (locale.value === 'nan-TW') return `已掃 ${scanInfo.value.succeeded}/${scanInfo.value.requested}`;
  return `已掃 ${scanInfo.value.succeeded}/${scanInfo.value.requested}`;
});
const analysisSteps = computed(() => {
  if (locale.value === 'en') {
    return isAutoScan.value
      ? [
          'Discovering candidates across selected markets',
          'Cross-checking local finance news sources',
          'Loading price and fundamentals data',
          'Strictly vetting quality candidates'
        ]
      : [
          'Loading recent company news',
          'Fetching price and fundamentals data',
          'Calculating strategy scores',
          'Preparing decisions and risk notes'
        ];
  }
  if (locale.value === 'zh-CN') {
    return isAutoScan.value
      ? ['正在深度扫描所选市场', '正在交叉检查当地财经新闻源', '正在拉取行情与基本面', '正在严格筛选优质投资候选']
      : ['正在拉取个股近期新闻', '正在获取行情与基本面', '正在计算策略评分', '正在整理判断与风险提示'];
  }
  if (locale.value === 'ja') {
    return isAutoScan.value
      ? ['選択市場から候補を発見中', '現地の金融ニュースを照合中', '価格とファンダメンタルを取得中', '高品質候補を厳格に選別中']
      : ['直近の企業ニュースを取得中', '価格とファンダメンタルを取得中', '戦略スコアを計算中', '判断とリスクメモを作成中'];
  }
  if (locale.value === 'ko') {
    return isAutoScan.value
      ? ['선택 시장에서 후보를 찾는 중', '현지 금융 뉴스를 교차 확인 중', '가격과 펀더멘털을 가져오는 중', '우량 후보를 엄격히 선별 중']
      : ['최근 기업 뉴스를 가져오는 중', '가격과 펀더멘털을 가져오는 중', '전략 점수를 계산 중', '판단과 리스크 메모를 정리 중'];
  }
  if (locale.value === 'nan-TW') {
    return isAutoScan.value
      ? ['深入掃所選市場', '交叉檢查在地財經新聞', '取得行情佮基本面', '嚴格篩選優質投資候選']
      : ['取得個股近期新聞', '取得行情佮基本面', '計算策略分數', '整理判斷佮風險提示'];
  }
  return isAutoScan.value
    ? ['正在深度掃描所選市場', '正在交叉檢查當地財經新聞源', '正在拉取行情與基本面', '正在嚴格篩選優質投資候選']
    : ['正在拉取個股近期新聞', '正在取得行情與基本面', '正在計算策略評分', '正在整理判斷與風險提示'];
});
const activeAnalysisStep = computed(() => analysisSteps.value[Math.min(loadingStepIndex.value, analysisSteps.value.length - 1)]);
const loadingElapsedLabel = computed(() => {
  if (locale.value === 'en') return `${loadingElapsedSeconds.value}s elapsed`;
  if (locale.value === 'zh-CN') return `已等待 ${loadingElapsedSeconds.value} 秒`;
  if (locale.value === 'ja') return `${loadingElapsedSeconds.value} 秒経過`;
  if (locale.value === 'ko') return `${loadingElapsedSeconds.value}초 경과`;
  if (locale.value === 'nan-TW') return `已等 ${loadingElapsedSeconds.value} 秒`;
  return `已等待 ${loadingElapsedSeconds.value} 秒`;
});

function isLocale(value: unknown): value is Locale {
  return value === 'en' || value === 'zh-CN' || value === 'zh-TW' || value === 'nan-TW' || value === 'ja' || value === 'ko';
}

function isMarket(value: unknown): value is Market {
  return defaultMarkets.includes(value as Market);
}

function isResultSortKey(value: unknown): value is ResultSortKey {
  return resultSortOptions.includes(value as ResultSortKey);
}

function isSortDirection(value: unknown): value is SortDirection {
  return value === 'asc' || value === 'desc';
}

function isDisplayMode(value: unknown): value is DisplayMode {
  return value === 'simple' || value === 'professional';
}

function isInvestmentTask(value: unknown): value is InvestmentTask {
  return investmentTasks.includes(value as InvestmentTask);
}

function normalizeWeight(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? Math.min(40, Math.max(0, value)) : null;
}

function authUserId() {
  return authSession.value?.role === 'user' ? authSession.value.user.id : 'guest';
}

function userSettingsStorageKey() {
  return `${SETTINGS_STORAGE_KEY}.${authUserId()}`;
}

function userSavedScansStorageKey() {
  return `${SAVED_SCANS_STORAGE_KEY}.${authUserId()}`;
}

function currentPersistedSettings(): PersistedSettings {
  return {
    locale: locale.value,
    selectedMarkets: selectedMarkets.value,
    selectedStrategyId: selectedStrategyId.value,
    useCustom: useCustom.value,
    customWeights: { ...customWeights },
    symbolText: symbolText.value,
    manualHoldingText: manualHoldingText.value,
    displayMode: displayMode.value,
    defaultTaskMode: activeTaskMode.value,
    defaultResultView: activeView.value,
    resultSortKey: resultSortKey.value,
    resultSortDirection: resultSortDirection.value
  };
}

function applyPersistedSettings(settings: PersistedSettings | Record<string, unknown> | undefined) {
  if (!settings || typeof settings !== 'object') return;
  const persisted = settings as PersistedSettings;
  if (isLocale(persisted.locale)) {
    locale.value = persisted.locale;
  }
  if (Array.isArray(persisted.selectedMarkets)) {
    selectedMarkets.value = persisted.selectedMarkets.filter(isMarket);
  }
  if (typeof persisted.selectedStrategyId === 'string' && persisted.selectedStrategyId) {
    selectedStrategyId.value = persisted.selectedStrategyId;
  }
  if (typeof persisted.useCustom === 'boolean') {
    useCustom.value = persisted.useCustom;
  }
  if (persisted.customWeights && typeof persisted.customWeights === 'object') {
    weightKeys.forEach((key) => {
      const value = normalizeWeight(persisted.customWeights?.[key]);
      if (value !== null) {
        customWeights[key] = value;
      }
    });
  }
  if (typeof persisted.symbolText === 'string') {
    symbolText.value = persisted.symbolText;
  }
  if (typeof persisted.manualHoldingText === 'string') {
    manualHoldingText.value = persisted.manualHoldingText;
  }
  if (isDisplayMode(persisted.displayMode)) {
    displayMode.value = persisted.displayMode;
  }
  if (isInvestmentTask(persisted.defaultTaskMode)) {
    activeInvestmentTask.value = persisted.defaultTaskMode;
  }
  if (persisted.defaultResultView === 'stocks' || persisted.defaultResultView === 'sectors') {
    activeView.value = persisted.defaultResultView;
  }
  if (isResultSortKey(persisted.resultSortKey)) {
    resultSortKey.value = persisted.resultSortKey;
  }
  if (isSortDirection(persisted.resultSortDirection)) {
    resultSortDirection.value = persisted.resultSortDirection;
  }
}

function currentUserState(): UserState {
  return {
    settings: currentPersistedSettings() as Record<string, unknown>,
    savedScans: cloneJson(savedScans.value),
    portfolio: activePortfolio.value ? cloneJson(activePortfolio.value) : null,
    portfolioMemory: cloneJson(portfolioMemory.value.slice(0, PORTFOLIO_MEMORY_LIMIT)),
    recommendationHistory: cloneJson(recommendationHistory.value.slice(0, RECOMMENDATION_HISTORY_LIMIT))
  };
}

function persistSettings() {
  if (!authSession.value || authSession.value.role !== 'user' || !userStateReady.value) return;
  const settings = currentPersistedSettings();
  try {
    localStorage.setItem(userSettingsStorageKey(), JSON.stringify(settings));
  } catch {
    // Ignore storage failures so the scanner remains usable in private or restricted contexts.
  }
  scheduleUserStateSync();
}

function refreshDataMode() {
  dataMode.value = currentDataMode();
}

function restoreSettings() {
  try {
    const raw = localStorage.getItem(userSettingsStorageKey()) ?? localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return;
    applyPersistedSettings(JSON.parse(raw) as PersistedSettings);
  } catch {
    try {
      localStorage.removeItem(userSettingsStorageKey());
    } catch {
      // Ignore storage failures so the scanner remains usable in private or restricted contexts.
    }
  }
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function restoreSavedScans() {
  try {
    const raw = localStorage.getItem(userSavedScansStorageKey()) ?? localStorage.getItem(SAVED_SCANS_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return;
    savedScans.value = parsed
      .filter((item): item is SavedScan => item && typeof item.id === 'string' && Array.isArray(item.picks))
      .slice(0, SAVED_SCAN_LIMIT);
  } catch {
    try {
      localStorage.removeItem(userSavedScansStorageKey());
    } catch {
      // Ignore storage failures so export and scanning still work.
    }
  }
}

function persistSavedScans() {
  if (!authSession.value || authSession.value.role !== 'user' || !userStateReady.value) return;
  try {
    localStorage.setItem(userSavedScansStorageKey(), JSON.stringify(savedScans.value.slice(0, SAVED_SCAN_LIMIT)));
  } catch {
    // Ignore storage failures so export and scanning still work.
  }
  scheduleUserStateSync();
}

function applySavedScans(value: unknown) {
  if (!Array.isArray(value)) return false;
  savedScans.value = value
    .filter((item): item is SavedScan => item && typeof item.id === 'string' && Array.isArray((item as SavedScan).picks))
    .slice(0, SAVED_SCAN_LIMIT);
  return true;
}

function normalizePortfolioMemoryItem(value: unknown): PortfolioMemoryItem | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as PortfolioMemoryItem;
  if (!item.id || !item.portfolio || !Array.isArray(item.portfolio.positions)) return null;
  return {
    id: String(item.id),
    savedAt: String(item.savedAt || new Date().toISOString()),
    title: String(item.title || item.sourceName || portfolioMemoryFallbackTitle(item.portfolio)),
    sourceName: String(item.sourceName || item.portfolio.sourceName || portfolioText().manualTitle),
    sourceType: String(item.sourceType || item.portfolio.sourceType || 'manual-holdings'),
    recognizedCount: Number(item.recognizedCount || item.portfolio.recognizedCount || item.portfolio.positions.length || 0),
    symbols: Array.isArray(item.symbols) ? item.symbols.map(String) : item.portfolio.positions.map((position) => position.symbol),
    totalMarketValue: Number(item.totalMarketValue || item.portfolio.totalMarketValue || 0),
    totalUnrealizedPnl: Number(item.totalUnrealizedPnl || item.portfolio.totalUnrealizedPnl || 0),
    totalUnrealizedPnlPct: item.totalUnrealizedPnlPct ?? item.portfolio.totalUnrealizedPnlPct ?? null,
    diff: item.diff ?? null,
    portfolio: cloneJson(item.portfolio)
  };
}

function applyPortfolioMemory(value: unknown) {
  if (!Array.isArray(value)) return false;
  portfolioMemory.value = value
    .map(normalizePortfolioMemoryItem)
    .filter((item): item is PortfolioMemoryItem => Boolean(item))
    .slice(0, PORTFOLIO_MEMORY_LIMIT);
  return true;
}

function applyRecommendationHistory(value: unknown) {
  if (!Array.isArray(value)) return false;
  recommendationHistory.value = value
    .filter((item): item is RecommendationHistoryItem => Boolean(item) && typeof item.id === 'string' && typeof item.symbol === 'string')
    .slice(0, RECOMMENDATION_HISTORY_LIMIT);
  return true;
}

function portfolioMemoryFallbackTitle(portfolio: PortfolioImportResponse | PortfolioAnalysis) {
  const lead = portfolio.positions[0]?.name || portfolio.positions[0]?.symbol || portfolio.sourceName;
  return `${lead} · ${portfolio.recognizedCount || portfolio.positions.length}`;
}

function portfolioMemorySnapshot(portfolio: PortfolioImportResponse | PortfolioAnalysis): PortfolioMemoryItem {
  const savedAt = new Date().toISOString();
  const symbols = portfolio.symbols?.length ? portfolio.symbols : portfolio.positions.map((position) => position.symbol);
  const previous = portfolioMemory.value[0]?.portfolio ?? null;
  return {
    id: `${Date.now()}-${symbols.slice(0, 3).join('-') || 'portfolio'}`,
    savedAt,
    title: portfolioMemoryFallbackTitle(portfolio),
    sourceName: portfolio.sourceName,
    sourceType: portfolio.sourceType,
    recognizedCount: portfolio.recognizedCount,
    symbols,
    totalMarketValue: Number(portfolio.totalMarketValue || 0),
    totalUnrealizedPnl: Number(portfolio.totalUnrealizedPnl || 0),
    totalUnrealizedPnlPct: portfolio.totalUnrealizedPnlPct ?? null,
    diff: previous ? portfolioMemoryDiff(portfolio, previous) : null,
    portfolio: cloneJson(portfolio)
  };
}

function portfolioMemoryDiff(current: PortfolioImportResponse | PortfolioAnalysis, previous: PortfolioImportResponse | PortfolioAnalysis) {
  const currentMap = new Map(current.positions.map((position) => [position.symbol, position]));
  const previousMap = new Map(previous.positions.map((position) => [position.symbol, position]));
  let quantityChanged = 0;
  let costChanged = 0;
  currentMap.forEach((position, symbol) => {
    const old = previousMap.get(symbol);
    if (!old) return;
    if (Number(position.quantity ?? 0) !== Number(old.quantity ?? 0)) quantityChanged += 1;
    if (Math.abs(Number(position.costPrice ?? 0) - Number(old.costPrice ?? 0)) >= 0.0001) costChanged += 1;
  });
  return {
    added: [...currentMap.keys()].filter((symbol) => !previousMap.has(symbol)).length,
    removed: [...previousMap.keys()].filter((symbol) => !currentMap.has(symbol)).length,
    quantityChanged,
    costChanged,
    pnlChange: Number((Number(current.totalUnrealizedPnl || 0) - Number(previous.totalUnrealizedPnl || 0)).toFixed(4))
  };
}

function rememberPortfolio(portfolio: PortfolioImportResponse | PortfolioAnalysis) {
  const snapshot = portfolioMemorySnapshot(portfolio);
  const signature = snapshot.symbols.join('|');
  portfolioMemory.value = [
    snapshot,
    ...portfolioMemory.value.filter((item) => item.symbols.join('|') !== signature)
  ].slice(0, PORTFOLIO_MEMORY_LIMIT);
}

function applyUserState(state: UserState) {
  userStateReady.value = false;
  if (!applyPortfolioMemory(state.portfolioMemory)) {
    portfolioMemory.value = [];
  }
  if (!applyRecommendationHistory(state.recommendationHistory)) {
    recommendationHistory.value = [];
  }
  if (state.settings && Object.keys(state.settings).length) {
    applyPersistedSettings(state.settings);
  } else {
    restoreSettings();
  }
  if (!applySavedScans(state.savedScans)) {
    restoreSavedScans();
  }
  if (state.portfolio && typeof state.portfolio === 'object') {
    const portfolio = cloneJson(state.portfolio as PortfolioImportResponse | PortfolioAnalysis);
    if ('matchedCount' in portfolio) {
      analysisPortfolio.value = portfolio as PortfolioAnalysis;
      importedPortfolio.value = null;
    } else {
      importedPortfolio.value = portfolio as PortfolioImportResponse;
      analysisPortfolio.value = null;
    }
    if (!portfolioMemory.value.length) rememberPortfolio(portfolio);
  }
  userStateReady.value = true;
  persistSettings();
  persistSavedScans();
}

async function loadUserState() {
  userStateError.value = '';
  try {
    applyUserState(await fetchUserState());
  } catch (cause) {
    userStateError.value = cause instanceof Error ? cause.message : 'Failed to load user state';
    userStateReady.value = true;
    restoreSettings();
    restoreSavedScans();
  }
}

function scheduleUserStateSync() {
  if (!authSession.value || authSession.value.role !== 'user' || !userStateReady.value) return;
  if (userStateSyncTimer) window.clearTimeout(userStateSyncTimer);
  userStateSyncTimer = window.setTimeout(() => {
    void persistUserStateNow();
  }, 700);
}

async function persistUserStateNow() {
  if (!authSession.value || authSession.value.role !== 'user' || !userStateReady.value) return;
  userStateSaving.value = true;
  userStateError.value = '';
  try {
    await saveUserState(currentUserState());
  } catch (cause) {
    userStateError.value = cause instanceof Error ? cause.message : 'Failed to save user state';
  } finally {
    userStateSaving.value = false;
  }
}

function normalizeStrategySelection() {
  if (!strategies.value.length) return;
  if (!strategies.value.some((strategy) => strategy.id === selectedStrategyId.value)) {
    selectedStrategyId.value = strategies.value.find((strategy) => strategy.id === 'ai_smart_blend')?.id ?? strategies.value[0].id;
  }
}

function toggleMarket(market: Market) {
  if (selectedMarkets.value.includes(market)) {
    selectedMarkets.value = selectedMarkets.value.filter((item) => item !== market);
    return;
  }
  selectedMarkets.value = [...selectedMarkets.value, market];
}

function strategyName(strategy: Strategy) {
  return strategyText[locale.value][strategy.id]?.name ?? strategy.name;
}

function strategyDescription(strategy?: Strategy) {
  if (!strategy) return '';
  return strategyText[locale.value][strategy.id]?.description ?? strategy.description;
}

function detailedWeightLabel(key: string) {
  return detailedWeightText[locale.value][key] ?? strategyLibrary.value?.detailedWeightLabels?.[key] ?? key;
}

function applyStrategyLibrary(library: StrategyLibrary) {
  if (!config.value) return;
  const runtimeStrategies = library.runtimeStrategies?.length ? library.runtimeStrategies : library.strategies;
  config.value = {
    ...config.value,
    strategies: runtimeStrategies,
    strategyLibrary: library
  };
  normalizeStrategySelection();
}

async function refreshOnlineStrategies() {
  if (refreshingStrategies.value) return;
  refreshingStrategies.value = true;
  strategyRefreshError.value = '';
  try {
    const library = await refreshStrategyLibrary();
    applyStrategyLibrary(library);
  } catch (cause) {
    strategyRefreshError.value = cause instanceof Error ? cause.message : 'Strategy refresh failed';
  } finally {
    refreshingStrategies.value = false;
    refreshDataMode();
  }
}

async function bootUserApp() {
  userStateReady.value = false;
  config.value = await fetchConfig();
  refreshDataMode();
  normalizeStrategySelection();
  await loadUserState();
}

async function resumeAuthSession() {
  const session = getAuthSession();
  if (!session) return;
  authSession.value = session;
  try {
    const valid = await fetchCurrentSession();
    if (!valid) {
      logout();
      return;
    }
    if (session.role === 'admin') {
      await loadAdminUsers();
    } else {
      await bootUserApp();
    }
  } catch {
    logout();
  }
}

async function submitAccessLogin() {
  if (authLoading.value) return;
  authLoading.value = true;
  authError.value = '';
  try {
    authSession.value = await loginWithAccessKey(accessKeyInput.value.trim());
    accessKeyInput.value = '';
    await bootUserApp();
  } catch (cause) {
    authError.value = cause instanceof Error ? cause.message : loginErrorLabel();
  } finally {
    authLoading.value = false;
  }
}

async function submitAdminLogin() {
  if (authLoading.value) return;
  authLoading.value = true;
  authError.value = '';
  try {
    authSession.value = await loginAdmin(adminUsernameInput.value.trim(), adminPasswordInput.value);
    adminPasswordInput.value = '';
    await loadAdminUsers();
  } catch (cause) {
    authError.value = cause instanceof Error ? cause.message : adminLoginErrorLabel();
  } finally {
    authLoading.value = false;
  }
}

function logout() {
  if (userStateSyncTimer) window.clearTimeout(userStateSyncTimer);
  clearAuthSession();
  setAuthSession(null);
  authSession.value = null;
  config.value = null;
  userStateReady.value = false;
  userStateError.value = '';
  savedScans.value = [];
  recommendationHistory.value = [];
  portfolioMemory.value = [];
  importedPortfolio.value = null;
  analysisPortfolio.value = null;
  picks.value = [];
  sectors.value = [];
  scanInfo.value = null;
  generatedAt.value = '';
}

async function loadAdminUsers() {
  adminLoading.value = true;
  adminError.value = '';
  try {
    adminUsers.value = await fetchAdminUsers();
  } catch (cause) {
    adminError.value = cause instanceof Error ? cause.message : adminLoadErrorLabel();
  } finally {
    adminLoading.value = false;
  }
}

async function submitNewUser() {
  if (adminLoading.value) return;
  adminLoading.value = true;
  adminError.value = '';
  try {
    await createAdminUser({
      accessKey: newUserKey.value.trim(),
      label: newUserLabel.value.trim(),
      notes: newUserNotes.value.trim(),
      enabled: newUserEnabled.value
    });
    newUserKey.value = '';
    newUserLabel.value = '';
    newUserNotes.value = '';
    newUserEnabled.value = true;
    await loadAdminUsers();
  } catch (cause) {
    adminError.value = cause instanceof Error ? cause.message : adminSaveErrorLabel();
  } finally {
    adminLoading.value = false;
  }
}

async function saveAdminUser(user: AdminUser) {
  adminError.value = '';
  try {
    const updated = await updateAdminUser(user.id, {
      label: user.label,
      notes: user.notes,
      enabled: Boolean(user.enabled)
    });
    adminUsers.value = adminUsers.value.map((item) => (item.id === updated.id ? updated : item));
  } catch (cause) {
    adminError.value = cause instanceof Error ? cause.message : adminSaveErrorLabel();
  }
}

async function resetAdminUser(user: AdminUser) {
  adminError.value = '';
  try {
    await resetAdminUserState(user.id);
    await loadAdminUsers();
  } catch (cause) {
    adminError.value = cause instanceof Error ? cause.message : adminSaveErrorLabel();
  }
}

function authHeading() {
  return localeText({ en: 'Sign in', 'zh-CN': '登入', 'zh-TW': '登入', ja: 'ログイン', ko: '로그인' });
}

function authSubheading() {
  return localeText({
    en: 'Enter your access key before using market scans, holdings, or saved research.',
    'zh-CN': '输入正确 key 后，才可以使用扫描、持仓和保存的研究资料。',
    'zh-TW': '輸入正確 key 後，才可以使用掃描、持倉和保存的研究資料。',
    ja: 'アクセスキーを入力してからスキャン、保有、保存済み研究を利用します。',
    ko: '액세스 키를 입력해야 스캔, 보유, 저장된 리서치를 사용할 수 있습니다.'
  });
}

function loginErrorLabel() {
  return localeText({ en: 'Invalid access key.', 'zh-CN': 'key 不正确或已停用。', 'zh-TW': 'key 不正確或已停用。', ja: 'キーが無効です。', ko: '키가 올바르지 않습니다.' });
}

function adminLoginErrorLabel() {
  return localeText({ en: 'Invalid administrator credentials.', 'zh-CN': '管理员账号或密码不正确。', 'zh-TW': '管理員帳號或密碼不正確。', ja: '管理者認証に失敗しました。', ko: '관리자 인증에 실패했습니다.' });
}

function adminLoadErrorLabel() {
  return localeText({ en: 'Failed to load users.', 'zh-CN': '无法载入用户。', 'zh-TW': '無法載入使用者。', ja: 'ユーザーを読み込めません。', ko: '사용자를 불러오지 못했습니다.' });
}

function adminSaveErrorLabel() {
  return localeText({ en: 'Failed to save user.', 'zh-CN': '无法保存用户。', 'zh-TW': '無法保存使用者。', ja: 'ユーザーを保存できません。', ko: '사용자를 저장하지 못했습니다.' });
}

function chartX(index: number, total: number) {
  return 40 + (index / Math.max(1, total)) * 640;
}

function chartY(value: number | null | undefined) {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return 220;
  const range = chartRange.value;
  return 220 - ((numberValue - range.min) / Math.max(0.01, range.max - range.min)) * 180;
}

function makeChartLinePath(points: StockChartPoint[]) {
  if (!points.length) return '';
  const total = Math.max(1, points.length - 1);
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${chartX(index, total).toFixed(2)} ${chartY(point.close).toFixed(2)}`).join(' ');
}

function makeChartValuePath(points: StockChartPoint[], key: 'ma5' | 'ma10' | 'ma20') {
  const total = Math.max(1, points.length - 1);
  let path = '';
  points.forEach((point, index) => {
    const value = point[key];
    if (!Number.isFinite(value)) return;
    path += `${path ? ' L' : 'M'} ${chartX(index, total).toFixed(2)} ${chartY(value).toFixed(2)}`;
  });
  return path;
}

function makeChartAreaPath(points: StockChartPoint[]) {
  const line = makeChartLinePath(points);
  if (!line || !points.length) return '';
  const total = Math.max(1, points.length - 1);
  return `${line} L ${chartX(points.length - 1, total).toFixed(2)} 220 L ${chartX(0, total).toFixed(2)} 220 Z`;
}

function chartTickLabel(point: StockChartPoint | undefined) {
  if (!point?.time) return '';
  const date = new Date(point.time);
  if (Number.isNaN(date.getTime())) return '';
  return detailChartTab.value === 'intraday'
    ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function chartChangeLabel(points: StockChartPoint[]) {
  if (points.length < 2) return '-';
  const first = points[0].close;
  const last = points[points.length - 1].close;
  if (!first) return '-';
  const change = ((last - first) / first) * 100;
  return `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
}

function chartNumberLabel(value: number | null | undefined, digits = 2) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : '-';
}

function chartVolumeLabel(value: number | null | undefined) {
  if (!Number.isFinite(value)) return '-';
  const numberValue = Number(value);
  if (numberValue >= 1_000_000_000) return `${(numberValue / 1_000_000_000).toFixed(2)}B`;
  if (numberValue >= 1_000_000) return `${(numberValue / 1_000_000).toFixed(2)}M`;
  if (numberValue >= 1_000) return `${(numberValue / 1_000).toFixed(1)}K`;
  return numberValue.toFixed(0);
}

function chartTooltipRows(point: StockChartPoint) {
  const rows = [
    ['Open', chartNumberLabel(point.open)],
    ['High', chartNumberLabel(point.high)],
    ['Low', chartNumberLabel(point.low)],
    ['Close', chartNumberLabel(point.close)],
    ['Volume', chartVolumeLabel(point.volume)]
  ];
  if (Number.isFinite(point.ma5)) rows.push(['MA5', chartNumberLabel(point.ma5)]);
  if (Number.isFinite(point.ma10)) rows.push(['MA10', chartNumberLabel(point.ma10)]);
  if (Number.isFinite(point.ma20)) rows.push(['MA20', chartNumberLabel(point.ma20)]);
  if (Number.isFinite(point.limitUpPrice)) rows.push([strategyUi.value.limitUp, chartNumberLabel(point.limitUpPrice)]);
  return rows;
}

function chartPointTimeLabel(point: StockChartPoint) {
  if (!point.time) return '';
  const date = new Date(point.time);
  if (Number.isNaN(date.getTime())) return point.time;
  return detailChartTab.value === 'intraday'
    ? date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
}

function updateChartPointer(event: MouseEvent | TouchEvent) {
  const svg = chartSvgRef.value;
  const points = visibleChartPoints.value;
  if (!svg || !points.length) return;
  const rect = svg.getBoundingClientRect();
  const clientX = 'touches' in event ? event.touches[0]?.clientX : event.clientX;
  if (clientX === undefined) return;
  const x = ((clientX - rect.left) / Math.max(1, rect.width)) * 720;
  const clamped = Math.min(680, Math.max(40, x));
  const index = Math.round(((clamped - 40) / 640) * Math.max(1, points.length - 1));
  chartPointerIndex.value = Math.min(points.length - 1, Math.max(0, index));
}

function clearChartPointer() {
  chartPointerIndex.value = null;
}

async function openStockDetail(pick: Pick, tab: ChartTab = 'intraday') {
  detailPick.value = pick;
  detailChartTab.value = tab;
  detailChart.value = null;
  detailChartError.value = '';
  chartPointerIndex.value = null;
  detailChartLoading.value = true;
  try {
    detailChart.value = await fetchStockChart(pick.symbol);
  } catch (cause) {
    detailChartError.value = cause instanceof Error ? cause.message : strategyUi.value.chartUnavailable;
  } finally {
    detailChartLoading.value = false;
    refreshDataMode();
  }
}

function closeStockDetail() {
  detailPick.value = null;
  detailChart.value = null;
  detailChartError.value = '';
}

function marketLabel(market: Market) {
  return marketLabels[locale.value][market] ?? market;
}

function selectInvestmentTask(task: InvestmentTask) {
  activeInvestmentTask.value = task;
  activeView.value = 'stocks';
  if (task !== 'shortTerm' && resultVerdictFilter.value === 't') resultVerdictFilter.value = 'all';
  if (task === 'portfolio') {
    activeWorkbenchBucket.value = 'holdings';
    resultMarketFilter.value = 'all';
    resultSortKey.value = 'decision';
  }
  if (task === 'etf') {
    activeWorkbenchBucket.value = 'etf';
    resultSortKey.value = 'decision';
  }
  if (task === 'shortTerm') {
    activeWorkbenchBucket.value = 'all';
    resultVerdictFilter.value = 't';
    resultSortKey.value = 'tScore';
  }
  if (task === 'discover') {
    activeWorkbenchBucket.value = 'buy';
    resultSortKey.value = 'decision';
  }
}

function controlPanelTitle() {
  return localeText({
    en: 'Investment task',
    'zh-CN': '投资任务',
    'zh-TW': '投資任務',
    ja: '投資タスク',
    ko: '투자 작업'
  });
}

function investmentTaskLabel(task: InvestmentTask) {
  const labels: Record<InvestmentTask, LocalizedText> = {
    discover: { en: 'Full-market ideas', 'zh-CN': '全市场找股', 'zh-TW': '全市場找股', ja: '市場全体探索', ko: '전체 시장 탐색' },
    portfolio: { en: 'Holdings workbench', 'zh-CN': '持仓工作台', 'zh-TW': '持倉工作台', ja: '保有ワークベンチ', ko: '보유 워크벤치' },
    etf: { en: 'ETF screen', 'zh-CN': 'ETF 筛选', 'zh-TW': 'ETF 篩選', ja: 'ETF選別', ko: 'ETF 선별' },
    shortTerm: { en: 'Short-term / T+1', 'zh-CN': '短线/T+1', 'zh-TW': '短線/T+1', ja: '短期/T+1', ko: '단기/T+1' }
  };
  return localeText(labels[task]);
}

function investmentTaskHint(task: InvestmentTask) {
  const labels: Record<InvestmentTask, LocalizedText> = {
    discover: { en: 'Find investable candidates', 'zh-CN': '寻找值得研究的优质候选', 'zh-TW': '尋找值得研究的優質候選', ja: '投資候補を探す', ko: '투자 후보 찾기' },
    portfolio: { en: 'Today actions and risk', 'zh-CN': '今日动作与风险', 'zh-TW': '今日動作與風險', ja: '本日の対応とリスク', ko: '오늘 조치와 리스크' },
    etf: { en: 'Core or tactical funds', 'zh-CN': '核心或战术 ETF', 'zh-TW': '核心或戰術 ETF', ja: 'コア/戦術ETF', ko: '핵심/전술 ETF' },
    shortTerm: { en: 'Liquidity and execution', 'zh-CN': '流动性与执行限制', 'zh-TW': '流動性與執行限制', ja: '流動性と執行制限', ko: '유동성과 실행 제한' }
  };
  return localeText(labels[task]);
}

function profileForMarket(market: Market) {
  return marketProfiles.value[market] ?? scanInfo.value?.marketProfiles?.[market];
}

function marketCoverageTierLabel(tier: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    'local-deep': { en: 'Local deep', 'zh-CN': '本地深度', 'zh-TW': '本地深度', ja: 'ローカル深度', ko: '로컬 심층' },
    regional: { en: 'Regional', 'zh-CN': '区域增强', 'zh-TW': '區域增強', ja: '地域強化', ko: '지역 강화' },
    global: { en: 'Global', 'zh-CN': '全球基础', 'zh-TW': '全球基礎', ja: 'グローバル', ko: '글로벌' },
    basic: { en: 'Basic', 'zh-CN': '基础可用', 'zh-TW': '基礎可用', ja: '基本', ko: '기본' }
  };
  return localeText(labels[tier || 'basic'] ?? labels.basic);
}

function marketCoverageLabel(market: Market) {
  const profile = profileForMarket(market);
  if (!profile) return marketCoverageTierLabel('basic');
  const score = Number(profile.sourceReliabilityScore ?? 0);
  const suffix = Number.isFinite(score) && score > 0 ? ` · ${marketReliabilityLabel(score)}` : '';
  return `${marketCoverageTierLabel(profile.coverageTier)}${suffix}`;
}

function marketReliabilityLabel(score: number) {
  const value = score.toFixed(0);
  if (locale.value === 'en') return `source ${value}`;
  if (locale.value === 'zh-CN') return `资料源 ${value}`;
  if (locale.value === 'ja') return `情報源 ${value}`;
  if (locale.value === 'ko') return `데이터원 ${value}`;
  return `資料源 ${value}`;
}

function marketSupportTitle() {
  return localeText({
    en: 'Market data layer',
    'zh-CN': '市场资料层',
    'zh-TW': '市場資料層',
    ja: '市場データ層',
    ko: '시장 데이터층'
  });
}

function marketSourceStackLabel(pick: Pick) {
  const support = pick.decisionEngine?.marketSupport;
  const sources = support?.sources?.filter(Boolean).slice(0, 2);
  if (sources?.length) return sources.join(' / ');
  return marketCoverageTierLabel(support?.coverageTier ?? profileForMarket(pick.market)?.coverageTier);
}

function taskInputTitle() {
  if (activeInvestmentTask.value === 'portfolio') {
    return localeText({ en: 'Holdings source', 'zh-CN': '持仓来源', 'zh-TW': '持倉來源', ja: '保有データ元', ko: '보유 출처' });
  }
  if (activeInvestmentTask.value === 'etf') {
    return localeText({ en: 'ETF universe', 'zh-CN': 'ETF 股票池', 'zh-TW': 'ETF 股票池', ja: 'ETFユニバース', ko: 'ETF 유니버스' });
  }
  if (activeInvestmentTask.value === 'shortTerm') {
    return localeText({ en: 'Short-term universe', 'zh-CN': '短线观察池', 'zh-TW': '短線觀察池', ja: '短期ウォッチ対象', ko: '단기 관찰군' });
  }
  return localeText({ en: 'Market universe', 'zh-CN': '全市场股票池', 'zh-TW': '全市場股票池', ja: '市場ユニバース', ko: '시장 유니버스' });
}

function pickMatchesWorkbenchBucket(pick: Pick, bucket: WorkbenchBucket) {
  if (bucket === 'all') return true;
  if (bucket === 'etf') return pick.instrumentType === 'etf';
  if (bucket === 'holdings') return Boolean(pick.holding && pick.holdingAnalysis);
  const action = pick.finalDecision?.action ?? pick.decisionEngine?.action;
  if (bucket === 'buy') return finalVerdictBucket(pick) === 'buy' || action === 'accumulate';
  if (bucket === 'risk') return finalVerdictBucket(pick) === 'sell' || action === 'reduce' || action === 'exit';
  if (bucket === 'hold') return finalVerdictBucket(pick) === 'watch' && action !== 'reduce' && action !== 'exit';
  return true;
}

function workbenchBucketLabel(bucket: WorkbenchBucket) {
  const labels: Record<WorkbenchBucket, LocalizedText> = {
    all: { en: 'All', 'zh-CN': '全部', 'zh-TW': '全部', ja: 'すべて', ko: '전체' },
    buy: { en: 'Worth buying', 'zh-CN': '值得买入', 'zh-TW': '值得買入', ja: '買い候補', ko: '매수 가치' },
    hold: { en: 'Hold / watch', 'zh-CN': '持有观察', 'zh-TW': '持有觀察', ja: '保有/監視', ko: '보유/관찰' },
    risk: { en: 'Reduce / exit', 'zh-CN': '减仓/退出', 'zh-TW': '減倉/退出', ja: '縮小/退出', ko: '축소/청산' },
    etf: { en: 'ETF', 'zh-CN': 'ETF', 'zh-TW': 'ETF', ja: 'ETF', ko: 'ETF' },
    holdings: { en: 'Holdings', 'zh-CN': '已持仓', 'zh-TW': '已持倉', ja: '保有中', ko: '보유' }
  };
  return localeText(labels[bucket]);
}

function workbenchBucketHint(bucket: WorkbenchBucket) {
  const labels: Record<WorkbenchBucket, LocalizedText> = {
    all: { en: 'Full result set', 'zh-CN': '完整结果', 'zh-TW': '完整結果', ja: '全結果', ko: '전체 결과' },
    buy: { en: 'Action is accumulate or buy', 'zh-CN': '买入/分批买入', 'zh-TW': '買入/分批買入', ja: '買い/積み増し', ko: '매수/분할 매수' },
    hold: { en: 'No urgent action', 'zh-CN': '无需急动', 'zh-TW': '無需急動', ja: '急ぎなし', ko: '긴급 조치 없음' },
    risk: { en: 'Reduce or exit signal', 'zh-CN': '减仓/退出信号', 'zh-TW': '減倉/退出訊號', ja: '縮小/撤退', ko: '축소/청산 신호' },
    etf: { en: 'ETF only', 'zh-CN': '只看 ETF', 'zh-TW': '只看 ETF', ja: 'ETFのみ', ko: 'ETF만' },
    holdings: { en: 'With cost and size', 'zh-CN': '含成本仓位', 'zh-TW': '含成本倉位', ja: 'コスト/数量あり', ko: '원가/수량 포함' }
  };
  return localeText(labels[bucket]);
}

function decisionWorkbenchTitle() {
  return localeText({
    en: 'Decision workbench',
    'zh-CN': '决策工作台',
    'zh-TW': '決策工作台',
    ja: '判断ワークベンチ',
    ko: '의사결정 워크벤치'
  });
}

function workbenchSubtitle() {
  const universe = scanUniverse.value;
  if (!universe) {
    if (locale.value === 'en') return 'Run a scan to split candidates by decision, ETF, and holdings.';
    if (locale.value === 'zh-CN') return '开始扫描后会按决策、ETF、持仓分流。';
    if (locale.value === 'ja') return 'スキャン後、判断・ETF・保有で分流します。';
    if (locale.value === 'ko') return '스캔 후 의사결정, ETF, 보유로 분류합니다.';
    return '開始掃描後會按決策、ETF、持倉分流。';
  }
  return `${scanUniverseModeLabel(universe.mode)} · ${universe.candidatePoolSize} ${scanUniverseMetricLabel('candidatePoolSize')} · ${universe.deepAnalysisCount} ${scanUniverseMetricLabel('deepAnalysisCount')}`;
}

function holdingCommandTitle() {
  return localeText({
    en: 'Holdings workbench',
    'zh-CN': '持仓工作台',
    'zh-TW': '持倉工作台',
    ja: '保有ワークベンチ',
    ko: '보유 워크벤치'
  });
}

function activeResultTitle() {
  if (activeTaskMode.value === 'portfolio') return holdingCommandTitle();
  if (activeTaskMode.value === 'etf') return localeText({ en: 'ETF candidates', 'zh-CN': 'ETF 候选', 'zh-TW': 'ETF 候選', ja: 'ETF候補', ko: 'ETF 후보' });
  if (activeTaskMode.value === 'shortTerm') return localeText({ en: 'Short-term watchlist', 'zh-CN': '短线观察', 'zh-TW': '短線觀察', ja: '短期ウォッチ', ko: '단기 관찰' });
  return t.value.topIdeas;
}

function portfolioWorkbenchSubtitle() {
  if (activePortfolio.value) return holdingCommandSubtitle();
  return localeText({
    en: 'Import or restore holdings first, then run a holdings check.',
    'zh-CN': '先导入或恢复持仓，再检查今天能做什么。',
    'zh-TW': '先匯入或恢復持倉，再檢查今天能做什麼。',
    ja: '保有を取り込むか復元してから、本日の対応を点検します。',
    ko: '보유를 가져오거나 복원한 뒤 오늘 가능한 조치를 점검합니다.'
  });
}

function portfolioEmptyTitle() {
  return localeText({
    en: 'No holdings loaded',
    'zh-CN': '还没有持仓数据',
    'zh-TW': '還沒有持倉資料',
    ja: '保有データがありません',
    ko: '보유 데이터가 없습니다'
  });
}

function portfolioEmptyHint() {
  return localeText({
    en: 'Use the holdings source panel to paste, upload, or restore a recent snapshot.',
    'zh-CN': '请在左侧持仓来源中粘贴、上传，或恢复最近快照。',
    'zh-TW': '請在左側持倉來源中貼上、上傳，或恢復最近快照。',
    ja: '左側の保有データ元で貼り付け、アップロード、または最近のスナップショットを復元してください。',
    ko: '왼쪽 보유 출처에서 붙여넣기, 업로드 또는 최근 스냅샷 복원을 사용하세요.'
  });
}

function portfolioSourceCtaLabel() {
  return portfolioMemory.value.length
    ? localeText({ en: 'Restore a snapshot or import new holdings', 'zh-CN': '恢复快照或导入新持仓', 'zh-TW': '恢復快照或匯入新持倉', ja: 'スナップショット復元または新規取込', ko: '스냅샷 복원 또는 새 보유 가져오기' })
    : localeText({ en: 'Import holdings to start', 'zh-CN': '导入持仓后开始', 'zh-TW': '匯入持倉後開始', ja: '保有を取り込んで開始', ko: '보유를 가져와 시작' });
}

function portfolioDashboardMetricLabel(key: PortfolioDashboardMetricKey) {
  const labels: Record<PortfolioDashboardMetricKey, LocalizedText> = {
    marketValue: { en: 'Market value', 'zh-CN': '总市值', 'zh-TW': '總市值', ja: '評価額', ko: '평가금액' },
    pnl: { en: 'Total P/L', 'zh-CN': '总盈亏', 'zh-TW': '總損益', ja: '総損益', ko: '총 손익' },
    sellable: { en: 'Sellable today', 'zh-CN': '今日可卖', 'zh-TW': '今日可賣', ja: '本日売却可', ko: '오늘 매도 가능' },
    locked: { en: 'T+1 locked', 'zh-CN': 'T+1 锁定', 'zh-TW': 'T+1 鎖定', ja: 'T+1 制限', ko: 'T+1 잠김' },
    risk: { en: 'Reduce / exit', 'zh-CN': '建议减仓/退出', 'zh-TW': '建議減倉/退出', ja: '縮小/撤退推奨', ko: '축소/청산 제안' },
    observe: { en: 'Observe', 'zh-CN': '只观察', 'zh-TW': '只觀察', ja: '観察のみ', ko: '관찰만' }
  };
  return localeText(labels[key]);
}

function portfolioPositionUnitLabel() {
  return localeText({ en: 'positions', 'zh-CN': '只持仓', 'zh-TW': '檔持倉', ja: '保有', ko: '보유' });
}

function portfolioObserveDetailLabel() {
  return localeText({ en: 'no action', 'zh-CN': '无需操作', 'zh-TW': '無需操作', ja: '対応不要', ko: '조치 없음' });
}

function portfolioActionBoardTitle() {
  return localeText({ en: 'Today operations', 'zh-CN': '今日持仓操作台', 'zh-TW': '今日持倉操作台', ja: '本日の保有操作', ko: '오늘 보유 작업대' });
}

function portfolioHoldingRowsTitle() {
  return localeText({ en: 'Holding details', 'zh-CN': '个股持仓明细', 'zh-TW': '個股持倉明細', ja: '保有明細', ko: '보유 상세' });
}

function displayModeLabel(mode: DisplayMode = displayMode.value) {
  if (mode === 'professional') {
    return localeText({ en: 'Professional', 'zh-CN': '专业', 'zh-TW': '專業', ja: 'プロ', ko: '전문' });
  }
  return localeText({ en: 'Simple', 'zh-CN': '简洁', 'zh-TW': '簡潔', ja: '簡潔', ko: '간결' });
}

function displayModeHint() {
  return isProfessionalMode.value
    ? localeText({
        en: 'Full factors and diagnostics',
        'zh-CN': '展开完整指标和诊断',
        'zh-TW': '展開完整指標和診斷',
        ja: '全指標と診断を表示',
        ko: '전체 지표와 진단 표시'
      })
    : localeText({
        en: 'Conclusion first',
        'zh-CN': '结论优先',
        'zh-TW': '結論優先',
        ja: '結論優先',
        ko: '결론 우선'
      });
}

function detailAnalysisLabel() {
  return localeText({
    en: 'Detailed analysis',
    'zh-CN': '详细分析',
    'zh-TW': '詳細分析',
    ja: '詳細分析',
    ko: '상세 분석'
  });
}

function marketRuleStateLabel(pick: Pick) {
  const state = pick.marketRuleState ?? pick.decisionEngine?.marketRuleState;
  if (!state) return marketCoverageTierLabel(pick.decisionEngine?.marketSupport?.coverageTier);
  const statusLabels: Record<string, LocalizedText> = {
    regular: { en: 'Trading', 'zh-CN': '交易中', 'zh-TW': '交易中', ja: '取引中', ko: '거래 중' },
    opening_confirmation: { en: 'Opening check', 'zh-CN': '开盘确认中', 'zh-TW': '開盤確認中', ja: '寄付き確認中', ko: '개장 확인' },
    lunch_break: { en: 'Lunch break', 'zh-CN': '午休', 'zh-TW': '午休', ja: '昼休み', ko: '점심 휴장' },
    closed: { en: 'Closed', 'zh-CN': '闭市', 'zh-TW': '閉市', ja: '休場/時間外', ko: '장외' },
    unknown: { en: 'Rule basic', 'zh-CN': '基础规则', 'zh-TW': '基礎規則', ja: '基本ルール', ko: '기본 규칙' }
  };
  const depth = state.ruleDepth === 'deep'
    ? localeText({ en: 'deep rules', 'zh-CN': '深度规则', 'zh-TW': '深度規則', ja: '深い規則', ko: '심층 규칙' })
    : localeText({ en: 'basic rules', 'zh-CN': '基础规则', 'zh-TW': '基礎規則', ja: '基本規則', ko: '기본 규칙' });
  return `${localeText(statusLabels[state.status] ?? statusLabels.unknown)} · ${depth}`;
}

function marketRuleStateTone(pick: Pick) {
  const state = pick.marketRuleState ?? pick.decisionEngine?.marketRuleState;
  if (!state) return 'basic';
  if (state.status === 'regular' && state.openConfirmed) return 'regular';
  if (state.status === 'opening_confirmation') return 'opening';
  if (state.status === 'closed' || state.status === 'lunch_break') return 'closed';
  return state.ruleDepth === 'deep' ? 'opening' : 'basic';
}

function decisionExecutionLabel(pick: Pick) {
  const execution = pick.finalDecision?.execution;
  if (!execution || execution.status === 'not_applicable') return decisionActionLabel(pick.finalDecision?.action ?? pick.decisionEngine?.action);
  return holdingExecutionStatusLabel(execution.status);
}

function conciseReasonItems(pick: Pick) {
  const gateReasons = pick.decisionEngine?.gates?.slice(0, 3).map((gate) => decisionGateLabel(gate.key)) ?? [];
  if (gateReasons.length) return gateReasons;
  const finalReasons = pick.finalDecision?.primaryReasons?.slice(0, 3).map((reason) => decisionReasonLabel(reason)) ?? [];
  if (finalReasons.length) return finalReasons;
  return reportSupportItems(pick).slice(0, 3);
}

function holdingCommandSubtitle() {
  return localeText({
    en: 'Focus on risk actions, T+1 availability, and executable share changes.',
    'zh-CN': '优先看风险动作、T+1 可用量、以及今天真正可执行的股数。',
    'zh-TW': '優先看風險動作、T+1 可用量，以及今天真正可執行的股數。',
    ja: 'リスク対応、T+1 の売却可否、実行可能な数量を優先表示します。',
    ko: '리스크 조치, T+1 가능 수량, 오늘 실행 가능한 수량을 우선 표시합니다.'
  });
}

function holdingCommandMetricLabel(key: 'positions' | 'risk' | 'blocked' | 'planned' | 'executable') {
  const labels: Record<typeof key, LocalizedText> = {
    positions: { en: 'Holdings checked', 'zh-CN': '已检查持仓', 'zh-TW': '已檢查持倉', ja: '点検済み保有', ko: '점검 보유' },
    risk: { en: 'Reduce / exit', 'zh-CN': '减仓/退出', 'zh-TW': '減倉/退出', ja: '縮小/撤退', ko: '축소/청산' },
    blocked: { en: 'T+1 blocked', 'zh-CN': 'T+1 锁定', 'zh-TW': 'T+1 鎖定', ja: 'T+1 売却不可', ko: 'T+1 잠김' },
    planned: { en: 'Planned sell', 'zh-CN': '计划卖出', 'zh-TW': '計劃賣出', ja: '計画売却', ko: '계획 매도' },
    executable: { en: 'Executable today', 'zh-CN': '今日可执行', 'zh-TW': '今日可執行', ja: '本日実行可', ko: '오늘 실행' }
  };
  return localeText(labels[key]);
}

function holdingActionListTitle() {
  return localeText({ en: 'Today action list', 'zh-CN': '今日操作清单', 'zh-TW': '今日操作清單', ja: '本日の操作リスト', ko: '오늘 조치 목록' });
}

function holdingActionItemLabel(item: HoldingActionItem) {
  const action = holdingActionDisplayLabel(item.action);
  const execution = holdingExecutionStatusLabel(item.executionStatus);
  const planned = holdingPlannedQuantityDisplay(item.plannedQuantityChange);
  const executable = holdingExecutableQuantityDisplay(item.executableQuantityChange, item.executionStatus);
  if (locale.value === 'en') return `${action} · planned ${planned} · executable ${executable} · ${execution}`;
  if (locale.value === 'zh-CN') return `${action} · 计划 ${planned} · 可执行 ${executable} · ${execution}`;
  if (locale.value === 'ja') return `${action} · 計画 ${planned} · 実行可 ${executable} · ${execution}`;
  if (locale.value === 'ko') return `${action} · 계획 ${planned} · 실행 ${executable} · ${execution}`;
  return `${action} · 計劃 ${planned} · 可執行 ${executable} · ${execution}`;
}

function recommendationReviewTitle() {
  return localeText({ en: 'Recommendation review', 'zh-CN': '推荐复盘', 'zh-TW': '推薦複盤', ja: '推奨レビュー', ko: '추천 리뷰' });
}

function recommendationReviewHint() {
  return localeText({
    en: 'Saved buy calls compared with prices in the current scan.',
    'zh-CN': '用当前扫描价格回看已保存买入建议。',
    'zh-TW': '用目前掃描價格回看已保存買入建議。',
    ja: '保存済み買い判断を現在価格で確認します。',
    ko: '저장된 매수 판단을 현재 가격과 비교합니다.'
  });
}

function recommendationReviewMetricLabel(key: 'reviewed' | 'wins' | 'avg' | 'worst') {
  const labels: Record<typeof key, LocalizedText> = {
    reviewed: { en: 'Reviewed', 'zh-CN': '已复盘', 'zh-TW': '已複盤', ja: '確認済み', ko: '검토' },
    wins: { en: 'Positive', 'zh-CN': '为正', 'zh-TW': '為正', ja: 'プラス', ko: '플러스' },
    avg: { en: 'Average', 'zh-CN': '平均', 'zh-TW': '平均', ja: '平均', ko: '평균' },
    worst: { en: 'Worst', 'zh-CN': '最差', 'zh-TW': '最差', ja: '最悪', ko: '최저' }
  };
  return localeText(labels[key]);
}

function quoteConsensusLabel(status: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    aligned: { en: 'Quote aligned', 'zh-CN': '报价一致', 'zh-TW': '報價一致', ja: '価格一致', ko: '호가 일치' },
    delayed: { en: 'Delayed quote', 'zh-CN': '延迟报价', 'zh-TW': '延遲報價', ja: '遅延価格', ko: '지연 호가' },
    fallback: { en: 'Fallback quote', 'zh-CN': '备用报价', 'zh-TW': '備援報價', ja: '代替価格', ko: '대체 호가' },
    divergent: { en: 'Quote drift', 'zh-CN': '报价偏差', 'zh-TW': '報價偏差', ja: '価格乖離', ko: '호가 편차' },
    conflict: { en: 'Quote conflict', 'zh-CN': '报价冲突', 'zh-TW': '報價衝突', ja: '価格衝突', ko: '호가 충돌' }
  };
  return localeText(labels[status || 'fallback'] ?? labels.fallback);
}

function quoteConsensusHint(pick: Pick) {
  const consensus = pick.quoteConsensus;
  if (!consensus) return marketSourceStackLabel(pick);
  const deviation = `${Number(consensus.maxDeviationPct || 0).toFixed(1)}%`;
  if (locale.value === 'en') return `${consensus.primarySource} · ${consensus.observationCount} checks · max drift ${deviation}`;
  if (locale.value === 'zh-CN') return `${consensus.primarySource} · ${consensus.observationCount} 个校验 · 最大偏差 ${deviation}`;
  if (locale.value === 'ja') return `${consensus.primarySource} · ${consensus.observationCount} 件確認 · 最大乖離 ${deviation}`;
  if (locale.value === 'ko') return `${consensus.primarySource} · ${consensus.observationCount}개 확인 · 최대 편차 ${deviation}`;
  return `${consensus.primarySource} · ${consensus.observationCount} 個校驗 · 最大偏差 ${deviation}`;
}

function sourceRoleLabel(role: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    'market-wide': { en: 'market-wide', 'zh-CN': '全市场', 'zh-TW': '全市場', ja: '市場全体', ko: '시장 전체' },
    fallback: { en: 'fallback', 'zh-CN': 'fallback', 'zh-TW': 'fallback', ja: 'fallback', ko: 'fallback' },
    requested: { en: 'requested', 'zh-CN': '指定', 'zh-TW': '指定', ja: '指定', ko: '지정' },
    portfolio: { en: 'portfolio', 'zh-CN': '持仓', 'zh-TW': '持倉', ja: '保有', ko: '보유' },
    local: { en: 'local', 'zh-CN': '本地', 'zh-TW': '本地', ja: 'ローカル', ko: '로컬' }
  };
  return localeText(labels[role || 'requested'] ?? labels.requested);
}

function scanUniverseModeLabel(mode: string | undefined) {
  if (mode === 'portfolio-holdings') {
    return localeText({ en: 'Holdings review', 'zh-CN': '持仓检查', 'zh-TW': '持倉檢查', ja: '保有点検', ko: '보유 점검' });
  }
  if (mode === 'manual-symbols') {
    return localeText({ en: 'Manual symbols', 'zh-CN': '指定股票', 'zh-TW': '指定股票', ja: '指定銘柄', ko: '지정 종목' });
  }
  return localeText({ en: 'Market-wide candidate pool', 'zh-CN': '全市场候选池', 'zh-TW': '全市場候選池', ja: '市場全体候補', ko: '시장 전체 후보' });
}

function scanUniverseMetricLabel(metric: string) {
  const labels: Record<string, LocalizedText> = {
    candidatePoolSize: { en: 'candidates', 'zh-CN': '候选', 'zh-TW': '候選', ja: '候補', ko: '후보' },
    deepAnalysisCount: { en: 'deep analyzed', 'zh-CN': '深度分析', 'zh-TW': '深度分析', ja: '深掘り分析', ko: '심층 분석' },
    displayedCount: { en: 'shown', 'zh-CN': '显示', 'zh-TW': '顯示', ja: '表示', ko: '표시' },
    sourceBreakdown: { en: 'sources', 'zh-CN': '来源', 'zh-TW': '來源', ja: '情報源', ko: '출처' }
  };
  return localeText(labels[metric] ?? labels.candidatePoolSize);
}

function scanUniverseSourcePreview() {
  const sources = scanUniverse.value?.sourceBreakdown ?? [];
  if (!sources.length) return '-';
  return sources.slice(0, 2).map((source) => `${source.label} ${source.count}`).join(' · ');
}

function scanUniverseFallbackLabel() {
  const active = Boolean(scanUniverse.value?.fallbackActive);
  if (active) {
    return localeText({ en: 'Fallback used', 'zh-CN': '已使用 fallback', 'zh-TW': '已使用 fallback', ja: 'fallback使用', ko: 'fallback 사용' });
  }
  return localeText({ en: 'No fallback', 'zh-CN': '未用 fallback', 'zh-TW': '未用 fallback', ja: 'fallbackなし', ko: 'fallback 없음' });
}

function fullMarketAssuranceLabel() {
  const universe = scanUniverse.value;
  if (!universe) {
    return localeText({ en: 'Awaiting scan evidence', 'zh-CN': '等待扫描证据', 'zh-TW': '等待掃描證據', ja: 'スキャン根拠待ち', ko: '스캔 근거 대기' });
  }
  if (universe.fullMarketSourceActive) {
    return localeText({ en: 'Market-wide source active', 'zh-CN': '全市场来源已启用', 'zh-TW': '全市場來源已啟用', ja: '市場全体情報源が有効', ko: '시장 전체 출처 활성' });
  }
  return scanUniverseModeLabel(universe.mode);
}

function verdictLabel(verdict: Pick['verdict']) {
  return t.value[verdict];
}

function overallSuitabilityLabel(suitability: OverallSuitability) {
  if (suitability === 'strongBuy' || suitability === 'buy') return t.value.buy;
  if (suitability === 'watch') return t.value.watch;
  if (suitability === 'sell') return t.value.sell;
  if (locale.value === 'en') return 'Avoid new buy';
  if (locale.value === 'zh-CN') return '暂不买入';
  if (locale.value === 'ja') return '新規買い見送り';
  if (locale.value === 'ko') return '신규 매수 보류';
  return '暫不買入';
}

function finalVerdictLabel(pick: Pick) {
  if (pick.finalDecision) return decisionActionLabel(pick.finalDecision.action);
  if (pick.decisionEngine) return decisionActionLabel(pick.decisionEngine.action);
  return pick.overallAssessment ? overallSuitabilityLabel(pick.overallAssessment.suitability) : verdictLabel(pick.verdict);
}

function finalVerdictBucket(pick: Pick): Pick['verdict'] {
  if (pick.finalDecision?.verdict) return pick.finalDecision.verdict;
  if (pick.finalDecision?.action === 'accumulate') return 'buy';
  if (pick.finalDecision?.action === 'exit') return 'sell';
  if (pick.decisionEngine?.action === 'accumulate') return 'buy';
  if (pick.decisionEngine?.action === 'exit') return 'sell';
  const suitability = pick.overallAssessment?.suitability;
  if (suitability === 'strongBuy' || suitability === 'buy') return 'buy';
  if (suitability === 'sell') return 'sell';
  if (suitability === 'avoid' || suitability === 'watch') return 'watch';
  return pick.verdict;
}

function allMarketsFilterLabel() {
  if (locale.value === 'en') return 'All markets';
  if (locale.value === 'zh-CN') return '全部市场';
  if (locale.value === 'ja') return 'すべての市場';
  if (locale.value === 'ko') return '전체 시장';
  if (locale.value === 'nan-TW') return '全部市場';
  return '全部市場';
}

function resultVerdictFilterLabel(option: ResultVerdictFilter) {
  if (option === 't') {
    if (locale.value === 'en') return 'T candidates';
    if (locale.value === 'zh-CN') return '做T候选';
    if (locale.value === 'ja') return 'T候補';
    if (locale.value === 'ko') return 'T 후보';
    if (locale.value === 'nan-TW') return '做T候選';
    return '做T候選';
  }
  if (option !== 'all') return verdictLabel(option);
  if (locale.value === 'en') return 'All calls';
  if (locale.value === 'zh-CN') return '全部判断';
  if (locale.value === 'ja') return 'すべての判断';
  if (locale.value === 'ko') return '전체 판단';
  if (locale.value === 'nan-TW') return '全部判斷';
  return '全部判斷';
}

function resultSortLabel(option: ResultSortKey) {
  const labels: Record<ResultSortKey, Partial<Record<Locale, string>> & { en: string }> = {
    recommended: { en: 'AI recommended', 'zh-CN': 'AI 推荐顺序', 'zh-TW': 'AI 推薦順序', 'nan-TW': 'AI 推薦順序', ja: 'AI 推奨順', ko: 'AI 추천순' },
    decision: { en: 'Decision rank', 'zh-CN': '决策排序', 'zh-TW': '決策排序', 'nan-TW': '決策排序', ja: '判断順位', ko: '의사결정 순위' },
    overall: { en: 'Final total', 'zh-CN': '最终总评', 'zh-TW': '最終總評', 'nan-TW': '最終總評', ja: '最終評価', ko: '최종 종합' },
    score: { en: 'Base score', 'zh-CN': '原始评分', 'zh-TW': '原始評分', 'nan-TW': '原始評分', ja: '基本スコア', ko: '기본 점수' },
    todayBuy: { en: 'Worth buying today', 'zh-CN': '今日买入', 'zh-TW': '今日買入', 'nan-TW': '今仔日買', ja: '本日買い', ko: '오늘 매수' },
    futureRise: { en: 'Future rise', 'zh-CN': '未来上涨', 'zh-TW': '未來上漲', 'nan-TW': '後勢上漲', ja: '将来上昇', ko: '향후 상승' },
    profitableExit: { en: 'Profitable exit', 'zh-CN': '盈利卖出', 'zh-TW': '盈利賣出', 'nan-TW': '趁錢賣出', ja: '利益確定', ko: '수익 매도' },
    newsHeat: { en: 'News heat', 'zh-CN': '新闻热度', 'zh-TW': '新聞熱度', 'nan-TW': '新聞熱度', ja: 'ニュース熱量', ko: '뉴스 열기' },
    continuation: { en: 'Next-session continuation', 'zh-CN': '次日延续', 'zh-TW': '隔日延續', 'nan-TW': '隔日延續', ja: '翌日継続', ko: '다음 세션 지속' },
    riskLow: { en: 'Lowest risk', 'zh-CN': '风险最低', 'zh-TW': '風險最低', 'nan-TW': '風險上低', ja: '低リスク', ko: '낮은 리스크' },
    tScore: { en: 'T suitability', 'zh-CN': '做T适配', 'zh-TW': '做T適配', 'nan-TW': '做T適配', ja: 'T適性', ko: 'T 적합도' },
    change: { en: 'Price change', 'zh-CN': '涨跌幅', 'zh-TW': '漲跌幅', 'nan-TW': '起落幅', ja: '騰落率', ko: '등락률' },
    confidence: { en: 'Confidence', 'zh-CN': '信心', 'zh-TW': '信心', 'nan-TW': '信心', ja: '信頼度', ko: '신뢰도' }
  };
  return labels[option][locale.value] ?? labels[option].en;
}

function sortDirectionLabel() {
  if (resultSortDirection.value === 'desc') {
    if (locale.value === 'en') return 'High first';
    if (locale.value === 'zh-CN') return '高到低';
    if (locale.value === 'ja') return '高い順';
    if (locale.value === 'ko') return '높은 순';
    return '高到低';
  }
  if (locale.value === 'en') return 'Low first';
  if (locale.value === 'zh-CN') return '低到高';
  if (locale.value === 'ja') return '低い順';
  if (locale.value === 'ko') return '낮은 순';
  return '低到高';
}

function sortFieldLabel() {
  if (locale.value === 'en') return 'Sort by';
  if (locale.value === 'zh-CN') return '排序';
  if (locale.value === 'ja') return '並び順';
  if (locale.value === 'ko') return '정렬';
  if (locale.value === 'nan-TW') return '排序';
  return '排序';
}

function pickSortValue(pick: Pick, option: ResultSortKey) {
  if (option === 'recommended') return null;
  if (option === 'decision') return pick.decisionEngine?.rankScore ?? pick.compositeModel?.rankScore;
  if (option === 'overall') return pick.decisionEngine?.rankScore ?? pick.overallAssessment?.totalScore;
  if (option === 'score') return pick.score;
  if (option === 'todayBuy') return pick.overallAssessment?.components.todayBuyScore ?? pick.prediction?.todayBuyScore;
  if (option === 'futureRise') return pick.overallAssessment?.components.futureRiseScore ?? pick.prediction?.futureRiseScore ?? pick.opportunityScore;
  if (option === 'profitableExit') return pick.overallAssessment?.components.profitableExitScore ?? pick.prediction?.profitableExitScore;
  if (option === 'newsHeat') return pick.newsHeatAnalysis?.impactScore ?? pick.prediction?.newsHeatImpactScore;
  if (option === 'continuation') return pick.nextSessionContinuationScore ?? pick.trendAnalysis?.continuationScore;
  if (option === 'riskLow') {
    const risk = pick.downsideRiskScore ?? pick.nextSessionReversalRiskScore ?? pick.trendAnalysis?.reversalRiskScore;
    return risk === undefined ? undefined : 100 - risk;
  }
  if (option === 'tScore') return pick.tScore;
  if (option === 'change') return pick.change;
  if (option === 'confidence') return pick.confidence;
  return null;
}

function compareSortedPicks(left: { pick: Pick; index: number }, right: { pick: Pick; index: number }) {
  if (resultSortKey.value === 'recommended') return left.index - right.index;
  const leftValue = pickSortValue(left.pick, resultSortKey.value);
  const rightValue = pickSortValue(right.pick, resultSortKey.value);
  const leftMissing = !Number.isFinite(leftValue);
  const rightMissing = !Number.isFinite(rightValue);
  if (leftMissing && rightMissing) return left.index - right.index;
  if (leftMissing) return 1;
  if (rightMissing) return -1;
  const direction = resultSortDirection.value === 'asc' ? 1 : -1;
  const delta = (Number(leftValue) - Number(rightValue)) * direction;
  return delta || left.index - right.index;
}

function resultCountLabel() {
  if (locale.value === 'en') return `${filteredPicks.value.length}/${picks.value.length} shown`;
  if (locale.value === 'zh-CN') return `显示 ${filteredPicks.value.length}/${picks.value.length}`;
  if (locale.value === 'ja') return `${filteredPicks.value.length}/${picks.value.length} 件表示`;
  if (locale.value === 'ko') return `${filteredPicks.value.length}/${picks.value.length}개 표시`;
  if (locale.value === 'nan-TW') return `顯示 ${filteredPicks.value.length}/${picks.value.length}`;
  return `顯示 ${filteredPicks.value.length}/${picks.value.length}`;
}

function scanGeneratedAtLabel() {
  return generatedAt.value || new Date().toLocaleString();
}

function scanStrategyLabel() {
  if (useCustom.value) return t.value.customWeights;
  return selectedStrategy.value ? strategyName(selectedStrategy.value) : selectedStrategyId.value;
}

type HoldingFieldKey = 'quantity' | 'cost' | 'pnl' | 'weight';
type PortfolioMarkdownKey = 'importedHoldings' | 'source' | 'currentHoldings' | 'totalMarketValue' | 'unrealizedPnl' | 'portfolioWarnings' | 'holding' | 'shares' | 'cost' | 'action';
type HoldingNoteParams = Record<string, string | number>;
type PortfolioLocaleText = {
  scanLabel: (count: number) => string;
  importTitle: string;
  importHint: string;
  manualTitle: string;
  manualHint: string;
  manualPlaceholder: string;
  manualApply: string;
  manualFailed: string;
  importing: string;
  chooseFile: string;
  clear: string;
  importFailed: string;
  liveBackendRequired: string;
  ready: (count: number, ignoredRows: number) => string;
  actions: Record<HoldingAction, string>;
  fields: Record<HoldingFieldKey, string>;
  markdown: Record<PortfolioMarkdownKey, string>;
  notes: Record<string, (params: HoldingNoteParams) => string>;
};

const portfolioTexts: Record<Locale, PortfolioLocaleText> = {
  en: {
    scanLabel: (count) => `${count} holdings`,
    importTitle: 'Import broker holdings',
    importHint: 'Supports Dongwu Securities A-share .xls text exports; current non-zero holdings are analyzed automatically.',
    manualTitle: 'Paste holdings manually',
    manualHint: 'One row per stock. Use headers or default order: symbol, name, quantity, available, cost, latest price.',
    manualPlaceholder: 'symbol,name,quantity,available,cost,latest\n300750.SZ,CATL,100,80,200\n600519.SS,Kweichow Moutai,50,50,1200,1258',
    manualApply: 'Analyze pasted holdings',
    manualFailed: 'No valid holdings were found. Include at least symbol, quantity, and cost price.',
    importing: 'Importing...',
    chooseFile: 'Choose holdings file',
    clear: 'Clear',
    importFailed: 'Failed to import holdings file.',
    liveBackendRequired: 'Holdings import requires the live Python backend.',
    ready: (count, ignoredRows) => `${count} current holdings recognized${ignoredRows ? ` · ${ignoredRows} ignored` : ''}`,
    actions: { add: 'Add only in batches', hold: 'Hold / wait', reduce: 'Reduce risk', exit: 'Exit risk' },
    fields: { quantity: 'Quantity', cost: 'Cost', pnl: 'P/L', weight: 'Weight' },
    markdown: {
      importedHoldings: 'Imported holdings',
      source: 'Source',
      currentHoldings: 'Current holdings recognized',
      totalMarketValue: 'Total market value',
      unrealizedPnl: 'Unrealized P/L',
      portfolioWarnings: 'Portfolio warnings',
      holding: 'Holding',
      shares: 'shares',
      cost: 'cost',
      action: 'action'
    },
    notes: {
      holdingStrategyExit: (p) => `Strategy marks exit risk: score ${p.score}, downside risk ${p.risk}/100.`,
      holdingReduceRisk: (p) => `Downside risk is ${p.risk}/100; reduce exposure or tighten stops.`,
      holdingAddOnlyInBatches: (p) => `Strategy support is positive at ${p.score}/100; only add in batches.`,
      holdingHoldWait: () => 'No high-conviction add signal yet; hold and wait for confirmation.',
      holdingLargeLoss: (p) => `Position loss is ${p.pnlPct}%; avoid averaging down without signal repair.`,
      holdingNoAverageDown: () => 'Do not average down while risk/news/price signals remain weak.',
      holdingBelowCost: (p) => `Position is below cost by ${p.pnlPct}%; wait for stabilization before adding.`,
      holdingConcentration: (p) => `Position weight is ${p.weight}%; concentration risk needs active control.`,
      holdingProfitProtect: (p) => `Profit is ${p.pnlPct}%, but pullback risk is ${p.risk}/100; protect gains.`,
      holdingCostGap: (p) => `Live price is ${p.gap}% versus cost ${p.cost}.`,
      holdingPriceSourceDrift: (p) => `Broker price ${p.broker} and live price ${p.live} differ by ${p.gap}%; verify the quote source before acting.`,
      holdingSizingPlan: (p) => `Target weight is ${p.target}%; suggested share change ${p.change}.`,
      holdingOrderLotAdjusted: (p) => `Order size adjusted for ${p.market} lot rules: raw ${p.raw}, usable ${p.adjusted}, lot ${p.lot || 'n/a'} (${p.policy}).`,
      holdingStopLossPlan: (p) => `Review exit or reduction if price breaks ${p.price}.`,
      holdingT1Unavailable: (p) => `T+1 lock: ${p.blocked} shares are not sellable today; planned change ${p.planned}.`,
      holdingEtfCore: () => 'ETF holding can stay as a core allocation only while trend and drawdown stay controlled.',
      portfolioTotalDrawdown: (p) => `Portfolio drawdown is ${p.pnlPct}%; prioritize risk review.`,
      portfolioConcentration: (p) => `${p.symbol} is ${p.weight}% of holdings; concentration is high.`,
      portfolioLargeLoss: (p) => `${p.symbol} is down ${p.pnlPct}%; avoid passive averaging down.`,
      portfolioNoCurrentHolding: () => 'No current non-zero holdings were found in the file.'
    }
  },
  'zh-CN': {
    scanLabel: (count) => `持仓 ${count} 只`,
    importTitle: '导入券商持仓',
    importHint: '兼容东吴证券 A 股 .xls 文本导出；只识别当前实际数量大于 0 的持仓，并自动做策略分析。',
    manualTitle: '批量粘贴持仓',
    manualHint: '每行一只股票。可带表头；无表头时默认：代码、名称、实际数量、可用数量、成本价、最新价。',
    manualPlaceholder: '代码,名称,实际数量,可用数量,成本价,最新价\n300750,宁德时代,100,80,200\n600519,贵州茅台,50,50,1200,1258',
    manualApply: '分析粘贴持仓',
    manualFailed: '没有识别到有效持仓。至少需要股票代码、实际数量和成本价。',
    importing: '正在导入...',
    chooseFile: '选择持仓文件',
    clear: '清除',
    importFailed: '持仓文件导入失败。',
    liveBackendRequired: '持仓导入需要连接实时 Python 后端。',
    ready: (count, ignoredRows) => `已识别 ${count} 只当前持仓${ignoredRows ? ` · 忽略 ${ignoredRows} 行` : ''}`,
    actions: { add: '只分批加仓', hold: '持有观察', reduce: '降低风险', exit: '退出风险' },
    fields: { quantity: '持仓数量', cost: '成本价', pnl: '浮动盈亏', weight: '仓位占比' },
    markdown: {
      importedHoldings: '导入持仓',
      source: '来源',
      currentHoldings: '已识别当前持仓',
      totalMarketValue: '总市值',
      unrealizedPnl: '浮动盈亏',
      portfolioWarnings: '组合风险提示',
      holding: '持仓',
      shares: '股',
      cost: '成本',
      action: '操作'
    },
    notes: {
      holdingStrategyExit: (p) => `策略判断有退出风险：评分 ${p.score}，下行风险 ${p.risk}/100。`,
      holdingReduceRisk: (p) => `下行风险 ${p.risk}/100；应降低仓位或收紧止损。`,
      holdingAddOnlyInBatches: (p) => `策略支持度 ${p.score}/100；只适合分批，不适合追高。`,
      holdingHoldWait: () => '暂时没有高信心加仓信号；以持有观察、等待确认为主。',
      holdingLargeLoss: (p) => `持仓亏损 ${p.pnlPct}%；信号未修复前避免摊平。`,
      holdingNoAverageDown: () => '风险、新闻或价格信号仍弱时，不建议摊平。',
      holdingBelowCost: (p) => `持仓低于成本 ${p.pnlPct}%；加仓前先等价格稳定。`,
      holdingConcentration: (p) => `单只仓位占比 ${p.weight}%；集中度风险需要主动控制。`,
      holdingProfitProtect: (p) => `已有 ${p.pnlPct}% 浮盈，但回撤风险 ${p.risk}/100；应保护利润。`,
      holdingCostGap: (p) => `现价相对成本 ${p.cost} 的差距为 ${p.gap}%。`,
      holdingPriceSourceDrift: (p) => `券商价 ${p.broker} 与实时价 ${p.live} 相差 ${p.gap}%；操作前先确认报价来源。`,
      holdingSizingPlan: (p) => `目标仓位 ${p.target}%；建议增减股数 ${p.change}。`,
      holdingOrderLotAdjusted: (p) => `已按 ${p.market} 交易单位修正：原始 ${p.raw}，可用 ${p.adjusted}，每手 ${p.lot || '无'}（${p.policy}）。`,
      holdingStopLossPlan: (p) => `若价格跌破 ${p.price}，应重新评估减仓或退出。`,
      holdingT1Unavailable: (p) => `T+1 限制：${p.blocked} 股今日不可卖；计划调整 ${p.planned}。`,
      holdingEtfCore: () => 'ETF 只有在趋势与回撤受控时，才适合作为核心配置继续持有。',
      portfolioTotalDrawdown: (p) => `持仓整体亏损 ${p.pnlPct}%；优先检查风险。`,
      portfolioConcentration: (p) => `${p.symbol} 占持仓 ${p.weight}%；集中度偏高。`,
      portfolioLargeLoss: (p) => `${p.symbol} 亏损 ${p.pnlPct}%；避免被动摊平。`,
      portfolioNoCurrentHolding: () => '文件中没有识别到实际数量大于 0 的当前持仓。'
    }
  },
  'zh-TW': {
    scanLabel: (count) => `持倉 ${count} 檔`,
    importTitle: '匯入券商持倉',
    importHint: '兼容東吳證券 A 股 .xls 文字匯出；只識別目前實際數量大於 0 的持倉，並自動做策略分析。',
    manualTitle: '批量貼上持倉',
    manualHint: '每列一檔股票。可帶表頭；無表頭時預設：代碼、名稱、實際數量、可用數量、成本價、最新價。',
    manualPlaceholder: '代碼,名稱,實際數量,可用數量,成本價,最新價\n300750,寧德時代,100,80,200\n600519,貴州茅台,50,50,1200,1258',
    manualApply: '分析貼上持倉',
    manualFailed: '沒有識別到有效持倉。至少需要股票代碼、實際數量和成本價。',
    importing: '正在匯入...',
    chooseFile: '選擇持倉檔',
    clear: '清除',
    importFailed: '持倉檔匯入失敗。',
    liveBackendRequired: '持倉匯入需要連線即時 Python 後端。',
    ready: (count, ignoredRows) => `已識別 ${count} 檔目前持倉${ignoredRows ? ` · 忽略 ${ignoredRows} 行` : ''}`,
    actions: { add: '只分批加倉', hold: '持有觀察', reduce: '降低風險', exit: '退出風險' },
    fields: { quantity: '持倉數量', cost: '成本價', pnl: '浮動盈虧', weight: '倉位占比' },
    markdown: {
      importedHoldings: '匯入持倉',
      source: '來源',
      currentHoldings: '已識別目前持倉',
      totalMarketValue: '總市值',
      unrealizedPnl: '浮動盈虧',
      portfolioWarnings: '組合風險提示',
      holding: '持倉',
      shares: '股',
      cost: '成本',
      action: '操作'
    },
    notes: {
      holdingStrategyExit: (p) => `策略判斷有退出風險：評分 ${p.score}，下行風險 ${p.risk}/100。`,
      holdingReduceRisk: (p) => `下行風險 ${p.risk}/100；應降低倉位或收緊停損。`,
      holdingAddOnlyInBatches: (p) => `策略支持度 ${p.score}/100；只適合分批，不適合追高。`,
      holdingHoldWait: () => '暫無高信心加倉訊號；以持有觀察、等待確認為主。',
      holdingLargeLoss: (p) => `持倉虧損 ${p.pnlPct}%；訊號未修復前避免攤平。`,
      holdingNoAverageDown: () => '風險、新聞或價格訊號仍弱時，不建議攤平。',
      holdingBelowCost: (p) => `持倉低於成本 ${p.pnlPct}%；加倉前先等價格穩定。`,
      holdingConcentration: (p) => `單檔倉位占比 ${p.weight}%；集中度風險需要主動控制。`,
      holdingProfitProtect: (p) => `已有 ${p.pnlPct}% 浮盈，但回撤風險 ${p.risk}/100；應保護利潤。`,
      holdingCostGap: (p) => `現價相對成本 ${p.cost} 的差距為 ${p.gap}%。`,
      holdingPriceSourceDrift: (p) => `券商價 ${p.broker} 與即時價 ${p.live} 相差 ${p.gap}%；操作前先確認報價來源。`,
      holdingSizingPlan: (p) => `目標倉位 ${p.target}%；建議增減股數 ${p.change}。`,
      holdingOrderLotAdjusted: (p) => `已按 ${p.market} 交易單位修正：原始 ${p.raw}，可用 ${p.adjusted}，每手 ${p.lot || '無'}（${p.policy}）。`,
      holdingStopLossPlan: (p) => `若價格跌破 ${p.price}，應重新評估減倉或退出。`,
      holdingT1Unavailable: (p) => `T+1 限制：${p.blocked} 股今日不可賣；計畫調整 ${p.planned}。`,
      holdingEtfCore: () => 'ETF 只有在趨勢與回撤受控時，才適合作為核心配置繼續持有。',
      portfolioTotalDrawdown: (p) => `持倉整體虧損 ${p.pnlPct}%；優先檢查風險。`,
      portfolioConcentration: (p) => `${p.symbol} 占持倉 ${p.weight}%；集中度偏高。`,
      portfolioLargeLoss: (p) => `${p.symbol} 虧損 ${p.pnlPct}%；避免被動攤平。`,
      portfolioNoCurrentHolding: () => '檔案中沒有識別到實際數量大於 0 的目前持倉。'
    }
  },
  'nan-TW': {
    scanLabel: (count) => `持倉 ${count} 檔`,
    importTitle: '匯入券商持倉',
    importHint: '支援東吳證券 A 股 .xls 匯出；只分析實際數量大過 0 的持倉。',
    manualTitle: '批量貼持倉',
    manualHint: '一列一檔。會使有表頭；無表頭照：代碼、名稱、實際數量、可用數量、成本價、最新價。',
    manualPlaceholder: '代碼,名稱,實際數量,可用數量,成本價,最新價\n300750,寧德時代,100,80,200\n600519,貴州茅台,50,50,1200,1258',
    manualApply: '分析貼上的持倉',
    manualFailed: '無認出有效持倉。至少愛有股票代碼、實際數量佮成本價。',
    importing: '咧匯入...',
    chooseFile: '選持倉檔',
    clear: '清掉',
    importFailed: '持倉檔匯入無成功。',
    liveBackendRequired: '持倉匯入愛連線即時 Python 後端。',
    ready: (count, ignoredRows) => `已認出 ${count} 檔目前持倉${ignoredRows ? ` · 忽略 ${ignoredRows} 行` : ''}`,
    actions: { add: '分批閣加', hold: '持有觀察', reduce: '降低風險', exit: '退出風險' },
    fields: { quantity: '持倉數量', cost: '成本價', pnl: '浮動盈虧', weight: '倉位占比' },
    markdown: {
      importedHoldings: '匯入持倉',
      source: '來源',
      currentHoldings: '已認出目前持倉',
      totalMarketValue: '總市值',
      unrealizedPnl: '浮動盈虧',
      portfolioWarnings: '組合風險提示',
      holding: '持倉',
      shares: '股',
      cost: '成本',
      action: '操作'
    },
    notes: {
      holdingStrategyExit: (p) => `策略看著退出風險：分數 ${p.score}，下行風險 ${p.risk}/100。`,
      holdingReduceRisk: (p) => `下行風險 ${p.risk}/100；著降低倉位抑是收緊停損。`,
      holdingAddOnlyInBatches: (p) => `策略支持度 ${p.score}/100；只適合分批，毋通追高。`,
      holdingHoldWait: () => '猶未有高信心加倉訊號；先持有觀察、等確認。',
      holdingLargeLoss: (p) => `持倉虧損 ${p.pnlPct}%；訊號未修復前毋通攤平。`,
      holdingNoAverageDown: () => '風險、新聞抑是價格訊號猶弱，毋建議攤平。',
      holdingBelowCost: (p) => `持倉低過成本 ${p.pnlPct}%；加倉前先等價格穩定。`,
      holdingConcentration: (p) => `單檔倉位占比 ${p.weight}%；集中度風險愛控制。`,
      holdingProfitProtect: (p) => `已有 ${p.pnlPct}% 浮盈，毋過回撤風險 ${p.risk}/100；愛保護利潤。`,
      holdingCostGap: (p) => `現價比成本 ${p.cost} 差 ${p.gap}%。`,
      holdingPriceSourceDrift: (p) => `券商價 ${p.broker} 佮即時價 ${p.live} 差 ${p.gap}%；操作前先確認報價來源。`,
      holdingSizingPlan: (p) => `目標倉位 ${p.target}%；建議增減股數 ${p.change}。`,
      holdingOrderLotAdjusted: (p) => `已照 ${p.market} 交易單位修正：原始 ${p.raw}，會使 ${p.adjusted}，每手 ${p.lot || '無'}（${p.policy}）。`,
      holdingStopLossPlan: (p) => `若價格跌破 ${p.price}，愛重新評估減倉抑是退出。`,
      holdingT1Unavailable: (p) => `T+1 限制：${p.blocked} 股今仔日袂當賣；計畫調整 ${p.planned}。`,
      holdingEtfCore: () => 'ETF 只有趨勢佮回撤受控，才適合繼續做核心配置。',
      portfolioTotalDrawdown: (p) => `持倉整體虧損 ${p.pnlPct}%；先檢查風險。`,
      portfolioConcentration: (p) => `${p.symbol} 占持倉 ${p.weight}%；集中度偏懸。`,
      portfolioLargeLoss: (p) => `${p.symbol} 虧損 ${p.pnlPct}%；避免被動攤平。`,
      portfolioNoCurrentHolding: () => '檔案內底無認出實際數量大過 0 的目前持倉。'
    }
  },
  ja: {
    scanLabel: (count) => `保有 ${count} 件`,
    importTitle: '証券会社の保有を取り込む',
    importHint: '東呉証券の A 株 .xls テキスト出力に対応し、現在数量がある保有だけを自動分析します。',
    manualTitle: '保有を一括貼り付け',
    manualHint: '1 行 1 銘柄。ヘッダー付き可。ヘッダーなしは: symbol, name, quantity, available, cost, latest.',
    manualPlaceholder: 'symbol,name,quantity,available,cost,latest\n300750.SZ,CATL,100,80,200\n600519.SS,Kweichow Moutai,50,50,1200,1258',
    manualApply: '貼り付け保有を分析',
    manualFailed: '有効な保有が見つかりません。少なくともコード、数量、取得単価を入力してください。',
    importing: '取り込み中...',
    chooseFile: '保有ファイルを選択',
    clear: '解除',
    importFailed: '保有ファイルの取り込みに失敗しました。',
    liveBackendRequired: '保有ファイルの取り込みにはライブ Python バックエンドが必要です。',
    ready: (count, ignoredRows) => `${count} 件の現在保有を認識${ignoredRows ? ` · ${ignoredRows} 行除外` : ''}`,
    actions: { add: '分割で追加', hold: '保有して待つ', reduce: 'リスク縮小', exit: '撤退リスク' },
    fields: { quantity: '保有数量', cost: '取得単価', pnl: '評価損益', weight: '保有比率' },
    markdown: {
      importedHoldings: '取り込み保有',
      source: 'ソース',
      currentHoldings: '認識した現在保有',
      totalMarketValue: '評価額合計',
      unrealizedPnl: '評価損益',
      portfolioWarnings: 'ポートフォリオ警告',
      holding: '保有',
      shares: '株',
      cost: '取得単価',
      action: 'アクション'
    },
    notes: {
      holdingStrategyExit: (p) => `戦略上は撤退リスクです: スコア ${p.score}、下落リスク ${p.risk}/100。`,
      holdingReduceRisk: (p) => `下落リスクは ${p.risk}/100 です。保有を減らすか、損切り基準を厳しくしてください。`,
      holdingAddOnlyInBatches: (p) => `戦略支持度は ${p.score}/100。追加する場合も分割のみです。`,
      holdingHoldWait: () => 'まだ高確度の追加シグナルはありません。保有しながら確認を待ちます。',
      holdingLargeLoss: (p) => `評価損は ${p.pnlPct}% です。シグナル改善前のナンピンは避けてください。`,
      holdingNoAverageDown: () => 'リスク、ニュース、価格シグナルが弱い間はナンピンしないでください。',
      holdingBelowCost: (p) => `取得価格を ${p.pnlPct}% 下回っています。追加前に価格安定を待ってください。`,
      holdingConcentration: (p) => `保有比率は ${p.weight}% です。集中リスクを管理してください。`,
      holdingProfitProtect: (p) => `${p.pnlPct}% の含み益がありますが、押し戻しリスクは ${p.risk}/100 です。利益保護を優先してください。`,
      holdingCostGap: (p) => `現在値は取得単価 ${p.cost} に対して ${p.gap}% です。`,
      holdingPriceSourceDrift: (p) => `証券会社価格 ${p.broker} とライブ価格 ${p.live} が ${p.gap}% ずれています。売買前に価格ソースを確認してください。`,
      holdingSizingPlan: (p) => `目標比率は ${p.target}%、提案株数変更は ${p.change} です。`,
      holdingOrderLotAdjusted: (p) => `${p.market} の売買単位に合わせて調整しました: 元 ${p.raw}、使用可 ${p.adjusted}、単位 ${p.lot || 'なし'} (${p.policy})。`,
      holdingStopLossPlan: (p) => `${p.price} を割り込む場合は、縮小または撤退を再評価してください。`,
      holdingT1Unavailable: (p) => `T+1 制限: ${p.blocked} 株は本日売却不可、計画変更は ${p.planned} です。`,
      holdingEtfCore: () => 'ETF はトレンドとドローダウンが管理されている間だけ、コア配分として保有できます。',
      portfolioTotalDrawdown: (p) => `ポートフォリオの評価損は ${p.pnlPct}% です。リスク点検を優先してください。`,
      portfolioConcentration: (p) => `${p.symbol} は保有全体の ${p.weight}% です。集中度が高いです。`,
      portfolioLargeLoss: (p) => `${p.symbol} は ${p.pnlPct}% 下落しています。受け身のナンピンは避けてください。`,
      portfolioNoCurrentHolding: () => '現在数量が 0 を超える保有はファイル内に見つかりませんでした。'
    }
  },
  ko: {
    scanLabel: (count) => `보유 ${count}개`,
    importTitle: '증권사 보유 종목 가져오기',
    importHint: '동오증권 A주 .xls 텍스트 내보내기를 지원하며 현재 수량이 있는 보유 종목만 자동 분석합니다.',
    manualTitle: '보유 종목 일괄 붙여넣기',
    manualHint: '한 줄에 한 종목. 헤더 사용 가능. 헤더가 없으면 symbol, name, quantity, available, cost, latest 순서입니다.',
    manualPlaceholder: 'symbol,name,quantity,available,cost,latest\n300750.SZ,CATL,100,80,200\n600519.SS,Kweichow Moutai,50,50,1200,1258',
    manualApply: '붙여넣은 보유 분석',
    manualFailed: '유효한 보유 종목을 찾지 못했습니다. 최소 코드, 수량, 평균 단가를 입력하세요.',
    importing: '가져오는 중...',
    chooseFile: '보유 파일 선택',
    clear: '지우기',
    importFailed: '보유 파일을 가져오지 못했습니다.',
    liveBackendRequired: '보유 파일 가져오기는 실시간 Python 백엔드가 필요합니다.',
    ready: (count, ignoredRows) => `현재 보유 ${count}개 인식${ignoredRows ? ` · ${ignoredRows}행 제외` : ''}`,
    actions: { add: '분할 추가만', hold: '보유 / 대기', reduce: '리스크 축소', exit: '이탈 리스크' },
    fields: { quantity: '보유 수량', cost: '평균 단가', pnl: '평가 손익', weight: '비중' },
    markdown: {
      importedHoldings: '가져온 보유 종목',
      source: '출처',
      currentHoldings: '인식한 현재 보유',
      totalMarketValue: '총 평가금액',
      unrealizedPnl: '평가 손익',
      portfolioWarnings: '포트폴리오 경고',
      holding: '보유',
      shares: '주',
      cost: '단가',
      action: '조치'
    },
    notes: {
      holdingStrategyExit: (p) => `전략상 이탈 리스크입니다: 점수 ${p.score}, 하방 리스크 ${p.risk}/100.`,
      holdingReduceRisk: (p) => `하방 리스크가 ${p.risk}/100입니다. 노출을 줄이거나 손절 기준을 조정하세요.`,
      holdingAddOnlyInBatches: (p) => `전략 지지도가 ${p.score}/100입니다. 추가 매수는 분할로만 접근하세요.`,
      holdingHoldWait: () => '아직 확신 높은 추가 매수 신호가 없습니다. 보유하며 확인을 기다립니다.',
      holdingLargeLoss: (p) => `평가 손실이 ${p.pnlPct}%입니다. 신호가 회복되기 전 물타기는 피하세요.`,
      holdingNoAverageDown: () => '리스크, 뉴스, 가격 신호가 약한 동안에는 물타기를 하지 마세요.',
      holdingBelowCost: (p) => `평균 단가 대비 ${p.pnlPct}% 낮습니다. 추가 전 가격 안정화를 기다리세요.`,
      holdingConcentration: (p) => `보유 비중이 ${p.weight}%입니다. 집중 리스크 관리가 필요합니다.`,
      holdingProfitProtect: (p) => `${p.pnlPct}% 수익 상태지만 되돌림 리스크가 ${p.risk}/100입니다. 수익 보호를 우선하세요.`,
      holdingCostGap: (p) => `현재가는 평균 단가 ${p.cost} 대비 ${p.gap}%입니다.`,
      holdingPriceSourceDrift: (p) => `증권사 가격 ${p.broker}과 실시간 가격 ${p.live} 차이가 ${p.gap}%입니다. 실행 전 가격 출처를 확인하세요.`,
      holdingSizingPlan: (p) => `목표 비중은 ${p.target}%이며, 제안 수량 변화는 ${p.change}주입니다.`,
      holdingOrderLotAdjusted: (p) => `${p.market} 거래 단위에 맞춰 조정했습니다: 원시 ${p.raw}, 사용 ${p.adjusted}, 단위 ${p.lot || '없음'} (${p.policy}).`,
      holdingStopLossPlan: (p) => `${p.price} 이탈 시 축소 또는 이탈을 재평가하세요.`,
      holdingT1Unavailable: (p) => `T+1 제한: ${p.blocked}주는 오늘 매도할 수 없으며 계획 변화는 ${p.planned}입니다.`,
      holdingEtfCore: () => 'ETF는 추세와 낙폭이 통제될 때만 핵심 배분으로 계속 보유할 수 있습니다.',
      portfolioTotalDrawdown: (p) => `포트폴리오 손실이 ${p.pnlPct}%입니다. 리스크 점검을 우선하세요.`,
      portfolioConcentration: (p) => `${p.symbol}이 보유 비중의 ${p.weight}%입니다. 집중도가 높습니다.`,
      portfolioLargeLoss: (p) => `${p.symbol}이 ${p.pnlPct}% 하락했습니다. 수동적인 물타기는 피하세요.`,
      portfolioNoCurrentHolding: () => '현재 수량이 0보다 큰 보유 종목을 파일에서 찾지 못했습니다.'
    }
  }
};

function portfolioText() {
  return portfolioTexts[locale.value] ?? portfolioTexts.en;
}

function portfolioScanLabel(count: number) {
  return portfolioText().scanLabel(count);
}

function portfolioImportTitle() {
  return portfolioText().importTitle;
}

function portfolioImportHint() {
  return portfolioText().importHint;
}

function portfolioManualTitle() {
  return portfolioText().manualTitle;
}

function portfolioManualHint() {
  return portfolioText().manualHint;
}

function portfolioManualPlaceholder() {
  return portfolioText().manualPlaceholder;
}

function portfolioManualApplyLabel() {
  return portfolioText().manualApply;
}

function portfolioImportButtonLabel() {
  return importingPortfolio.value ? portfolioText().importing : portfolioText().chooseFile;
}

function clearPortfolioLabel() {
  return portfolioText().clear;
}

function portfolioMemoryTitleLabel() {
  return localeText({
    en: 'Holdings memory',
    'zh-CN': '持仓记忆',
    'zh-TW': '持倉記憶',
    ja: '保有履歴',
    ko: '보유 기억'
  });
}

function portfolioMemoryHintLabel() {
  return localeText({
    en: 'Recent versions saved under this login key.',
    'zh-CN': '最近版本会跟随当前登录 key 保存。',
    'zh-TW': '最近版本會跟隨目前登入 key 保存。',
    ja: '最近の版はこのログインキーに保存されます。',
    ko: '최근 버전은 현재 로그인 key에 저장됩니다.'
  });
}

function restorePortfolioLabel() {
  return localeText({ en: 'Restore', 'zh-CN': '恢复', 'zh-TW': '恢復', ja: '復元', ko: '복원' });
}

function deletePortfolioMemoryLabel() {
  return localeText({ en: 'Delete', 'zh-CN': '删除', 'zh-TW': '刪除', ja: '削除', ko: '삭제' });
}

function portfolioMemoryMeta(item: PortfolioMemoryItem) {
  const savedAt = new Date(item.savedAt);
  const savedLabel = Number.isNaN(savedAt.getTime()) ? item.savedAt : savedAt.toLocaleString();
  return `${savedLabel} · ${item.recognizedCount} · ${moneyLabel(item.totalMarketValue)} · ${percentLabel(item.totalUnrealizedPnlPct)}`;
}

function portfolioMemoryDiffLabel(item: PortfolioMemoryItem) {
  const diff = item.diff;
  if (!diff) {
    return localeText({ en: 'Baseline snapshot', 'zh-CN': '基准快照', 'zh-TW': '基準快照', ja: '基準スナップショット', ko: '기준 스냅샷' });
  }
  const pnl = signedMoneyLabel(diff.pnlChange);
  if (locale.value === 'en') return `+${diff.added} / -${diff.removed} · qty ${diff.quantityChanged} · cost ${diff.costChanged} · P/L ${pnl}`;
  if (locale.value === 'zh-CN') return `新增 ${diff.added} / 移除 ${diff.removed} · 数量变 ${diff.quantityChanged} · 成本变 ${diff.costChanged} · 盈亏 ${pnl}`;
  if (locale.value === 'ja') return `追加 ${diff.added} / 削除 ${diff.removed} · 数量 ${diff.quantityChanged} · 原価 ${diff.costChanged} · 損益 ${pnl}`;
  if (locale.value === 'ko') return `추가 ${diff.added} / 제거 ${diff.removed} · 수량 ${diff.quantityChanged} · 원가 ${diff.costChanged} · 손익 ${pnl}`;
  return `新增 ${diff.added} / 移除 ${diff.removed} · 數量變 ${diff.quantityChanged} · 成本變 ${diff.costChanged} · 盈虧 ${pnl}`;
}

function portfolioMemoryDiffTitle() {
  return localeText({ en: 'Version diff', 'zh-CN': '版本差异', 'zh-TW': '版本差異', ja: '版の差分', ko: '버전 차이' });
}

function portfolioReadyLabel(portfolio: PortfolioImportResponse | PortfolioAnalysis) {
  return portfolioText().ready(portfolio.recognizedCount, portfolio.ignoredRows || 0);
}

function portfolioCurrency() {
  return 'CNY';
}

function marketCurrency(market: Market | string | undefined) {
  const currencies: Record<string, string> = {
    CN: 'CNY',
    TW: 'TWD',
    HK: 'HKD',
    US: 'USD',
    JP: 'JPY',
    KR: 'KRW',
    SG: 'SGD'
  };
  return currencies[String(market || '')] ?? portfolioCurrency();
}

function currentPriceLabel() {
  return localeText({ en: 'Current price', 'zh-CN': '当前价格', 'zh-TW': '目前價格', ja: '現在値', ko: '현재가' });
}

function moneyLabel(value: number | null | undefined, currency = portfolioCurrency()) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${currency} ${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function percentLabel(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(1)}%`;
}

function nonNegativeQuantity(value: number | null | undefined) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, number);
}

function quantityMagnitude(value: number | null | undefined) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return 0;
  return Math.abs(number);
}

function quantityAbsLabel(value: number | null | undefined) {
  return quantityMagnitude(value).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function signedMoneyLabel(value: number | null | undefined, currency = portfolioCurrency()) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${Number(value) > 0 ? '+' : ''}${moneyLabel(value, currency)}`;
}

function holdingActionLabel(action: HoldingAction) {
  return portfolioText().actions[action];
}

function holdingActionDisplayLabel(action: HoldingAction | string) {
  return holdingActionLabel(action as HoldingAction) || String(action || '-');
}

function holdingActionTone(action: HoldingAction | string | undefined) {
  if (action === 'exit') return 'exit';
  if (action === 'reduce') return 'reduce';
  if (action === 'add') return 'add';
  return 'hold';
}

function holdingPlannedQuantityDisplay(value: number | null | undefined) {
  return quantityAbsLabel(value);
}

function holdingExecutableQuantityDisplay(value: number | null | undefined, status?: string) {
  if (status === 'blocked_today') return '0';
  return quantityAbsLabel(value);
}

function holdingRuleLabel(orderSizing: HoldingActionItem['orderSizing'] | undefined, market?: Market | string) {
  const lot = orderSizing?.sellLotSize ?? orderSizing?.boardLotSize ?? orderSizing?.buyLotSize;
  if (lot && lot > 1) {
    if (locale.value === 'en') return `${lot} shares / lot`;
    if (locale.value === 'zh-CN') return `${lot} 股一手`;
    if (locale.value === 'ja') return `${lot}株単位`;
    if (locale.value === 'ko') return `${lot}주 단위`;
    return `${lot} 股一手`;
  }
  if (orderSizing?.allowsOddLotSell || orderSizing?.allowsOddLotBuy) {
    return localeText({ en: 'Odd lots allowed', 'zh-CN': '支持零股', 'zh-TW': '支援零股', ja: '単元未満可', ko: '단주 가능' });
  }
  if (market === 'CN') return localeText({ en: 'A-share lot rules', 'zh-CN': 'A 股手数规则', 'zh-TW': 'A 股手數規則', ja: 'A株単位規則', ko: 'A주 단위 규칙' });
  return localeText({ en: 'Market lot rules', 'zh-CN': '市场手数规则', 'zh-TW': '市場手數規則', ja: '市場単位規則', ko: '시장 단위 규칙' });
}

function holdingActionRuleLabel(item: HoldingActionItem) {
  return holdingRuleLabel(item.orderSizing, item.market);
}

function holdingActionItemReasonLabel(item: HoldingActionItem) {
  if (item.executionStatus === 'blocked_today') return holdingExecutionStatusLabel(item.executionStatus);
  if (item.executionStatus === 'partial_t1_locked') return holdingExecutionStatusLabel(item.executionStatus);
  if (item.tradableNow === false) return localeText({ en: 'Market not tradable now', 'zh-CN': '当前市场不可交易', 'zh-TW': '目前市場不可交易', ja: '現在は取引不可', ko: '현재 거래 불가' });
  if (item.primaryNoteKeys?.length) return item.primaryNoteKeys.slice(0, 2).join(' · ');
  return holdingExecutionStatusLabel(item.executionStatus);
}

function holdingFieldLabel(field: HoldingFieldKey) {
  return portfolioText().fields[field];
}

function holdingNoteLabel(note: HoldingNote) {
  const formatter = portfolioText().notes[note.key];
  return formatter ? formatter(note.params ?? {}) : note.key;
}

function portfolioImportErrorLabel(cause: unknown) {
  const copy = portfolioText();
  const message = cause instanceof Error ? cause.message : '';
  if (!message || message === 'Failed to import holdings file') return copy.importFailed;
  if (message.includes('live Python backend') || message.includes('Static preview')) return copy.liveBackendRequired;
  return locale.value === 'en' ? message : copy.importFailed;
}

type ManualHoldingField = 'symbol' | 'name' | 'quantity' | 'availableQuantity' | 'costPrice' | 'lastPrice' | 'marketValue';
const manualHoldingHeaderAliases: Record<ManualHoldingField, string[]> = {
  symbol: ['symbol', 'ticker', 'code', 'stockcode', 'securitycode', '代码', '代碼', '股票代码', '股票代碼', '证券代码', '證券代碼', '종목코드', '銘柄コード'],
  name: ['name', 'stockname', 'securityname', '名称', '名稱', '股票名称', '股票名稱', '证券名称', '證券名稱', '종목명', '銘柄名'],
  quantity: ['quantity', 'qty', 'actualquantity', 'shares', '持仓数量', '持倉數量', '实际数量', '實際數量', '股票余额', '股票餘額', '保有数量', '보유수량'],
  availableQuantity: ['available', 'availablequantity', '可用数量', '可用數量', '可用余额', '可用餘額', '可卖数量', '可賣數量', '매도가능수량'],
  costPrice: ['cost', 'costprice', 'avgcost', 'averagecost', '成本价', '成本價', '持仓成本', '持倉成本', '平均单价', '平均單價', '取得単価', '평균단가'],
  lastPrice: ['last', 'lastprice', 'latest', 'latestprice', 'price', 'marketprice', '最新价', '最新價', '现价', '現價', '市价', '市價', '現在値', '현재가'],
  marketValue: ['marketvalue', 'value', '市值', '持仓市值', '持倉市值', '评价金额', '評価額', '평가금액'],
};

function normalizeManualHeader(value: string) {
  return value.toLowerCase().replace(/[\s:_\-./()（）\[\]【】]+/g, '');
}

function fieldFromManualHeader(value: string): ManualHoldingField | null {
  const normalized = normalizeManualHeader(value);
  for (const [field, aliases] of Object.entries(manualHoldingHeaderAliases) as Array<[ManualHoldingField, string[]]>) {
    if (aliases.some((alias) => normalizeManualHeader(alias) === normalized)) return field;
  }
  return null;
}

function splitManualHoldingLine(line: string) {
  const trimmed = line.trim();
  if (!trimmed) return [];
  const delimiter = /[\t,，]/.test(trimmed) ? /[\t,，]+/ : /\s+/;
  return trimmed.split(delimiter).map((cell) => cell.trim()).filter(Boolean);
}

function manualHoldingNumber(value: string | undefined): number | null {
  if (value === undefined) return null;
  const normalized = value.replace(/[,%￥¥$]/g, '').trim();
  if (!normalized || normalized === '-' || normalized === '--') return null;
  const number = Number(normalized);
  return Number.isFinite(number) ? number : null;
}

function normalizeManualHoldingSymbol(value: string) {
  const raw = value.trim().toUpperCase().replace(/^[("'`]+|[)"'`]+$/g, '');
  if (/^SH\d{6}$/.test(raw)) return `${raw.slice(2)}.SS`;
  if (/^SZ\d{6}$/.test(raw)) return `${raw.slice(2)}.SZ`;
  if (/^\d{6}$/.test(raw)) return `${raw}.${raw.startsWith('6') || raw.startsWith('9') ? 'SS' : 'SZ'}`;
  if (/^\d{4,5}$/.test(raw)) return `${raw.padStart(5, '0')}.HK`;
  return raw;
}

function marketFromManualSymbol(symbol: string): Market {
  const upper = symbol.toUpperCase();
  if (upper.endsWith('.SS') || upper.endsWith('.SZ')) return 'CN';
  if (upper.endsWith('.HK')) return 'HK';
  if (upper.endsWith('.T')) return 'JP';
  if (upper.endsWith('.KS') || upper.endsWith('.KQ')) return 'KR';
  if (upper.endsWith('.SI')) return 'SG';
  if (upper.endsWith('.TW')) return 'TW';
  return 'US';
}

function manualPositionFromCells(cells: string[], headerMap: Partial<Record<ManualHoldingField, number>> | null): HoldingPosition | null {
  const get = (field: ManualHoldingField) => {
    const index = headerMap?.[field];
    return index === undefined ? undefined : cells[index];
  };
  const hasExplicitHeader = Boolean(headerMap);
  const secondIsNumber = manualHoldingNumber(cells[1]) !== null;
  const symbolTextValue = hasExplicitHeader ? get('symbol') : cells[0];
  if (!symbolTextValue) return null;

  const symbol = normalizeManualHoldingSymbol(symbolTextValue);
  const name = (hasExplicitHeader ? get('name') : (secondIsNumber ? '' : cells[1])) || symbol;
  const quantity = manualHoldingNumber(hasExplicitHeader ? get('quantity') : cells[secondIsNumber ? 1 : 2]);
  const availableQuantity = manualHoldingNumber(hasExplicitHeader ? get('availableQuantity') : cells[secondIsNumber ? 2 : 3]);
  const costPrice = manualHoldingNumber(hasExplicitHeader ? get('costPrice') : cells[secondIsNumber ? 3 : 4]);
  const lastPrice = manualHoldingNumber(hasExplicitHeader ? get('lastPrice') : cells[secondIsNumber ? 4 : 5]);
  const explicitMarketValue = manualHoldingNumber(hasExplicitHeader ? get('marketValue') : cells[secondIsNumber ? 5 : 6]);
  if (!symbol || quantity === null || quantity <= 0 || costPrice === null) return null;

  const costAmount = quantity * costPrice;
  const marketValue = explicitMarketValue ?? (lastPrice !== null ? quantity * lastPrice : null);
  const unrealizedPnl = marketValue !== null ? marketValue - costAmount : null;
  return {
    symbol,
    code: symbol.split('.')[0],
    name,
    market: marketFromManualSymbol(symbol),
    quantity,
    availableQuantity: availableQuantity ?? quantity,
    frozenQuantity: Math.max(0, quantity - (availableQuantity ?? quantity)),
    costPrice,
    lastPrice,
    marketValue,
    costAmount,
    unrealizedPnl,
    unrealizedPnlPct: unrealizedPnl !== null && costAmount ? unrealizedPnl / costAmount * 100 : null,
  };
}

function manualPortfolioFromText(text: string): PortfolioImportResponse {
  const rawLines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  let headerMap: Partial<Record<ManualHoldingField, number>> | null = null;
  const positions: HoldingPosition[] = [];
  let ignoredRows = 0;

  rawLines.forEach((line, lineIndex) => {
    const cells = splitManualHoldingLine(line);
    if (!cells.length) return;
    const candidateHeaderMap: Partial<Record<ManualHoldingField, number>> = {};
    cells.forEach((cell, index) => {
      const field = fieldFromManualHeader(cell);
      if (field && candidateHeaderMap[field] === undefined) candidateHeaderMap[field] = index;
    });
    if (lineIndex === 0 && candidateHeaderMap.symbol !== undefined && candidateHeaderMap.quantity !== undefined) {
      headerMap = candidateHeaderMap;
      return;
    }
    const position = manualPositionFromCells(cells, headerMap);
    if (position) {
      positions.push(position);
    } else {
      ignoredRows += 1;
    }
  });

  const uniquePositions = Array.from(new Map(positions.map((position) => [position.symbol, position])).values());
  if (!uniquePositions.length) {
    throw new Error(portfolioText().manualFailed);
  }
  const symbols = uniquePositions.map((position) => position.symbol);
  const totalMarketValue = uniquePositions.reduce((sum, position) => sum + (Number(position.marketValue) || 0), 0);
  const totalCostAmount = uniquePositions.reduce((sum, position) => sum + (Number(position.costAmount) || 0), 0);
  const totalUnrealizedPnl = uniquePositions.reduce((sum, position) => sum + (Number(position.unrealizedPnl) || 0), 0);
  return {
    sourceName: portfolioText().manualTitle,
    sourceType: 'manual-holdings',
    importedAt: new Date().toISOString(),
    positions: uniquePositions,
    symbols,
    recognizedCount: uniquePositions.length,
    ignoredRows,
    totalMarketValue: Number(totalMarketValue.toFixed(4)),
    totalCostAmount: Number(totalCostAmount.toFixed(4)),
    totalUnrealizedPnl: Number(totalUnrealizedPnl.toFixed(4)),
    totalUnrealizedPnlPct: totalCostAmount ? Number((totalUnrealizedPnl / totalCostAmount * 100).toFixed(4)) : null,
    warnings: [],
  };
}

async function applyManualHoldings() {
  if (loading.value || importingPortfolio.value) return;
  portfolioImportError.value = '';
  analysisPortfolio.value = null;
  try {
    const imported = manualPortfolioFromText(manualHoldingText.value);
    importedPortfolio.value = imported;
    rememberPortfolio(imported);
    symbolText.value = imported.symbols.join(', ');
    const importedMarkets = [...new Set(imported.positions.map((position) => position.market).filter(isMarket))];
    if (importedMarkets.length) selectedMarkets.value = importedMarkets;
    resultMarketFilter.value = 'all';
    resultVerdictFilter.value = 'all';
    activeView.value = 'stocks';
    scheduleUserStateSync();
    await nextTick();
    await runAnalysis();
  } catch (cause) {
    portfolioImportError.value = cause instanceof Error ? cause.message : portfolioText().manualFailed;
  }
}

function triggerPortfolioImport() {
  if (loading.value || importingPortfolio.value) return;
  portfolioFileInput.value?.click();
}

async function onPortfolioFileSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  importingPortfolio.value = true;
  portfolioImportError.value = '';
  analysisPortfolio.value = null;
  try {
    const imported = await importPortfolioFile(file);
    importedPortfolio.value = imported;
    if (!imported.positions.length) {
      portfolioImportError.value = holdingNoteLabel({ key: 'portfolioNoCurrentHolding', severity: 'warning', params: {} });
      return;
    }
    rememberPortfolio(imported);
    symbolText.value = imported.symbols.join(', ');
    const importedMarkets = [...new Set(imported.positions.map((position) => position.market).filter(isMarket))];
    if (importedMarkets.length) selectedMarkets.value = importedMarkets;
    resultMarketFilter.value = 'all';
    resultVerdictFilter.value = 'all';
    activeView.value = 'stocks';
    scheduleUserStateSync();
    await nextTick();
    await runAnalysis();
  } catch (cause) {
    portfolioImportError.value = portfolioImportErrorLabel(cause);
  } finally {
    importingPortfolio.value = false;
    input.value = '';
    refreshDataMode();
  }
}

function clearImportedPortfolio() {
  const importedSymbols = portfolioSymbols.value.join(', ');
  importedPortfolio.value = null;
  analysisPortfolio.value = null;
  portfolioImportError.value = '';
  if (symbolText.value === importedSymbols) {
    symbolText.value = '';
  }
  scheduleUserStateSync();
}

async function restorePortfolioMemory(item: PortfolioMemoryItem) {
  if (loading.value || importingPortfolio.value) return;
  const portfolio = cloneJson(item.portfolio);
  importedPortfolio.value = portfolio;
  analysisPortfolio.value = null;
  portfolioImportError.value = '';
  symbolText.value = portfolio.symbols.join(', ');
  const importedMarkets = [...new Set(portfolio.positions.map((position) => position.market).filter(isMarket))];
  if (importedMarkets.length) selectedMarkets.value = importedMarkets;
  resultMarketFilter.value = 'all';
  resultVerdictFilter.value = 'all';
  activeInvestmentTask.value = 'portfolio';
  activeWorkbenchBucket.value = 'holdings';
  activeView.value = 'stocks';
  rememberPortfolio(portfolio);
  scheduleUserStateSync();
  await nextTick();
  await runAnalysis();
}

function deletePortfolioMemory(id: string) {
  portfolioMemory.value = portfolioMemory.value.filter((item) => item.id !== id);
  scheduleUserStateSync();
}

function recordRecommendationHistory(sourcePicks: Pick[], generatedAtIso: string) {
  const entries = sourcePicks
    .filter((pick) => pick.finalDecision?.action === 'accumulate' && pick.recommendationAudit?.entryPrice)
    .map((pick) => ({
      id: `${pick.symbol}-${pick.recommendationAudit?.openedAt || generatedAtIso}`,
      symbol: pick.symbol,
      name: pick.name,
      market: pick.market,
      openedAt: pick.recommendationAudit?.openedAt || generatedAtIso,
      scanGeneratedAt: generatedAtIso,
      entryPrice: Number(pick.recommendationAudit?.entryPrice ?? pick.price),
      action: pick.finalDecision?.action || 'accumulate',
      verdict: pick.finalDecision?.verdict || pick.verdict,
      confidence: Number(pick.finalDecision?.confidence ?? pick.confidence ?? 0),
      source: pick.discoverySource
    }));
  if (!entries.length) return;
  const seen = new Set<string>();
  recommendationHistory.value = [...entries, ...recommendationHistory.value]
    .filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    })
    .slice(0, RECOMMENDATION_HISTORY_LIMIT);
}

function savedScanTitle(scan: SavedScan) {
  const first = scan.picks[0];
  const lead = first ? `${first.symbol} ${first.name}` : scan.strategyName;
  return `${lead} · ${scan.picks.length}`;
}

function makeSavedScan(): SavedScan {
  const generated = scanGeneratedAtLabel();
  return {
    id: window.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title: `${scanStrategyLabel()} · ${generated}`,
    savedAt: new Date().toLocaleString(),
    generatedAt: generated,
    dataMode: dataMode.value,
    locale: locale.value,
    markets: [...(selectedMarkets.value.length ? selectedMarkets.value : defaultMarkets)],
    symbols: [...symbols.value],
    strategyId: selectedStrategyId.value,
    strategyName: scanStrategyLabel(),
    useCustom: useCustom.value,
    customWeights: { ...customWeights },
    picks: cloneJson(picks.value),
    sectors: cloneJson(sectors.value),
    errors: cloneJson(dataIssues.value),
    scanInfo: scanInfo.value ? { ...scanInfo.value } : null,
    portfolio: activePortfolio.value ? cloneJson(activePortfolio.value) : null
  };
}

function saveCurrentScan() {
  if (!canSaveScan.value) return;
  const snapshot = makeSavedScan();
  savedScans.value = [snapshot, ...savedScans.value.filter((scan) => scan.title !== snapshot.title)].slice(0, SAVED_SCAN_LIMIT);
  persistSavedScans();
}

function loadSavedScan(scan: SavedScan) {
  picks.value = cloneJson(scan.picks);
  sectors.value = cloneJson(scan.sectors);
  dataIssues.value = cloneJson(scan.errors);
  scanInfo.value = scan.scanInfo ? { ...scan.scanInfo } : null;
  importedPortfolio.value = scan.portfolio ? cloneJson(scan.portfolio) as PortfolioImportResponse : null;
  analysisPortfolio.value = scan.portfolio && 'matchedCount' in scan.portfolio ? cloneJson(scan.portfolio) as PortfolioAnalysis : null;
  generatedAt.value = scan.generatedAt;
  dataMode.value = scan.dataMode;
  selectedMarkets.value = scan.markets.filter(isMarket);
  symbolText.value = scan.symbols.join(', ');
  selectedStrategyId.value = scan.strategyId || selectedStrategyId.value;
  normalizeStrategySelection();
  useCustom.value = scan.useCustom;
  weightKeys.forEach((key) => {
    customWeights[key] = normalizeWeight(scan.customWeights?.[key]) ?? customWeights[key];
  });
  resultMarketFilter.value = 'all';
  resultVerdictFilter.value = 'all';
  activeView.value = 'stocks';
}

function deleteSavedScan(id: string) {
  savedScans.value = savedScans.value.filter((scan) => scan.id !== id);
  persistSavedScans();
}

function safeFilePart(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 42) || 'scan';
}

function downloadText(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function scanFilename(extension: 'md' | 'json') {
  const lead = picks.value[0]?.symbol ?? 'stock-picker';
  return `open-stock-picker-${safeFilePart(lead)}-${new Date().toISOString().slice(0, 10)}.${extension}`;
}

function markdownLine(value: string | number | undefined) {
  return String(value ?? '').replace(/\s+/g, ' ').trim();
}

function currentScanMarkdown() {
  const lines = [
    '# Open Stock Picker Scan',
    '',
    `- Generated: ${scanGeneratedAtLabel()}`,
    `- Data mode: ${dataModeLabel.value}`,
    `- Strategy: ${scanStrategyLabel()}`,
    `- Markets: ${(selectedMarkets.value.length ? selectedMarkets.value : defaultMarkets).map(marketLabel).join(', ')}`,
    `- Symbols: ${symbols.value.length ? symbols.value.join(', ') : 'Automatic market scan'}`,
    `- Results: ${picks.value.length} stocks, ${sectors.value.length} sectors`,
    ''
  ];

  const portfolio = activePortfolio.value;
  if (portfolio) {
    const copy = portfolioText().markdown;
    lines.push(`## ${copy.importedHoldings}`);
    lines.push('');
    lines.push(`- ${copy.source}: ${markdownLine(portfolio.sourceName)}`);
    lines.push(`- ${copy.currentHoldings}: ${portfolio.recognizedCount}`);
    lines.push(`- ${copy.totalMarketValue}: ${moneyLabel(portfolio.totalMarketValue)}`);
    lines.push(`- ${copy.unrealizedPnl}: ${signedMoneyLabel(portfolio.totalUnrealizedPnl)} (${percentLabel(portfolio.totalUnrealizedPnlPct)})`);
    if (portfolio.warnings?.length) {
      lines.push(`- ${copy.portfolioWarnings}:`);
      portfolio.warnings.slice(0, 4).forEach((note) => lines.push(`  - ${markdownLine(holdingNoteLabel(note))}`));
    }
    lines.push('');
  }

  picks.value.forEach((pick, index) => {
    lines.push(`## ${index + 1}. ${pick.symbol} · ${pick.name}`);
    lines.push('');
    lines.push(`- Market: ${marketLabel(pick.market)}`);
    lines.push(`- Verdict: ${finalVerdictLabel(pick)}`);
    if (pick.decisionEngine) {
      lines.push(`- ${decisionEngineTitle()}: ${decisionRegimeLabel(pick.decisionEngine.regime.name)} · ${decisionActionLabel(pick.decisionEngine.action)} · rank ${formatEngineScore(pick.decisionEngine.rankScore)}`);
      lines.push(`- ${dataQualityLabel(pick.decisionEngine.dataQuality.level)}: ${formatEngineScore(pick.decisionEngine.dataQuality.score)}/100`);
    }
    lines.push(`- Base score: ${pick.score}/100`);
    lines.push(`- Confidence: ${pick.confidence}%`);
    lines.push(`- Price: ${pick.currency} ${pick.price} (${pick.change > 0 ? '+' : ''}${pick.change}%)`);
    if (pick.overallAssessment) lines.push(`- ${t.value.finalReview}: ${markdownLine(pointLabel(pick.overallAssessment.summary))}`);
    if (pick.decision) lines.push(`- Decision: ${markdownLine(pointLabel(pick.decision.summary))}`);
    if (pick.newsHeatAnalysis) lines.push(`- ${t.value.newsHeat}: ${markdownLine(pointLabel(pick.newsHeatAnalysis.summary))}`);
    if (pick.actionPlan) lines.push(`- Action: ${markdownLine(pointLabel(pick.actionPlan.summary))}`);
    if (pick.tPlan) {
      lines.push(`- T plan: ${markdownLine(pointLabel(pick.tPlan.summary))}`);
      lines.push(`- T range: entry ${pick.currency} ${pick.tPlan.entryZone.low}-${pick.tPlan.entryZone.high}, take profit ${pick.currency} ${pick.tPlan.takeProfitZone.low}-${pick.tPlan.takeProfitZone.high}, stop ${pick.currency} ${pick.tPlan.stopLoss}`);
    }
    if (pick.holding && pick.holdingAnalysis) {
      const copy = portfolioText().markdown;
      lines.push(`- ${copy.holding}: ${pick.holding.quantity} ${copy.shares}, ${copy.cost} ${moneyLabel(pick.holding.costPrice, pick.currency)}, ${holdingFieldLabel('pnl')} ${percentLabel(pick.holding.unrealizedPnlPct)}, ${copy.action} ${holdingActionLabel(pick.holdingAnalysis.action)}`);
      pick.holdingAnalysis.notes.slice(0, 3).forEach((note) => lines.push(`  - ${markdownLine(holdingNoteLabel(note))}`));
    }
    const reasons = reasonLabels(pick).slice(0, 3);
    if (reasons.length) {
      lines.push('- Reasons:');
      reasons.forEach((reason) => lines.push(`  - ${markdownLine(reason)}`));
    }
    const signals = pick.signals.slice(0, 3);
    if (signals.length) {
      lines.push('- Signals:');
      signals.forEach((signal) => lines.push(`  - [${markdownLine(signal.title)}](${signal.link}) · ${signal.source}`));
    }
    lines.push('');
  });

  if (sectors.value.length) {
    lines.push('## Sectors');
    lines.push('');
    sectors.value.forEach((sector) => {
      lines.push(`- ${sector.name}: ${sector.score}/100 · ${sectorRecommendationLabel(sector.recommendation)} · ${sector.count} constituents`);
    });
    lines.push('');
  }

  lines.push('This export is research support only, not financial advice.');
  return lines.join('\n');
}

function exportMarkdown() {
  if (!canSaveScan.value) return;
  downloadText(scanFilename('md'), currentScanMarkdown(), 'text/markdown');
}

function exportJson() {
  if (!canSaveScan.value) return;
  downloadText(scanFilename('json'), JSON.stringify(makeSavedScan(), null, 2), 'application/json');
}

function filteredEmptyTitle() {
  if (locale.value === 'en') return 'No matches for these filters';
  if (locale.value === 'zh-CN') return '没有符合筛选的结果';
  if (locale.value === 'ja') return '条件に合う結果がありません';
  if (locale.value === 'ko') return '필터에 맞는 결과가 없습니다';
  if (locale.value === 'nan-TW') return '無符合篩選的結果';
  return '沒有符合篩選的結果';
}

function filteredEmptyHint() {
  if (locale.value === 'en') return 'Change the market or call filter to bring more candidates back.';
  if (locale.value === 'zh-CN') return '调整市场或判断筛选，就能看到更多候选。';
  if (locale.value === 'ja') return '市場または判断条件を変えると、候補を戻せます。';
  if (locale.value === 'ko') return '시장 또는 판단 필터를 바꾸면 더 많은 후보를 볼 수 있습니다.';
  if (locale.value === 'nan-TW') return '調整市場抑是判斷篩選，就會看著較濟候選。';
  return '調整市場或判斷篩選，就能看到更多候選。';
}

function factorLabel(value: string | number | undefined) {
  const key = String(value ?? '') as keyof StrategyWeights;
  return t.value[key] ?? String(value ?? '');
}

function instrumentLabel(pick: Pick) {
  if (pick.instrumentType === 'etf') {
    return localeText({
      en: 'ETF',
      'zh-CN': 'ETF',
      'zh-TW': 'ETF',
      ja: 'ETF',
      ko: 'ETF'
    });
  }
  return localeText({
    en: 'Stock',
    'zh-CN': '股票',
    'zh-TW': '股票',
    ja: '個別株',
    ko: '주식'
  });
}

function financialReviewTitle(pick: Pick) {
  if (pick.instrumentType === 'etf') {
    return localeText({
      en: 'ETF analysis',
      'zh-CN': 'ETF 分析',
      'zh-TW': 'ETF 分析',
      ja: 'ETF 分析',
      ko: 'ETF 분석'
    });
  }
  return t.value.financialReview;
}

function decisionToplineLabel() {
  return localeText({
    en: 'Current decision',
    'zh-CN': '当前决策',
    'zh-TW': '當前決策',
    ja: '現在の判断',
    ko: '현재 의사결정'
  });
}

function decisionSnapshotItems(pick: Pick) {
  if (pick.decisionEngine) {
    const dangerGates = pick.decisionEngine.gates.filter((gate) => gate.severity === 'danger').length;
    const warningGates = pick.decisionEngine.gates.filter((gate) => gate.severity === 'warning').length;
    const gateValue = dangerGates || warningGates
      ? `${dangerGates ? `${dangerGates}D` : ''}${dangerGates && warningGates ? ' / ' : ''}${warningGates ? `${warningGates}W` : ''}`
      : localeText({ en: 'Clear', 'zh-CN': '通过', 'zh-TW': '通過', ja: '通過', ko: '통과' });
    return [
      { key: 'buy', label: decisionActionLabel('accumulate'), value: `${formatEngineScore(pick.decisionEngine.buyScore)}/100`, tone: 'buy' },
      { key: 'sell', label: decisionActionLabel('reduce'), value: `${formatEngineScore(pick.decisionEngine.sellScore)}/100`, tone: pick.decisionEngine.sellScore >= 68 ? 'sell' : 'watch' },
      { key: 'data', label: dataQualityLabel(pick.decisionEngine.dataQuality.level), value: `${formatEngineScore(pick.decisionEngine.dataQuality.score)}/100`, tone: pick.decisionEngine.dataQuality.level },
      { key: 'gate', label: t.value.riskControls, value: gateValue, tone: dangerGates ? 'sell' : warningGates ? 'watch' : 'buy' }
    ];
  }
  return reportMetricItems(pick).slice(0, 4).map((metric) => ({
    key: metric.key,
    label: metric.label,
    value: metric.value,
    tone: Number(metric.score ?? 0) >= 70 ? 'buy' : Number(metric.score ?? 0) < 45 ? 'sell' : 'watch'
  }));
}

function etfPanelTitle(pick: Pick) {
  const regime = pick.decisionEngine?.regime.name;
  if (regime === 'defensive_etf_core') return decisionRegimeLabel(regime);
  if (regime === 'sector_etf_tactical') return decisionRegimeLabel(regime);
  return localeText({
    en: 'ETF profile',
    'zh-CN': 'ETF 档案',
    'zh-TW': 'ETF 檔案',
    ja: 'ETFプロファイル',
    ko: 'ETF 프로필'
  });
}

function etfProfileRows(pick: Pick) {
  const etfMetrics = pick.financialAnalysis?.metrics
    ?.filter((metric) => String(metric.key).toLowerCase().includes('etf'))
    .slice(0, 6)
    .map((metric) => ({
      key: metric.key,
      label: financialMetricLabel(metric),
      value: metric.value,
      score: metric.score
    })) ?? [];
  if (etfMetrics.length) return etfMetrics;
  const rows = [];
  if (pick.decisionEngine) {
    rows.push({ key: 'decisionRank', label: resultSortLabel('decision'), value: `${formatEngineScore(pick.decisionEngine.rankScore)}/100`, score: pick.decisionEngine.rankScore });
    rows.push({ key: 'riskReward', label: t.value.riskControls, value: `${formatEngineScore(pick.decisionEngine.riskRewardScore)}/100`, score: pick.decisionEngine.riskRewardScore });
  }
  if (pick.tPlan) rows.push({ key: 'liquidity', label: strategyMetricLabel('liquidityScore'), value: `${Number(pick.tPlan.components.liquidityScore).toFixed(1)}/100`, score: pick.tPlan.components.liquidityScore });
  if (pick.trendAnalysis) rows.push({ key: 'trend', label: strategyMetricLabel('nextSessionContinuationScore'), value: `${Number(pick.trendAnalysis.continuationScore).toFixed(1)}/100`, score: pick.trendAnalysis.continuationScore });
  if (pick.downsideRiskScore !== undefined) rows.push({ key: 'downside', label: strategyMetricLabel('downsideRiskInverse'), value: `${Number(100 - pick.downsideRiskScore).toFixed(1)}/100`, score: 100 - pick.downsideRiskScore });
  return rows.slice(0, 6);
}

function holdingPlanTitle() {
  return localeText({
    en: 'Position plan',
    'zh-CN': '仓位计划',
    'zh-TW': '倉位計畫',
    ja: 'ポジション計画',
    ko: '포지션 계획'
  });
}

function holdingPlannedQuantityTitle() {
  return localeText({
    en: 'Planned shares',
    'zh-CN': '计划股数',
    'zh-TW': '計畫股數',
    ja: '計画株数',
    ko: '계획 수량'
  });
}

function holdingExecutableQuantityTitle() {
  return localeText({
    en: 'Executable today',
    'zh-CN': '今日可执行',
    'zh-TW': '今日可執行',
    ja: '本日実行可',
    ko: '오늘 실행 가능'
  });
}

function holdingExecutionStatusLabel(status: string | undefined) {
  if (status === 'blocked_today') {
    return localeText({ en: 'T+1 locked', 'zh-CN': 'T+1 今日不可卖', 'zh-TW': 'T+1 今日不可賣', ja: 'T+1 売却不可', ko: 'T+1 매도 불가' });
  }
  if (status === 'partial_t1_locked') {
    return localeText({ en: 'Partially locked', 'zh-CN': '部分 T+1 锁定', 'zh-TW': '部分 T+1 鎖定', ja: '一部 T+1 制限', ko: '일부 T+1 잠김' });
  }
  return localeText({ en: 'Executable', 'zh-CN': '可执行', 'zh-TW': '可執行', ja: '実行可', ko: '실행 가능' });
}

function signedQuantityLabel(value: number | null | undefined) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number) || number === 0) return '0';
  return `${number > 0 ? '+' : ''}${number}`;
}

function holdingRowSeverity(row: HoldingRowView) {
  if (row.action === 'exit') return 5;
  if (row.action === 'reduce') return 4;
  if (row.executionStatus === 'blocked_today' || row.executionStatus === 'partial_t1_locked') return 3;
  if (Number(row.livePriceDriftPct ?? 0) >= 1) return 2;
  return 1;
}

function holdingRowAvailableLabel(row: HoldingRowView) {
  const available = row.availableQuantity !== null && row.availableQuantity !== undefined
    ? quantityAbsLabel(row.availableQuantity)
    : '-';
  const blocked = nonNegativeQuantity(row.blockedQuantity);
  if (blocked <= 0) return available;
  return `${available} / T+1 ${quantityAbsLabel(blocked)}`;
}

function holdingRowPriceSourceLabel(row: HoldingRowView) {
  if (row.livePriceDriftPct !== null && row.livePriceDriftPct !== undefined) {
    const drift = percentLabel(row.livePriceDriftPct);
    if (locale.value === 'en') return `Broker drift ${drift}`;
    if (locale.value === 'zh-CN') return `券商/实时偏差 ${drift}`;
    if (locale.value === 'ja') return `証券/リアル差 ${drift}`;
    if (locale.value === 'ko') return `증권/실시간 차이 ${drift}`;
    return `券商/即時偏差 ${drift}`;
  }
  if (row.quoteStatus) return quoteConsensusLabel(row.quoteStatus);
  return localeText({ en: 'Price source ok', 'zh-CN': '价格源正常', 'zh-TW': '價格源正常', ja: '価格ソース正常', ko: '가격 출처 정상' });
}

function holdingRowDetailTitle() {
  return localeText({ en: 'Rules and notes', 'zh-CN': '规则与原因', 'zh-TW': '規則與原因', ja: '規則と理由', ko: '규칙과 사유' });
}

function holdingRowRuleLabel(row: HoldingRowView) {
  return holdingRuleLabel(row.orderSizing, row.market);
}

function decisionEngineTitle() {
  return localeText({
    en: 'Decision engine',
    'zh-CN': '决策引擎',
    'zh-TW': '決策引擎',
    ja: '判断エンジン',
    ko: '의사결정 엔진'
  });
}

function professionalAnalyticsTitle() {
  return localeText({
    en: 'Professional analytics',
    'zh-CN': '专业投研分析',
    'zh-TW': '專業投研分析',
    ja: 'プロ分析',
    ko: '전문 분석'
  });
}

function professionalModuleLabel(key: string) {
  const labels: Record<string, LocalizedText> = {
    factor: { en: 'Factor model', 'zh-CN': '因子模型', 'zh-TW': '因子模型', ja: 'ファクターモデル', ko: '팩터 모델' },
    benchmark: { en: 'Benchmark', 'zh-CN': '基准比较', 'zh-TW': '基準比較', ja: 'ベンチマーク', ko: '벤치마크' },
    tracker: { en: 'Tracker', 'zh-CN': '推荐追踪', 'zh-TW': '推薦追蹤', ja: '追跡', ko: '추적' },
    attribution: { en: 'Attribution', 'zh-CN': '归因', 'zh-TW': '歸因', ja: '要因分解', ko: '기여 분석' },
    optimizer: { en: 'Portfolio optimizer', 'zh-CN': '组合优化器', 'zh-TW': '組合優化器', ja: 'ポートフォリオ最適化', ko: '포트폴리오 최적화' },
    alerts: { en: 'Alert monitor', 'zh-CN': '监控提醒器', 'zh-TW': '監控提醒器', ja: 'アラート監視', ko: '알림 모니터' }
  };
  return localeText(labels[key] ?? labels.factor);
}

function benchmarkRankLabel(rank: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    outperforming: { en: 'Outperforming', 'zh-CN': '跑赢基准', 'zh-TW': '跑贏基準', ja: 'アウトパフォーム', ko: '초과 성과' },
    'in-line': { en: 'In line', 'zh-CN': '接近基准', 'zh-TW': '接近基準', ja: '基準並み', ko: '기준 부합' },
    lagging: { en: 'Lagging', 'zh-CN': '落后基准', 'zh-TW': '落後基準', ja: '劣後', ko: '부진' }
  };
  return localeText(labels[rank || 'in-line'] ?? labels['in-line']);
}

function alertPriorityLabel(priority: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    high: { en: 'High priority', 'zh-CN': '高优先级', 'zh-TW': '高優先級', ja: '高優先度', ko: '높은 우선순위' },
    medium: { en: 'Medium priority', 'zh-CN': '中优先级', 'zh-TW': '中優先級', ja: '中優先度', ko: '중간 우선순위' },
    normal: { en: 'Normal', 'zh-CN': '普通', 'zh-TW': '普通', ja: '通常', ko: '일반' }
  };
  return localeText(labels[priority || 'normal'] ?? labels.normal);
}

function contributionLabel(value: number | undefined) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return '0.0';
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(1)}`;
}

function professionalFactorRows(pick: Pick) {
  return pick.professionalAnalytics?.factorModel.exposures.slice(0, 6) ?? [];
}

function professionalCheckpointLabel(pick: Pick) {
  const checkpoints = pick.professionalAnalytics?.recommendationTracker.checkpoints ?? [];
  return checkpoints.map((item) => `${item.horizon} ${item.targetReturnPct > 0 ? '+' : ''}${item.targetReturnPct}%`).join(' · ');
}

function decisionActionLabel(action: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    accumulate: { en: 'Accumulate', 'zh-CN': '分批买入', 'zh-TW': '分批買入', ja: '段階的に買い', ko: '분할 매수' },
    hold: { en: 'Hold / wait', 'zh-CN': '持有观察', 'zh-TW': '持有觀察', ja: '保有/待機', ko: '보유/대기' },
    reduce: { en: 'Reduce risk', 'zh-CN': '降低风险', 'zh-TW': '降低風險', ja: 'リスク削減', ko: '리스크 축소' },
    exit: { en: 'Exit', 'zh-CN': '退出', 'zh-TW': '退出', ja: '撤退', ko: '이탈' }
  };
  return localeText(labels[action || 'hold'] ?? labels.hold);
}

function decisionRegimeLabel(regime: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    quality_compounder: { en: 'Quality compounder', 'zh-CN': '优质复利股', 'zh-TW': '優質複利股', ja: '高品質成長', ko: '우량 복리형' },
    momentum_breakout: { en: 'Momentum breakout', 'zh-CN': '动能突破', 'zh-TW': '動能突破', ja: 'モメンタム突破', ko: '모멘텀 돌파' },
    deep_value_turnaround: { en: 'Value turnaround', 'zh-CN': '低估修复', 'zh-TW': '低估修復', ja: '割安反転', ko: '가치 반등' },
    event_driven: { en: 'Event driven', 'zh-CN': '事件催化', 'zh-TW': '事件催化', ja: 'イベント主導', ko: '이벤트 주도' },
    falling_knife: { en: 'Falling knife', 'zh-CN': '下跌破位', 'zh-TW': '下跌破位', ja: '急落リスク', ko: '급락 리스크' },
    overheated: { en: 'Overheated', 'zh-CN': '短线过热', 'zh-TW': '短線過熱', ja: '過熱', ko: '과열' },
    balanced_watch: { en: 'Balanced watch', 'zh-CN': '综合观察', 'zh-TW': '綜合觀察', ja: '総合監視', ko: '종합 관찰' },
    insufficient_data: { en: 'Insufficient data', 'zh-CN': '数据不足', 'zh-TW': '資料不足', ja: 'データ不足', ko: '데이터 부족' },
    defensive_etf_core: { en: 'Core ETF', 'zh-CN': '核心 ETF', 'zh-TW': '核心 ETF', ja: 'コアETF', ko: '코어 ETF' },
    sector_etf_tactical: { en: 'Tactical ETF', 'zh-CN': '战术 ETF', 'zh-TW': '戰術 ETF', ja: '戦術ETF', ko: '전술 ETF' }
  };
  return localeText(labels[regime || 'balanced_watch'] ?? labels.balanced_watch);
}

function dataQualityLabel(level: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    strong: { en: 'Strong data', 'zh-CN': '数据充分', 'zh-TW': '資料充分', ja: '強いデータ', ko: '데이터 강함' },
    usable: { en: 'Usable data', 'zh-CN': '数据可用', 'zh-TW': '資料可用', ja: '利用可能', ko: '사용 가능' },
    thin: { en: 'Thin data', 'zh-CN': '数据偏薄', 'zh-TW': '資料偏薄', ja: 'データ薄め', ko: '데이터 부족' },
    weak: { en: 'Weak data', 'zh-CN': '数据不足', 'zh-TW': '資料不足', ja: 'データ不足', ko: '데이터 약함' }
  };
  return localeText(labels[level || 'thin'] ?? labels.thin);
}

function decisionGateLabel(key: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    dataQualityTooWeak: { en: 'Data quality blocks new buy', 'zh-CN': '数据质量不足，阻止买入', 'zh-TW': '資料品質不足，阻止買入', ja: 'データ品質が買いを阻止', ko: '데이터 품질이 매수를 제한' },
    severePriceBreakdown: { en: 'Severe price breakdown', 'zh-CN': '严重破位下跌', 'zh-TW': '嚴重破位下跌', ja: '深刻な下落', ko: '심각한 가격 이탈' },
    largePriceBreakdown: { en: 'Large price breakdown', 'zh-CN': '明显破位下跌', 'zh-TW': '明顯破位下跌', ja: '大きな下落', ko: '큰 가격 이탈' },
    downsideRiskUrgent: { en: 'Urgent downside risk', 'zh-CN': '下行风险紧急', 'zh-TW': '下行風險緊急', ja: '下落リスク大', ko: '하방 리스크 긴급' },
    downsideRiskHigh: { en: 'High downside risk', 'zh-CN': '下行风险偏高', 'zh-TW': '下行風險偏高', ja: '下落リスク高め', ko: '하방 리스크 높음' },
    reversalRiskHigh: { en: 'Reversal risk high', 'zh-CN': '反转风险偏高', 'zh-TW': '反轉風險偏高', ja: '反転リスク高め', ko: '반전 리스크 높음' },
    pullbackRiskExtreme: { en: 'Pullback risk extreme', 'zh-CN': '回撤风险极高', 'zh-TW': '回撤風險極高', ja: '反落リスク極大', ko: '되돌림 리스크 극단' },
    negativeNewsDominates: { en: 'Negative news dominates', 'zh-CN': '负面新闻占优', 'zh-TW': '負面新聞占優', ja: '悪材料優勢', ko: '부정 뉴스 우세' },
    negativeNewsSevere: { en: 'Severe negative news', 'zh-CN': '重大负面新闻', 'zh-TW': '重大負面新聞', ja: '重大悪材料', ko: '중대 부정 뉴스' },
    liquidityTooWeak: { en: 'Liquidity too weak', 'zh-CN': '流动性不足', 'zh-TW': '流動性不足', ja: '流動性不足', ko: '유동성 부족' },
    etfLiquidityWeak: { en: 'ETF liquidity weak', 'zh-CN': 'ETF 流动性偏弱', 'zh-TW': 'ETF 流動性偏弱', ja: 'ETF流動性弱め', ko: 'ETF 유동성 약함' },
    financialQualityWeak: { en: 'Financial quality weak', 'zh-CN': '财务质量偏弱', 'zh-TW': '財務品質偏弱', ja: '財務品質弱め', ko: '재무 품질 약함' },
    sourceStackUnstable: { en: 'Source stack unstable', 'zh-CN': '数据源不稳，阻止新买入', 'zh-TW': '資料源不穩，阻止新買入', ja: 'データソース不安定', ko: '데이터 소스 불안정' },
    priceConsensusConflict: { en: 'Quote sources conflict', 'zh-CN': '报价来源冲突，阻止新买入', 'zh-TW': '報價來源衝突，阻止新買入', ja: '価格ソース衝突', ko: '호가 출처 충돌' },
    outsideTradingSession: { en: 'Outside live session', 'zh-CN': '非实时交易时段', 'zh-TW': '非即時交易時段', ja: '取引時間外', ko: '실시간 장외' },
    openingConfirmationPending: { en: 'Opening confirmation pending', 'zh-CN': '等待开盘确认', 'zh-TW': '等待開盤確認', ja: '寄り付き確認待ち', ko: '개장 확인 대기' },
    localMarketFastDrop: { en: 'Local market fast drop', 'zh-CN': '本地市场快速下跌', 'zh-TW': '本地市場快速下跌', ja: '現地市場の急落', ko: '현지 시장 급락' },
    localMarketIntradayDrop: { en: 'Intraday drop blocks buy', 'zh-CN': '盘中下跌阻止买入', 'zh-TW': '盤中下跌阻止買入', ja: '日中下落で買い停止', ko: '장중 하락으로 매수 제한' },
    etfTrendBreakdown: { en: 'ETF trend breakdown', 'zh-CN': 'ETF 趋势破位', 'zh-TW': 'ETF 趨勢破位', ja: 'ETFトレンド崩れ', ko: 'ETF 추세 이탈' },
    etfHighBetaIntradayDrop: { en: 'High-beta ETF drop', 'zh-CN': '高波动 ETF 盘中下跌', 'zh-TW': '高波動 ETF 盤中下跌', ja: '高ベータETF下落', ko: '고베타 ETF 하락' },
    etfIntradayDrop: { en: 'ETF intraday drop', 'zh-CN': 'ETF 盘中下跌', 'zh-TW': 'ETF 盤中下跌', ja: 'ETF日中下落', ko: 'ETF 장중 하락' },
    hotListChaseRisk: { en: 'Hot-list chase risk', 'zh-CN': '热榜追高风险', 'zh-TW': '熱榜追高風險', ja: '人気銘柄追随リスク', ko: '인기 목록 추격 리스크' },
    hotListDiscoveryNeedsConfirmation: { en: 'Hot-list idea needs confirmation', 'zh-CN': '热榜候选需确认', 'zh-TW': '熱榜候選需確認', ja: '人気候補は確認待ち', ko: '인기 후보 확인 필요' }
  };
  return localeText(labels[key || ''] ?? { en: String(key ?? ''), 'zh-CN': String(key ?? ''), 'zh-TW': String(key ?? ''), ja: String(key ?? ''), ko: String(key ?? '') });
}

function decisionReasonLabel(reason: string) {
  if (reason.startsWith('holding:')) {
    return holdingNoteLabel({ key: reason.replace('holding:', ''), severity: 'info', params: {} });
  }
  if (reason.startsWith('regime:')) return decisionRegimeLabel(reason.replace('regime:', ''));
  if (reason.startsWith('dataQuality:')) return dataQualityLabel(reason.replace('dataQuality:', ''));
  if (reason.startsWith('marketSupport:')) return `${marketSupportTitle()} · ${marketCoverageTierLabel(reason.replace('marketSupport:', ''))}`;
  if (reason === 'legacyWeights:secondary') {
    return localeText({
      en: 'Legacy weights are secondary',
      'zh-CN': '旧权重仅作辅助',
      'zh-TW': '舊權重僅作輔助',
      ja: '旧ウェイトは補助',
      ko: '기존 가중치는 보조'
    });
  }
  return decisionGateLabel(reason);
}

function formatEngineScore(value: number | undefined) {
  const numeric = Number(value ?? 0);
  return Number.isFinite(numeric) ? numeric.toFixed(1) : '0.0';
}

function engineCoverageLabel(pick: Pick) {
  const engine = pick.decisionEngine;
  if (!engine) return '';
  const price = formatEngineScore(engine.dataQuality.priceHistoryScore);
  const news = formatEngineScore(engine.dataQuality.newsCoverageScore);
  if (locale.value === 'en') return `${price} price · ${news} news`;
  if (locale.value === 'zh-CN') return `${price} 价格 · ${news} 新闻`;
  if (locale.value === 'ja') return `${price} 価格 · ${news} ニュース`;
  if (locale.value === 'ko') return `${price} 가격 · ${news} 뉴스`;
  return `${price} 價格 · ${news} 新聞`;
}

function scoreWeightLabel(item: { weight: number; baseWeight?: number; available?: boolean }) {
  const effective = Number(item.weight).toFixed(1);
  const base = item.baseWeight === undefined ? effective : Number(item.baseWeight).toFixed(1);
  if (item.available === false) return `0.0% (${base}%)`;
  return base !== effective ? `${base}% -> ${effective}%` : `${effective}%`;
}

function localeText(text: LocalizedText) {
  return text[locale.value as StandardLocale] ?? text.en;
}

function strategyMetricLabel(metric: string) {
  const labels: Record<string, LocalizedText> = {
    overallTotal: { en: 'Final total', 'zh-CN': '最终总分', 'zh-TW': '最終總分', ja: '最終総合', ko: '최종 종합' },
    todayBuyScore: { en: 'Buy today', 'zh-CN': '今日买入', 'zh-TW': '今日買入', ja: '本日買い', ko: '오늘 매수' },
    futureRiseScore: { en: 'Future rise', 'zh-CN': '后续上涨', 'zh-TW': '後續上漲', ja: '今後の上昇', ko: '향후 상승' },
    profitableExitScore: { en: 'Profitable exit', 'zh-CN': '盈利卖出', 'zh-TW': '盈利賣出', ja: '利益確定', ko: '수익 매도' },
    newsHeatImpactScore: { en: 'News heat impact', 'zh-CN': '新闻热度影响', 'zh-TW': '新聞熱度影響', ja: 'ニュース熱量影響', ko: '뉴스 열기 영향' },
    breakoutSetupScore: { en: 'Breakout setup', 'zh-CN': '突破 setup', 'zh-TW': '突破 setup', ja: 'ブレイク設定', ko: '돌파 setup' },
    pullbackRiskScore: { en: 'Pullback risk', 'zh-CN': '回落风险', 'zh-TW': '回落風險', ja: '反落リスク', ko: '되돌림 리스크' },
    pullbackRiskInverse: { en: 'Pullback safety', 'zh-CN': '回落安全度', 'zh-TW': '回落安全度', ja: '反落安全度', ko: '되돌림 안전도' },
    downsideRiskScore: { en: 'Downside risk', 'zh-CN': '下跌风险', 'zh-TW': '下跌風險', ja: '下落リスク', ko: '하방 리스크' },
    downsideRiskInverse: { en: 'Downside safety', 'zh-CN': '下跌安全度', 'zh-TW': '下跌安全度', ja: '下落安全度', ko: '하방 안전도' },
    nextSessionContinuationScore: { en: 'Next-session continuation', 'zh-CN': '次日延续', 'zh-TW': '次日延續', ja: '翌日継続', ko: '다음 세션 지속' },
    nextSessionReversalRiskScore: { en: 'Next-session reversal risk', 'zh-CN': '次日反转风险', 'zh-TW': '次日反轉風險', ja: '翌日反転リスク', ko: '다음 세션 반전 리스크' },
    nextSessionReversalRiskInverse: { en: 'Reversal safety', 'zh-CN': '反转安全度', 'zh-TW': '反轉安全度', ja: '反転安全度', ko: '반전 안전도' },
    maStructureScore: { en: 'MA structure', 'zh-CN': '均线结构', 'zh-TW': '均線結構', ja: '移動平均構造', ko: '이동평균 구조' },
    rsiScore: { en: 'RSI health', 'zh-CN': 'RSI 健康度', 'zh-TW': 'RSI 健康度', ja: 'RSI 健全性', ko: 'RSI 건강도' },
    macdScore: { en: 'MACD confirmation', 'zh-CN': 'MACD 确认', 'zh-TW': 'MACD 確認', ja: 'MACD 確認', ko: 'MACD 확인' },
    volumeConfirmationScore: { en: 'Volume confirmation', 'zh-CN': '量能确认', 'zh-TW': '量能確認', ja: '出来高確認', ko: '거래량 확인' },
    supportScore: { en: 'Support position', 'zh-CN': '支撑位置', 'zh-TW': '支撐位置', ja: '支持位置', ko: '지지 위치' },
    tScore: { en: 'T / exit score', 'zh-CN': '做T/卖出分', 'zh-TW': '做T/賣出分', ja: 'T/売却スコア', ko: 'T/매도 점수' },
    liquidityScore: { en: 'Liquidity', 'zh-CN': '流动性', 'zh-TW': '流動性', ja: '流動性', ko: '유동성' },
    volatilityScore: { en: 'Tradable volatility', 'zh-CN': '可交易波动', 'zh-TW': '可交易波動', ja: '取引可能な変動', ko: '거래 가능한 변동성' },
    fundFlowScore: { en: 'Fund flow', 'zh-CN': '资金流', 'zh-TW': '資金流', ja: '資金フロー', ko: '자금 흐름' },
    shortTermScore: { en: 'Short-term fit', 'zh-CN': '短线适配', 'zh-TW': '短線適配', ja: '短期適合', ko: '단기 적합' },
    midLongTermScore: { en: 'Mid/long fit', 'zh-CN': '中长线适配', 'zh-TW': '中長線適配', ja: '中長期適合', ko: '중장기 적합' },
    stabilityScore: { en: 'Score stability', 'zh-CN': '评分稳定性', 'zh-TW': '評分穩定性', ja: 'スコア安定性', ko: '점수 안정성' },
    qualityCompositeScore: { en: 'Quality stability', 'zh-CN': '稳定优质', 'zh-TW': '穩定優質', ja: '品質安定性', ko: '품질 안정성' },
    priceChange: { en: 'Price change', 'zh-CN': '涨跌幅', 'zh-TW': '漲跌幅', ja: '騰落率', ko: '등락률' }
  };
  return labels[metric] ? localeText(labels[metric]) : factorLabel(metric);
}

function strategyRuleTitle(key: string) {
  const labels: Record<string, LocalizedText> = {
    strategyGateTodayBuy: { en: 'Today entry must be strong enough', 'zh-CN': '今日进场条件必须足够强', 'zh-TW': '今日進場條件必須足夠強', ja: '本日エントリー条件が必要', ko: '오늘 진입 조건 필요' },
    strategyGateFutureRise: { en: 'Future rise must clear the strategy floor', 'zh-CN': '后续上涨空间必须过线', 'zh-TW': '後續上漲空間必須過線', ja: '今後の上昇余地が必要', ko: '향후 상승 여지가 필요' },
    strategyGateProfitableExit: { en: 'Later profitable exit must be realistic', 'zh-CN': '之后盈利卖出必须现实', 'zh-TW': '之後盈利賣出必須現實', ja: '利益確定余地が必要', ko: '이후 수익 매도가 현실적이어야 함' },
    strategyGateDownside: { en: 'Downside risk must stay controlled', 'zh-CN': '下跌风险必须受控', 'zh-TW': '下跌風險必須受控', ja: '下落リスクの制御が必要', ko: '하방 리스크가 통제되어야 함' },
    strategyGateBreakout: { en: 'Breakout must have price confirmation', 'zh-CN': '突破必须有价格确认', 'zh-TW': '突破必須有價格確認', ja: 'ブレイクの価格確認が必要', ko: '돌파 가격 확인 필요' },
    strategyGateVolume: { en: 'Volume must confirm the move', 'zh-CN': '量能必须确认', 'zh-TW': '量能必須確認', ja: '出来高確認が必要', ko: '거래량 확인 필요' },
    strategyGatePullback: { en: 'Pullback risk must be acceptable', 'zh-CN': '回落风险必须可接受', 'zh-TW': '回落風險必須可接受', ja: '反落リスクが許容範囲内', ko: '되돌림 리스크 허용 범위' },
    strategyGateReversal: { en: 'Reversal risk must be low enough', 'zh-CN': '反转风险必须足够低', 'zh-TW': '反轉風險必須足夠低', ja: '反転リスクが低いこと', ko: '반전 리스크가 충분히 낮아야 함' },
    strategyGateContinuation: { en: 'Next session must be able to continue', 'zh-CN': '次日必须有延续能力', 'zh-TW': '次日必須有延續能力', ja: '翌日継続力が必要', ko: '다음 세션 지속력 필요' },
    strategyGateMacd: { en: 'MACD must confirm', 'zh-CN': 'MACD 必须确认', 'zh-TW': 'MACD 必須確認', ja: 'MACD 確認が必要', ko: 'MACD 확인 필요' },
    strategyGateTScore: { en: 'T / exit trade must be executable', 'zh-CN': '做T/卖出窗口必须可执行', 'zh-TW': '做T/賣出窗口必須可執行', ja: 'T/売却が実行可能', ko: 'T/매도 실행 가능해야 함' },
    strategyGateLiquidity: { en: 'Liquidity must support the trade', 'zh-CN': '流动性必须支撑交易', 'zh-TW': '流動性必須支撐交易', ja: '流動性が必要', ko: '유동성 필요' },
    strategyGateVolatility: { en: 'Tradable range must exist', 'zh-CN': '必须有可交易价差', 'zh-TW': '必須有可交易價差', ja: '取引可能な値幅が必要', ko: '거래 가능한 범위 필요' },
    strategyGateNewsHeat: { en: 'Catalyst heat must be visible', 'zh-CN': '题材热度必须明显', 'zh-TW': '題材熱度必須明顯', ja: '材料熱量が必要', ko: '재료 열기 필요' },
    strategyGateSentiment: { en: 'Sentiment must support the catalyst', 'zh-CN': '情绪必须支持题材', 'zh-TW': '情緒必須支持題材', ja: 'センチメント確認が必要', ko: '심리 확인 필요' },
    strategyGateFundFlow: { en: 'Fund flow cannot fight the setup', 'zh-CN': '资金流不能明显背离', 'zh-TW': '資金流不能明顯背離', ja: '資金フローの逆行を避ける', ko: '자금 흐름 역행 금지' },
    strategyGateMaStructure: { en: 'Moving averages must be constructive', 'zh-CN': '均线结构必须健康', 'zh-TW': '均線結構必須健康', ja: '移動平均構造が必要', ko: '이동평균 구조 필요' },
    strategyGateRsi: { en: 'RSI condition must confirm', 'zh-CN': 'RSI 条件必须确认', 'zh-TW': 'RSI 條件必須確認', ja: 'RSI 条件確認が必要', ko: 'RSI 조건 확인 필요' },
    strategyGateQuality: { en: 'Quality must pass', 'zh-CN': '基本面质量必须过线', 'zh-TW': '基本面品質必須過線', ja: '品質条件が必要', ko: '품질 조건 필요' },
    strategyGateValue: { en: 'Valuation must be acceptable', 'zh-CN': '估值必须可接受', 'zh-TW': '估值必須可接受', ja: '評価水準が必要', ko: '밸류에이션 조건 필요' },
    strategyGateRisk: { en: 'Risk score must pass', 'zh-CN': '风险分必须过线', 'zh-TW': '風險分必須過線', ja: 'リスク点が必要', ko: '리스크 점수 필요' },
    strategyGateShortTerm: { en: 'Short-term model must pass', 'zh-CN': '短线模型必须过线', 'zh-TW': '短線模型必須過線', ja: '短期モデルが必要', ko: '단기 모델 통과 필요' },
    strategyGateMidLongQuality: { en: 'Mid/long quality must pass', 'zh-CN': '中长线优质分必须过线', 'zh-TW': '中長線優質分必須過線', ja: '中長期品質が必要', ko: '중장기 품질 통과 필요' },
    strategyGateStableQuality: { en: 'Quality stability must pass', 'zh-CN': '稳定优质分必须过线', 'zh-TW': '穩定優質分必須過線', ja: '品質安定性が必要', ko: '품질 안정성 통과 필요' },
    strategyVetoSevereDrop: { en: 'Severe drop blocks this strategy', 'zh-CN': '大跌会直接阻断策略', 'zh-TW': '大跌會直接阻斷策略', ja: '急落は戦略除外', ko: '급락은 전략 차단' },
    strategyVetoDownside: { en: 'Downside risk veto', 'zh-CN': '下跌风险否决', 'zh-TW': '下跌風險否決', ja: '下落リスク除外', ko: '하방 리스크 차단' },
    strategyVetoReversal: { en: 'Reversal risk veto', 'zh-CN': '反转风险否决', 'zh-TW': '反轉風險否決', ja: '反転リスク除外', ko: '반전 리스크 차단' },
    strategyVetoNoVolume: { en: 'No volume confirmation', 'zh-CN': '量能未确认', 'zh-TW': '量能未確認', ja: '出来高未確認', ko: '거래량 미확인' },
    strategyVetoOverheated: { en: 'Overheated chase risk', 'zh-CN': '追高过热风险', 'zh-TW': '追高過熱風險', ja: '過熱追随リスク', ko: '과열 추격 리스크' },
    strategyVetoContinuationBreak: { en: 'Continuation has broken', 'zh-CN': '延续性已经破坏', 'zh-TW': '延續性已經破壞', ja: '継続性が崩れた', ko: '지속성 훼손' },
    strategyVetoLiquidity: { en: 'Liquidity veto', 'zh-CN': '流动性否决', 'zh-TW': '流動性否決', ja: '流動性除外', ko: '유동성 차단' },
    strategyVetoNewsCold: { en: 'Catalyst is too cold', 'zh-CN': '题材热度不足', 'zh-TW': '題材熱度不足', ja: '材料熱量不足', ko: '재료 열기 부족' },
    strategyVetoNoReversalConfirm: { en: 'Reversal lacks confirmation', 'zh-CN': '反转确认不足', 'zh-TW': '反轉確認不足', ja: '反転確認不足', ko: '반전 확인 부족' },
    strategyVetoQuality: { en: 'Quality veto', 'zh-CN': '质量否决', 'zh-TW': '品質否決', ja: '品質除外', ko: '품질 차단' },
    strategyVetoRisk: { en: 'Risk veto', 'zh-CN': '风险否决', 'zh-TW': '風險否決', ja: 'リスク除外', ko: '리스크 차단' },
    strategyVetoShortTermFail: { en: 'Short-term model failed', 'zh-CN': '短线模型失败', 'zh-TW': '短線模型失敗', ja: '短期モデル失敗', ko: '단기 모델 실패' },
    strategyVetoMidLongWeak: { en: 'Mid/long quality is too weak', 'zh-CN': '中长线优质分过弱', 'zh-TW': '中長線優質分過弱', ja: '中長期品質が弱すぎます', ko: '중장기 품질이 너무 약함' }
  };
  return labels[key] ? localeText(labels[key]) : key;
}

function strategyFocusLabel(item: StrategyFocusResult) {
  const labels: Record<string, LocalizedText> = {
    strategyFocusTodayEntry: { en: 'Whether it is worth buying today', 'zh-CN': '今天是否真的值得买', 'zh-TW': '今天是否真的值得買', ja: '本日買う価値', ko: '오늘 매수 가치' },
    strategyFocusFutureExit: { en: 'Whether later profit-taking is realistic', 'zh-CN': '之后能否盈利卖出', 'zh-TW': '之後能否盈利賣出', ja: '後日の利益確定余地', ko: '이후 수익 매도 가능성' },
    strategyFocusRiskControl: { en: 'Downside control first', 'zh-CN': '优先控制下跌风险', 'zh-TW': '優先控制下跌風險', ja: '下落リスク優先', ko: '하방 리스크 우선' },
    strategyFocusBreakoutVolume: { en: 'Breakout needs volume confirmation', 'zh-CN': '突破必须看量能确认', 'zh-TW': '突破必須看量能確認', ja: 'ブレイクは出来高確認', ko: '돌파는 거래량 확인' },
    strategyFocusNoChase: { en: 'Avoid chasing after overextension', 'zh-CN': '避免过热追高', 'zh-TW': '避免過熱追高', ja: '過熱追随を避ける', ko: '과열 추격 회피' },
    strategyFocusNextSession: { en: 'Next-session continuation', 'zh-CN': '次日延续能力', 'zh-TW': '次日延續能力', ja: '翌日継続力', ko: '다음 세션 지속력' },
    strategyFocusReversalRisk: { en: 'Reversal risk', 'zh-CN': '反转风险', 'zh-TW': '反轉風險', ja: '反転リスク', ko: '반전 리스크' },
    strategyFocusTrendStructure: { en: 'Trend and MA structure', 'zh-CN': '趋势与均线结构', 'zh-TW': '趨勢與均線結構', ja: 'トレンドと移動平均', ko: '추세와 이동평균' },
    strategyFocusTExit: { en: 'T / high-sell window', 'zh-CN': '做T/高抛窗口', 'zh-TW': '做T/高拋窗口', ja: 'T/高値売り窓', ko: 'T/고가 매도 구간' },
    strategyFocusLiquidity: { en: 'Liquidity and tradability', 'zh-CN': '流动性与可交易性', 'zh-TW': '流動性與可交易性', ja: '流動性と取引性', ko: '유동성과 거래성' },
    strategyFocusNewsFlow: { en: 'Fresh news catalyst', 'zh-CN': '新鲜题材热度', 'zh-TW': '新鮮題材熱度', ja: '新しい材料熱量', ko: '신선한 재료 열기' },
    strategyFocusFundFlow: { en: 'Fund flow confirmation', 'zh-CN': '资金流确认', 'zh-TW': '資金流確認', ja: '資金フロー確認', ko: '자금 흐름 확인' },
    strategyFocusShortTerm: { en: 'Short-term tradability', 'zh-CN': '短线可交易性', 'zh-TW': '短線可交易性', ja: '短期取引適性', ko: '단기 거래 적합성' },
    strategyFocusMidLongTerm: { en: 'Mid/long quality fit', 'zh-CN': '中长线优质适配', 'zh-TW': '中長線優質適配', ja: '中長期品質適合', ko: '중장기 품질 적합' },
    strategyFocusStableQuality: { en: 'Stable quality candidate', 'zh-CN': '稳定优质候选', 'zh-TW': '穩定優質候選', ja: '安定品質候補', ko: '안정 품질 후보' },
    strategyFocusPullbackSupport: { en: 'Controlled pullback near support', 'zh-CN': '靠近支撑的受控回踩', 'zh-TW': '靠近支撐的受控回踩', ja: '支持近辺の制御された押し目', ko: '지지 근처의 통제된 눌림' },
    strategyFocusRsiMacd: { en: 'RSI and MACD confirmation', 'zh-CN': 'RSI 与 MACD 共振', 'zh-TW': 'RSI 與 MACD 共振', ja: 'RSI と MACD 確認', ko: 'RSI와 MACD 확인' },
    strategyFocusConfirmBeforeBuy: { en: 'Confirm before buying', 'zh-CN': '确认后再买', 'zh-TW': '確認後再買', ja: '確認後に買う', ko: '확인 후 매수' },
    strategyFocusQualityValue: { en: 'Quality and valuation first', 'zh-CN': '质量与估值优先', 'zh-TW': '品質與估值優先', ja: '品質と評価優先', ko: '품질과 밸류 우선' },
    strategyFocusFinancialRepair: { en: 'Financial repair or support', 'zh-CN': '财务修复或支撑', 'zh-TW': '財務修復或支撐', ja: '財務改善または支え', ko: '재무 개선 또는 지지' }
  };
  return `${labels[item.key] ? localeText(labels[item.key]) : item.key} · ${strategyMetricLabel(item.metric)} ${Number(item.score).toFixed(1)}/100`;
}

function strategyCheckLabel(check: StrategyCheckResult, type: 'gate' | 'veto') {
  const actual = Number(check.actual).toFixed(1);
  const threshold = Number(check.threshold).toFixed(1);
  const operator = check.operator === 'min' ? '>=' : check.operator === 'max' ? '<=' : check.operator === 'lte' ? '<=' : '>=';
  const status = type === 'gate'
    ? check.passed ? strategyUi.value.passed : strategyUi.value.failed
    : check.triggered ? strategyUi.value.triggered : strategyUi.value.clear;
  return `${strategyRuleTitle(check.key)} · ${strategyMetricLabel(check.metric)} ${actual} ${operator} ${threshold} · ${status}`;
}

function strategyRecommendationLabel(pick: Pick) {
  const recommendation = pick.strategyAssessment?.recommendation;
  if (recommendation === 'aligned') return strategyUi.value.modelAligned;
  if (recommendation === 'watch') return strategyUi.value.modelWatch;
  if (recommendation === 'avoid') return strategyUi.value.modelAvoid;
  if (recommendation === 'blocked') return strategyUi.value.modelBlocked;
  return recommendation || strategyUi.value.modelWatch;
}

function strategyHorizonLabel(classification: string | undefined) {
  const labels: Record<string, LocalizedText> = {
    stableQuality: { en: 'Stable quality', 'zh-CN': '稳定优质', 'zh-TW': '穩定優質', ja: '安定品質', ko: '안정 품질' },
    shortTermOnly: { en: 'Short-term only', 'zh-CN': '偏短线机会', 'zh-TW': '偏短線機會', ja: '短期寄り', ko: '단기 기회' },
    midLongQuality: { en: 'Mid/long quality', 'zh-CN': '中长线优质', 'zh-TW': '中長線優質', ja: '中長期品質', ko: '중장기 품질' },
    unstable: { en: 'Unstable', 'zh-CN': '不稳定', 'zh-TW': '不穩定', ja: '不安定', ko: '불안정' },
    balanced: { en: 'Balanced', 'zh-CN': '均衡', 'zh-TW': '均衡', ja: 'バランス型', ko: '균형' }
  };
  return labels[classification || ''] ? localeText(labels[classification || '']) : classification || '-';
}

function uniquePointLabels(points: Array<DecisionPoint | undefined>, limit = 5) {
  const seen = new Set<string>();
  const labels: string[] = [];
  points.forEach((point) => {
    if (!point) return;
    const label = pointLabel(point);
    if (!label || seen.has(label)) return;
    seen.add(label);
    labels.push(label);
  });
  return labels.slice(0, limit);
}

function reportSupportItems(pick: Pick) {
  return uniquePointLabels([
    ...(pick.overallAssessment?.positives ?? []),
    ...(pick.decision?.positives ?? []),
    ...(pick.trendAnalysis?.positives ?? []),
    ...(pick.newsHeatAnalysis?.positives ?? []),
    ...(pick.financialAnalysis?.positives ?? []),
    ...(pick.tPlan?.reasons ?? [])
  ]);
}

function reportRiskItems(pick: Pick) {
  return uniquePointLabels([
    ...(pick.overallAssessment?.negatives ?? []),
    ...(pick.decision?.negatives ?? []),
    ...(pick.trendAnalysis?.negatives ?? []),
    ...(pick.newsHeatAnalysis?.negatives ?? []),
    ...(pick.financialAnalysis?.negatives ?? []),
    ...(pick.tPlan?.riskControls ?? []),
    ...(pick.actionPlan?.riskControls ?? [])
  ]);
}

function reportWatchItems(pick: Pick) {
  return uniquePointLabels([
    ...(pick.overallAssessment?.watchItems ?? []),
    ...(pick.decision?.watchItems ?? []),
    ...(pick.trendAnalysis?.watchItems ?? []),
    ...(pick.newsHeatAnalysis?.watchItems ?? []),
    ...(pick.financialAnalysis?.watchItems ?? []),
    ...(pick.actionPlan?.watchItems ?? [])
  ]);
}

function reportSummaryTitle(pick: Pick) {
  if (pick.decisionEngine) {
    return `${decisionRegimeLabel(pick.decisionEngine.regime.name)} · ${finalVerdictLabel(pick)}`;
  }
  const summary = pick.overallAssessment?.summary ?? pick.decision?.summary ?? pick.actionPlan?.summary;
  return summary ? pointLabel(summary) : finalVerdictLabel(pick);
}

function reportSummarySubtitle(pick: Pick) {
  return uniquePointLabels([
    pick.actionPlan?.summary,
    pick.trendAnalysis?.summary,
    pick.newsHeatAnalysis?.summary,
    pick.financialAnalysis?.summary
  ], 3).join(' · ');
}

function reportMetricItems(pick: Pick) {
  if (pick.decisionEngine) {
    return [
      { key: 'decisionRank', label: resultSortLabel('decision'), value: `${formatEngineScore(pick.decisionEngine.rankScore)}/100`, score: pick.decisionEngine.rankScore },
      { key: 'buyScore', label: decisionActionLabel('accumulate'), value: `${formatEngineScore(pick.decisionEngine.buyScore)}/100`, score: pick.decisionEngine.buyScore },
      { key: 'sellScore', label: decisionActionLabel('reduce'), value: `${formatEngineScore(pick.decisionEngine.sellScore)}/100`, score: pick.decisionEngine.sellScore },
      { key: 'dataQuality', label: dataQualityLabel(pick.decisionEngine.dataQuality.level), value: `${formatEngineScore(pick.decisionEngine.dataQuality.score)}/100`, score: pick.decisionEngine.dataQuality.score }
    ];
  }
  const metrics = pick.overallAssessment?.metrics?.slice(0, 5).map((metric) => ({
    key: metric.key,
    label: overallMetricLabel(metric),
    value: metric.value,
    score: metric.score
  })) ?? [];
  if (metrics.length) return metrics;
  return [
    { key: 'score', label: t.value.score, value: `${pick.score}/100`, score: pick.score },
    { key: 'confidence', label: t.value.confidence, value: `${pick.confidence}%`, score: pick.confidence }
  ];
}

function primaryScoreCaption(pick: Pick) {
  if (pick.decisionEngine) {
    if (locale.value === 'en') return 'Decision';
    if (locale.value === 'zh-CN') return '决策分';
    if (locale.value === 'ja') return '判断点';
    if (locale.value === 'ko') return '판단점수';
    return '決策分';
  }
  if (!pick.overallAssessment) return t.value.score;
  if (locale.value === 'en') return 'Final';
  if (locale.value === 'zh-CN') return '最终分';
  if (locale.value === 'ja') return '最終点';
  if (locale.value === 'ko') return '최종점';
  return '最終分';
}

function fundFlowTone(flow: FundFlowProfile | null | undefined) {
  const positive = Number(flow?.positiveScore ?? 0);
  const negative = Number(flow?.negativeScore ?? 0);
  if (positive >= 18 && positive >= negative) return 'support';
  if (negative >= 18 && negative > positive) return 'pressure';
  return 'watch';
}

function fundFlowDecisionPoint(flow: FundFlowProfile | null | undefined, currency: string): DecisionPoint {
  const params = {
    score: Number(flow?.score ?? 0).toFixed(1),
    amount: signedMoneyLabel(flow?.mainNet, currency),
    ratio: Number(flow?.mainRatio ?? 0).toFixed(1),
    source: flow?.source || 'Eastmoney'
  };
  const tone = fundFlowTone(flow);
  if (tone === 'support') return { key: 'fundFlowSupport', params };
  if (tone === 'pressure') return { key: 'fundFlowPressure', params };
  return { key: 'fundFlowWatch', params };
}

function fundFlowMetricValue(amount: number | null | undefined, ratio: number | null | undefined, currency: string) {
  return `${signedMoneyLabel(amount, currency)} · ${percentLabel(ratio)}`;
}

function fundFlowUnavailableLabel(pick: Pick) {
  if (locale.value === 'en') return `Online fund flow did not return for ${pick.symbol}; this scan does not fabricate local flow data.`;
  if (locale.value === 'zh-CN') return `${pick.symbol} 在线资金流暂未返回；本次不会用本地或伪造资金流。`;
  if (locale.value === 'ja') return `${pick.symbol} のオンライン資金フローは未返却です。ローカル値や推測値は使いません。`;
  if (locale.value === 'ko') return `${pick.symbol} 온라인 자금 흐름이 반환되지 않았습니다. 로컬 또는 추정 데이터는 쓰지 않습니다.`;
  return `${pick.symbol} 線上資金流暫未返回；本次不會用本地或偽造資金流。`;
}

function fundFlowChipLabel(pick: Pick) {
  if (!pick.fundFlow?.available) {
    if (locale.value === 'en') return 'Fund flow unavailable';
    if (locale.value === 'zh-CN') return '资金流：在线未返回';
    if (locale.value === 'ja') return '資金フロー未返却';
    if (locale.value === 'ko') return '자금 흐름 미반환';
    return '資金流：線上未返回';
  }
  return `${factorLabel('fundFlow')} ${fundFlowMetricValue(pick.fundFlow.mainNet, pick.fundFlow.mainRatio, pick.currency)}`;
}

function fundFlowRows(pick: Pick) {
  const flow = pick.fundFlow;
  if (!flow?.available) return [];
  const rows = [
    {
      key: 'fundFlowMain',
      label: financialMetricLabel({ key: 'fundFlowMain', value: '', score: flow.score }),
      value: fundFlowMetricValue(flow.mainNet, flow.mainRatio, pick.currency),
      score: Number(flow.score ?? 0).toFixed(1)
    }
  ];
  if (flow.superLargeNet !== undefined || flow.superLargeRatio !== undefined) {
    rows.push({
      key: 'fundFlowSuperLarge',
      label: financialMetricLabel({ key: 'fundFlowSuperLarge', value: '', score: flow.score }),
      value: fundFlowMetricValue(flow.superLargeNet, flow.superLargeRatio, pick.currency),
      score: Number(50 + Number(flow.superLargeRatio ?? 0) * 2.6).toFixed(1)
    });
  }
  if (flow.largeNet !== undefined || flow.largeRatio !== undefined) {
    rows.push({
      key: 'fundFlowLarge',
      label: financialMetricLabel({ key: 'fundFlowLarge', value: '', score: flow.score }),
      value: fundFlowMetricValue(flow.largeNet, flow.largeRatio, pick.currency),
      score: Number(50 + Number(flow.largeRatio ?? 0) * 2.3).toFixed(1)
    });
  }
  return rows;
}

function predictionScoreLabel(kind: 'opportunity' | 'downside' | 'setup' | 'pullback' | 'continuation' | 'reversal' | 't', pick: Pick) {
  const value = kind === 'opportunity'
    ? pick.opportunityScore
    : kind === 'downside'
      ? pick.downsideRiskScore
      : kind === 'setup'
        ? pick.breakoutSetupScore
        : kind === 'continuation'
          ? pick.nextSessionContinuationScore ?? pick.trendAnalysis?.continuationScore
          : kind === 'reversal'
            ? pick.nextSessionReversalRiskScore ?? pick.trendAnalysis?.reversalRiskScore
            : kind === 't'
              ? pick.tScore
              : pick.pullbackRiskScore;
  const score = value === undefined ? '-' : Number(value).toFixed(1);
  if (kind === 't') {
    if (locale.value === 'en') return `T suitability ${score}/100`;
    if (locale.value === 'zh-CN') return `做T适配 ${score}/100`;
    if (locale.value === 'ja') return `T適性 ${score}/100`;
    if (locale.value === 'ko') return `T 적합도 ${score}/100`;
    if (locale.value === 'nan-TW') return `做T適配 ${score}/100`;
    return `做T適配 ${score}/100`;
  }
  if (kind === 'opportunity') {
    if (locale.value === 'en') return `Advantage ${score}/100`;
    if (locale.value === 'zh-CN') return `相对优势 ${score}/100`;
    if (locale.value === 'ja') return `相対優位 ${score}/100`;
    if (locale.value === 'ko') return `상대 우위 ${score}/100`;
    if (locale.value === 'nan-TW') return `相對優勢 ${score}/100`;
    return `相對優勢 ${score}/100`;
  }
  if (kind === 'setup') {
    if (locale.value === 'en') return `Breakout setup ${score}/100`;
    if (locale.value === 'zh-CN') return `突破 setup ${score}/100`;
    if (locale.value === 'ja') return `ブレイクアウト設定 ${score}/100`;
    if (locale.value === 'ko') return `돌파 설정 ${score}/100`;
    if (locale.value === 'nan-TW') return `突破 setup ${score}/100`;
    return `突破 setup ${score}/100`;
  }
  if (kind === 'pullback') {
    if (locale.value === 'en') return `Pullback risk ${score}/100`;
    if (locale.value === 'zh-CN') return `回落风险 ${score}/100`;
    if (locale.value === 'ja') return `反落リスク ${score}/100`;
    if (locale.value === 'ko') return `되돌림 리스크 ${score}/100`;
    if (locale.value === 'nan-TW') return `回落風險 ${score}/100`;
    return `回落風險 ${score}/100`;
  }
  if (kind === 'continuation') {
    if (locale.value === 'en') return `Next-session continuation ${score}/100`;
    if (locale.value === 'zh-CN') return `次日延续 ${score}/100`;
    if (locale.value === 'ja') return `翌日継続 ${score}/100`;
    if (locale.value === 'ko') return `다음 세션 지속 ${score}/100`;
    if (locale.value === 'nan-TW') return `隔日延續 ${score}/100`;
    return `次日延續 ${score}/100`;
  }
  if (kind === 'reversal') {
    if (locale.value === 'en') return `Next-session reversal risk ${score}/100`;
    if (locale.value === 'zh-CN') return `次日反转风险 ${score}/100`;
    if (locale.value === 'ja') return `翌日反転リスク ${score}/100`;
    if (locale.value === 'ko') return `다음 세션 반전 리스크 ${score}/100`;
    if (locale.value === 'nan-TW') return `隔日反轉風險 ${score}/100`;
    return `次日反轉風險 ${score}/100`;
  }
  if (locale.value === 'en') return `Downside risk ${score}/100`;
  if (locale.value === 'zh-CN') return `下跌风险 ${score}/100`;
  if (locale.value === 'ja') return `下落リスク ${score}/100`;
  if (locale.value === 'ko') return `하락 리스크 ${score}/100`;
  if (locale.value === 'nan-TW') return `下跌風險 ${score}/100`;
  return `下跌風險 ${score}/100`;
}

function tSuitabilityLabel(pick: Pick) {
  const suitability = pick.tPlan?.suitability;
  if (suitability === 'candidate') {
    if (locale.value === 'en') return 'T-ready';
    if (locale.value === 'zh-CN') return '适合做T';
    if (locale.value === 'ja') return 'T向き';
    if (locale.value === 'ko') return 'T 적합';
    if (locale.value === 'nan-TW') return '適合做T';
    return '適合做T';
  }
  if (suitability === 'watch') {
    if (locale.value === 'en') return 'T watch';
    if (locale.value === 'zh-CN') return '等确认';
    if (locale.value === 'ja') return '確認待ち';
    if (locale.value === 'ko') return '확인 대기';
    if (locale.value === 'nan-TW') return '等確認';
    return '等確認';
  }
  if (locale.value === 'en') return 'Avoid T';
  if (locale.value === 'zh-CN') return '不适合做T';
  if (locale.value === 'ja') return 'T回避';
  if (locale.value === 'ko') return 'T 회피';
  if (locale.value === 'nan-TW') return '毋適合做T';
  return '不適合做T';
}

function priceZoneLabel(pick: Pick, zone?: { low: number; high: number }) {
  if (!zone) return '-';
  return `${pick.currency} ${zone.low} - ${zone.high}`;
}

function tPlanFieldLabel(key: 'entry' | 'takeProfit' | 'stop' | 'basis' | 'riskControls') {
  const labels: Record<'entry' | 'takeProfit' | 'stop' | 'basis' | 'riskControls', LocalizedText> = {
    entry: { en: 'Low-buy zone', 'zh-CN': '低吸区', 'zh-TW': '低吸區', ja: '押し目買いゾーン', ko: '저가 매수 구간' },
    takeProfit: { en: 'High-sell zone', 'zh-CN': '高抛区', 'zh-TW': '高拋區', ja: '高値売りゾーン', ko: '고가 매도 구간' },
    stop: { en: 'Stop line', 'zh-CN': '止损线', 'zh-TW': '停損線', ja: '損切りライン', ko: '손절 기준선' },
    basis: { en: 'Why it can T', 'zh-CN': '做T依据', 'zh-TW': '做T依據', ja: 'T取引の根拠', ko: 'T 매매 근거' },
    riskControls: { en: 'T risk control', 'zh-CN': '做T风控', 'zh-TW': '做T風控', ja: 'T取引のリスク管理', ko: 'T 매매 리스크 관리' }
  };
  return labels[key][locale.value as StandardLocale] ?? labels[key].en;
}

function reasonLabel(reason: ReasonCode) {
  const params = reason.params;
  if (reason.key === 'strongestFactors') {
    if (locale.value === 'en') return `${factorLabel(params.first)} and ${factorLabel(params.second)} are the strongest factors.`;
    if (locale.value === 'zh-CN') return `${factorLabel(params.first)} 与 ${factorLabel(params.second)} 是最强的评分因子。`;
    if (locale.value === 'ja') return `${factorLabel(params.first)} と ${factorLabel(params.second)} が最も強い評価因子です。`;
    if (locale.value === 'ko') return `${factorLabel(params.first)}와 ${factorLabel(params.second)}가 가장 강한 평가 요인입니다.`;
    if (locale.value === 'nan-TW') return `${factorLabel(params.first)} 佮 ${factorLabel(params.second)} 是較強的評分因子。`;
    return `${factorLabel(params.first)} 與 ${factorLabel(params.second)} 是最強的評分因子。`;
  }
  if (reason.key === 'sentimentImpact') {
    const delta = Number(params.delta).toFixed(1);
    if (locale.value === 'en') return `Live crawled sentiment changes the score by ${Number(params.delta) >= 0 ? '+' : ''}${delta} points.`;
    if (locale.value === 'zh-CN') return `实时爬文情绪让评分变化 ${Number(params.delta) >= 0 ? '+' : ''}${delta} 分。`;
    if (locale.value === 'ja') return `リアルタイム取得ニュースの心理でスコアが ${Number(params.delta) >= 0 ? '+' : ''}${delta} 点変化しました。`;
    if (locale.value === 'ko') return `실시간 수집 뉴스 심리로 점수가 ${Number(params.delta) >= 0 ? '+' : ''}${delta}점 변했습니다.`;
    if (locale.value === 'nan-TW') return `即時爬文的新聞氣口，予評分變化 ${Number(params.delta) >= 0 ? '+' : ''}${delta} 分。`;
    return `即時爬文情緒讓評分變化 ${Number(params.delta) >= 0 ? '+' : ''}${delta} 分。`;
  }
  if (reason.key === 'belowThreshold') {
    if (locale.value === 'en') return `${factorLabel(params.factor)} is below threshold and should be monitored before adding exposure.`;
    if (locale.value === 'zh-CN') return `${factorLabel(params.factor)} 低于门槛，加仓前需要继续观察。`;
    if (locale.value === 'ja') return `${factorLabel(params.factor)} が基準未満です。追加投資前に確認が必要です。`;
    if (locale.value === 'ko') return `${factorLabel(params.factor)}가 기준을 밑돌아 비중 확대 전 관찰이 필요합니다.`;
    if (locale.value === 'nan-TW') return `${factorLabel(params.factor)} 低於門檻，加碼前愛閣觀察。`;
    return `${factorLabel(params.factor)} 低於門檻，加碼前需要繼續觀察。`;
  }
  if (reason.key === 'severePriceDrop') {
    if (locale.value === 'en') return `Price action is disqualified for new buying after a ${params.change}% drop.`;
    if (locale.value === 'zh-CN') return `当日跌幅 ${params.change}%，大跌/跌停状态不允许判为优质买入。`;
    if (locale.value === 'ja') return `当日 ${params.change}% 下落しており、急落中の新規買い候補から除外します。`;
    if (locale.value === 'ko') return `당일 ${params.change}% 하락해 급락 중 신규 매수 후보로 보지 않습니다.`;
    if (locale.value === 'nan-TW') return `當日跌幅 ${params.change}%，大跌狀態袂當判做會使買入。`;
    return `當日跌幅 ${params.change}%，大跌/跌停狀態不允許判為優質買入。`;
  }
  if (reason.key === 'weakPriceAction') {
    if (locale.value === 'en') return `Price action is weak after a ${params.change}% drop; wait for stabilization.`;
    if (locale.value === 'zh-CN') return `当日跌幅 ${params.change}%，价格未企稳前只能观察。`;
    if (locale.value === 'ja') return `当日 ${params.change}% 下落しており、価格が落ち着くまで注視します。`;
    if (locale.value === 'ko') return `당일 ${params.change}% 하락해 가격 안정 전에는 관찰이 우선입니다.`;
    if (locale.value === 'nan-TW') return `當日跌幅 ${params.change}%，價格未徛穩前先觀察。`;
    return `當日跌幅 ${params.change}%，價格未企穩前只能觀察。`;
  }
  if (reason.key === 'overheatedPriceAction') {
    if (locale.value === 'en') return `Price is already up ${params.change}%, with pullback risk at ${params.risk}/100; new buying is blocked.`;
    if (locale.value === 'zh-CN') return `股价已上涨 ${params.change}%，回落风险 ${params.risk}/100，不把涨停后追高判为买入。`;
    if (locale.value === 'ja') return `株価はすでに ${params.change}% 上昇、反落リスクは ${params.risk}/100 のため新規買いを抑制します。`;
    if (locale.value === 'ko') return `이미 ${params.change}% 상승했고 되돌림 리스크가 ${params.risk}/100이므로 신규 추격 매수로 보지 않습니다.`;
    if (locale.value === 'nan-TW') return `股價已經漲 ${params.change}%，回落風險 ${params.risk}/100，毋當做追高買入。`;
    return `股價已上漲 ${params.change}%，回落風險 ${params.risk}/100，不把漲停後追高判為買入。`;
  }
  if (reason.key === 'pullbackRisk') {
    if (locale.value === 'en') return `Pullback risk is elevated at ${params.risk}/100; wait for follow-through or a controlled reset.`;
    if (locale.value === 'zh-CN') return `回落风险偏高（${params.risk}/100），等待承接确认或有控制的回踩。`;
    if (locale.value === 'ja') return `反落リスクが ${params.risk}/100 と高めです。追随買いより確認を待ちます。`;
    if (locale.value === 'ko') return `되돌림 리스크가 ${params.risk}/100으로 높아 후속 확인을 기다립니다.`;
    if (locale.value === 'nan-TW') return `回落風險偏懸（${params.risk}/100），等承接確認抑是有控制的回踩。`;
    return `回落風險偏高（${params.risk}/100），等待承接確認或有控制的回踩。`;
  }
  if (reason.key === 'breakoutSetup') {
    if (locale.value === 'en') return `Early breakout setup scores ${params.score}/100 from price and volume confirmation.`;
    if (locale.value === 'zh-CN') return `早期突破 setup ${params.score}/100，来自价格与成交量确认。`;
    if (locale.value === 'ja') return `初期ブレイクアウト設定は ${params.score}/100、価格と出来高の確認に基づきます。`;
    if (locale.value === 'ko') return `초기 돌파 setup은 ${params.score}/100으로 가격과 거래량 확인이 있습니다.`;
    if (locale.value === 'nan-TW') return `早期突破 setup ${params.score}/100，有價格佮成交量確認。`;
    return `早期突破 setup ${params.score}/100，來自價格與成交量確認。`;
  }
  if (reason.key === 'nextSessionSupport') {
    if (locale.value === 'en') return `Next-session continuation is ${params.continuation}/100 while reversal risk is ${params.risk}/100.`;
    if (locale.value === 'zh-CN') return `次日延续分 ${params.continuation}/100，反转风险 ${params.risk}/100。`;
    if (locale.value === 'ja') return `翌日継続性は ${params.continuation}/100、反転リスクは ${params.risk}/100 です。`;
    if (locale.value === 'ko') return `다음 세션 지속성은 ${params.continuation}/100, 반전 리스크는 ${params.risk}/100입니다.`;
    if (locale.value === 'nan-TW') return `隔日延續分 ${params.continuation}/100，反轉風險 ${params.risk}/100。`;
    return `次日延續分 ${params.continuation}/100，反轉風險 ${params.risk}/100。`;
  }
  if (reason.key === 'nextSessionRisk') {
    if (locale.value === 'en') return `Today's edge may not carry forward: continuation ${params.continuation}/100, reversal risk ${params.risk}/100.`;
    if (locale.value === 'zh-CN') return `今天的优势可能无法延续：次日延续 ${params.continuation}/100，反转风险 ${params.risk}/100。`;
    if (locale.value === 'ja') return `今日の優位性は続かない可能性があります。継続性 ${params.continuation}/100、反転リスク ${params.risk}/100。`;
    if (locale.value === 'ko') return `오늘의 우위가 이어지지 않을 수 있습니다. 지속성 ${params.continuation}/100, 반전 리스크 ${params.risk}/100.`;
    if (locale.value === 'nan-TW') return `今仔日的優勢可能袂延續：隔日延續 ${params.continuation}/100，反轉風險 ${params.risk}/100。`;
    return `今天的優勢可能無法延續：次日延續 ${params.continuation}/100，反轉風險 ${params.risk}/100。`;
  }
  if (reason.key === 'clearsBuyThreshold') {
    if (locale.value === 'en') return 'Composite score clears the buy threshold under the selected strategy.';
    if (locale.value === 'zh-CN') return '综合评分已通过当前策略的买入门槛。';
    if (locale.value === 'ja') return '総合スコアが選択戦略の買い基準を上回っています。';
    if (locale.value === 'ko') return '종합 점수가 선택 전략의 매수 기준을 넘었습니다.';
    if (locale.value === 'nan-TW') return '綜合評分已經過買入門檻，會使納入候選。';
    return '綜合評分已通過目前策略的買入門檻。';
  }
  if (reason.key === 'rankedTopOpportunity') {
    if (locale.value === 'en') return `Ranked #${params.rank} among buy candidates in this scan.`;
    if (locale.value === 'zh-CN') return `本次扫描在买入候选中排名第 ${params.rank}。`;
    if (locale.value === 'ja') return `今回の買い候補で第 ${params.rank} 位です。`;
    if (locale.value === 'ko') return `이번 매수 후보 중 ${params.rank}위입니다.`;
    if (locale.value === 'nan-TW') return `這擺掃描佇買入候選內排名第 ${params.rank}。`;
    return `本次掃描在買入候選中排名第 ${params.rank}。`;
  }
  if (locale.value === 'en') return 'Composite score is not strong enough for a high-conviction entry.';
  if (locale.value === 'zh-CN') return '综合评分暂不足以支持高信心进场。';
  if (locale.value === 'ja') return '総合スコアはまだ高い確信で入る水準ではありません。';
  if (locale.value === 'ko') return '종합 점수는 아직 높은 확신의 진입을 뒷받침하기에 부족합니다.';
  if (locale.value === 'nan-TW') return '綜合評分暫時無夠支持高信心進場。';
  return '綜合評分暫不足以支持高信心進場。';
}

function reasonLabels(pick: Pick) {
  return pick.reasonCodes?.length ? pick.reasonCodes.map(reasonLabel) : pick.reasons;
}

function signedScore(value: unknown) {
  const numeric = Number(value ?? 0);
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(1)}`;
}

function nanDecisionPointLabel(point: DecisionPoint, score: string, count: number, hours: number) {
  const p = point.params;
  const positiveScore = Number(p.positiveScore ?? 0).toFixed(1);
  const negativeScore = Number(p.negativeScore ?? 0).toFixed(1);
  const netScore = signedScore(p.netScore);
  const change = Number(p.change ?? 0).toFixed(1);
  const pullbackRisk = Number(p.risk ?? 0).toFixed(1);
  const range = Number(p.range ?? 0).toFixed(1);
  const amount = String(p.amount ?? 'N/A');
  const ratio = Number(p.ratio ?? 0).toFixed(1);
  const continuation = Number(p.continuation ?? 0).toFixed(1);
  const risk = Number(p.risk ?? 0).toFixed(1);
  const distance = Number(p.distance ?? 0).toFixed(1);
  const rsi = Number(p.rsi ?? 0).toFixed(1);
  const heat = Number(p.heat ?? 0).toFixed(1);
  const impact = Number(p.impact ?? 0).toFixed(1);
  const today = Number(p.today ?? 0).toFixed(1);
  const future = Number(p.future ?? 0).toFixed(1);
  const exit = Number(p.exit ?? 0).toFixed(1);
  switch (point.key) {
    case 'buySummary':
      return `會使買入：總分 ${p.score}/100，這个方案相對有力。`;
    case 'watchSummary':
      return `重點觀察：總分 ${p.score}/100，進場或離場確認猶未完整。`;
    case 'sellSummary':
      return `退出風險：總分 ${p.score}/100，目前風險報酬較弱。`;
    case 'newsSupport':
      return `新聞正面強度 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}，對判斷有支撐。`;
    case 'newsPressure':
      return `新聞負面強度 ${negativeScore}/100，高過正面 ${positiveScore}/100，淨分 ${netScore}，已有 ${count} 則相關訊號。`;
    case 'insufficientNews':
      return '近期新聞證據無夠，信心度愛收斂。';
    case 'freshNews':
      return `最新相關新聞約 ${hours} 小時前，時效性較好。`;
    case 'momentumSupport':
      return `價格動能 ${score}/100，有支撐。`;
    case 'weakMomentum':
      return `動能偏弱，只有 ${score}/100，價格未確認前毋通追高。`;
    case 'watchBreakout':
      return '觀察動能能否提升到 60/100 以上。';
    case 'breakoutSetup':
      return `早期突破 setup ${score}/100，已有價格佮成交量確認。`;
    case 'valuationSupport':
      return `估值分 ${score}/100，價格相對未明顯過貴。`;
    case 'expensiveValuation':
      return `估值偏貴，只有 ${score}/100，要注意利多兌現後回落。`;
    case 'watchValuation':
      return '觀察下一次財報或指引後，估值有無重新變合理。';
    case 'riskControlled':
      return `風險控制 ${score}/100，波動和 beta 目前可接受。`;
    case 'riskHigh':
      return `風險分偏低，只有 ${score}/100，下行保護較弱。`;
    case 'watchRisk':
      return '觀察波動率和回撤是否收斂。';
    case 'priceActionSevereDrop':
      return `當日跌幅 ${change}%，大跌狀態袂當判做會使買入。`;
    case 'priceActionWeak':
      return `當日跌幅 ${change}%，價格未徛穩前先觀察。`;
    case 'overheatedPriceAction':
      return `股價已經漲 ${change}%，有追高回落風險。`;
    case 'pullbackRisk':
      return `回落風險 ${pullbackRisk}/100，愛等承接確認抑是有控制的回踩。`;
    case 'qualitySupport':
      return `基本面品質 ${score}/100，對中期持有有支撐。`;
    case 'weakQuality':
      return `基本面品質偏弱，只有 ${score}/100。`;
    case 'watchNewsFlow':
      return `新聞正面 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}；繼續看後續新聞轉正抑是轉負。`;
    case 'fundFlowSupport':
      return `當日主力資金淨流入 ${amount}，佔比 ${ratio}%，資金面有支撐。`;
    case 'fundFlowPressure':
      return `當日主力資金淨流出 ${amount}，佔比 ${ratio}%，資金面偏壓抑。`;
    case 'fundFlowWatch':
      return `當日主力資金 ${amount}，佔比 ${ratio}%，資金面方向猶未明確。`;
    case 'newsHeatHotPositiveSummary':
      return `新聞熱度 ${heat}/100、影響 ${impact}/100，市場關注偏正面。`;
    case 'newsHeatHotNegativeSummary':
      return `新聞熱度 ${heat}/100、影響 ${impact}/100，市場關注偏負面。`;
    case 'newsHeatHotMixedSummary':
      return `新聞熱度 ${heat}/100，但是多空方向猶混合。`;
    case 'newsHeatColdSummary':
      return `新聞熱度 ${heat}/100，題材關注度有限。`;
    case 'newsHeatSupport':
      return `新聞熱度影響 ${impact}/100，對總評有加分。`;
    case 'newsHeatRisk':
      return `新聞熱度影響 ${impact}/100，熱門消息反而偏風險。`;
    case 'newsHeatWatch':
      return `新聞熱度影響 ${impact}/100，方向猶著觀察。`;
    case 'newsHeatFresh':
      return `新聞時效 ${score}/100，資料夠新。`;
    case 'newsHeatStale':
      return `新聞時效 ${score}/100，熱度資料較舊。`;
    case 'overallStrongBuySummary':
      return `最後總評 ${p.score}/100：今日可買、後續上漲佮盈利賣出條件攏較完整。`;
    case 'overallBuySummary':
      return `最後總評 ${p.score}/100：今日有買入價值，也有後續獲利空間。`;
    case 'overallWatchSummary':
      return `最後總評 ${p.score}/100：條件未完整，先列重點觀察。`;
    case 'overallAvoidSummary':
      return `最後總評 ${p.score}/100：今日不適合新買，等條件修復。`;
    case 'overallSellSummary':
      return `最後總評 ${p.score}/100：風險優先，偏向減倉或退出。`;
    case 'overallTodayBuySupport':
      return `今日買入分 ${today}/100，當下買點有支撐。`;
    case 'overallTodayBuyWeak':
      return `今日買入分 ${today}/100，這馬買入條件無夠。`;
    case 'overallTodayBuyWatch':
      return `今日買入分 ${today}/100，愛閣等確認。`;
    case 'overallFutureRiseSupport':
      return `後續上漲分 ${future}/100，延續機會較好。`;
    case 'overallFutureRiseWeak':
      return `後續上漲分 ${future}/100，後勢無明確優勢。`;
    case 'overallFutureRiseWatch':
      return `後續上漲分 ${future}/100，方向猶未定。`;
    case 'overallProfitableExitSupport':
      return `盈利賣出分 ${exit}/100，明日以後較有機會賣出獲利。`;
    case 'overallProfitableExitWeak':
      return `盈利賣出分 ${exit}/100，明日以後賣出獲利空間無清楚。`;
    case 'overallProfitableExitWatch':
      return `盈利賣出分 ${exit}/100，愛看量價有無延續。`;
    case 'overallNewsHeatSupport':
      return `新聞熱度影響 ${impact}/100，熱度方向對總評有幫助。`;
    case 'overallNewsHeatRisk':
      return `新聞熱度影響 ${impact}/100，熱度方向拖累總評。`;
    case 'overallNewsHeatWatch':
      return `新聞熱度影響 ${impact}/100，尚未形成明確加減分。`;
    case 'overallRiskTooHigh':
      return `下跌或反轉風險 ${risk}/100，總評需要降級。`;
    case 'trendBullishSummary':
      return `日線延續 ${continuation}/100，隔日反轉風險 ${risk}/100，趨勢有支撐。`;
    case 'trendConstructiveSummary':
      return `日線延續 ${continuation}/100，趨勢有條件，但是猶著等確認。`;
    case 'trendNeutralSummary':
      return `日線延續 ${continuation}/100，方向猶未明確。`;
    case 'trendRiskSummary':
      return `隔日反轉風險 ${risk}/100，今日優勢可能袂延續。`;
    case 'trendContinuationSupport':
      return `隔日延續分 ${continuation}/100、風險 ${risk}/100，短線較有機會接續。`;
    case 'trendContinuationWeak':
      return `隔日延續分 ${continuation}/100、風險 ${risk}/100，毋通共今日優勢當作明仔載也有效。`;
    case 'trendContinuationWatch':
      return `隔日延續分 ${continuation}/100，愛閣看明仔載量價確認。`;
    case 'trendStructureSupport':
      return `均線結構 ${score}/100，日線排列有支撐。`;
    case 'trendStructureWeak':
      return `均線結構 ${score}/100，趨勢排列偏弱。`;
    case 'trendRsiHealthy':
      return `RSI ${rsi}，動能無明顯過熱。`;
    case 'trendOverextended':
      return `RSI ${rsi}，短線過熱風險上升。`;
    case 'trendMacdSupport':
      return `MACD 動能 ${score}/100，短線有支持。`;
    case 'trendMacdPressure':
      return `MACD 動能 ${score}/100，短線轉弱。`;
    case 'trendVolumeConfirm':
      return `量能確認 ${score}/100，價格變動有成交量配合。`;
    case 'trendVolumeDivergence':
      return `量能確認 ${score}/100，價量配合無夠。`;
    case 'trendNearResistance':
      return `距離近壓力約 ${distance}%，需要突破確認。`;
    case 'trendNearSupport':
      return `距離近支撐約 ${distance}%，觀察有無守住。`;
    case 'newsBullishSummary':
      return `新聞淨偏多：正面強度 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}，來自 ${p.total} 則近期新聞。`;
    case 'newsBearishSummary':
      return `新聞淨偏空：負面強度 ${negativeScore}/100、正面 ${positiveScore}/100、淨分 ${netScore}。`;
    case 'newsMixedSummary':
      return `新聞多空混合：正面強度 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}。`;
    case 'newsNoEvidence':
      return '無找到可用的近期新聞證據。';
    case 'financialStrongSummary':
      return `財報 / 基本面檢查偏強，涵蓋 ${p.count} 個可用指標。`;
    case 'financialWeakSummary':
      return `財報 / 基本面檢查偏弱，涵蓋 ${p.count} 個可用指標。`;
    case 'financialMixedSummary':
      return `財報 / 基本面檢查多空混合，涵蓋 ${p.count} 個可用指標。`;
    case 'financialDataMissing':
      return '財報資料不足，需等待更完整的揭露或資料源。';
    case 'financialValuationReasonable':
      return `估值相對合理，PE 約 ${p.value}。`;
    case 'financialValuationRich':
      return `估值偏貴，PE 約 ${p.value}，毋通付太高價。`;
    case 'financialWatchValuation':
      return `估值中性，PE 約 ${p.value}；觀察獲利上修或價格回檔。`;
    case 'financialGrowthSupport':
      return `成長指標有支撐，評分 ${p.score}/100。`;
    case 'financialGrowthWeak':
      return `成長指標偏弱，評分 ${p.score}/100。`;
    case 'financialWatchNextReport':
      return '重點觀察下一份財報的營收佮 EPS 是否確認改善。';
    case 'financialProfitabilitySupport':
      return `獲利能力有支撐，評分 ${p.score}/100。`;
    case 'financialProfitabilityWeak':
      return `獲利能力偏弱，評分 ${p.score}/100。`;
    case 'financialDebtControlled':
      return `負債風險相對可控，評分 ${p.score}/100。`;
    case 'financialDebtRisk':
      return `負債壓力偏高，評分 ${p.score}/100。`;
    case 'financialLiquiditySupport':
      return `流動性佮市值規模代理指標有支撐，評分 ${p.score}/100。`;
    case 'financialLiquidityRisk':
      return `流動性佮市值規模代理指標偏弱，評分 ${p.score}/100。`;
    case 'financialAnalystUpside':
      return `分析師目標價隱含約 ${p.upside}% 上行空間，來自 ${p.count} 個意見。`;
    case 'financialAnalystDownside':
      return `分析師目標價隱含約 ${p.upside}% 下行空間。`;
    case 'financialDividendSupport':
      return `股息率約 ${p.yield}%，提供股東回報支撐。`;
    case 'financialWatchHighRange':
      return `價格位於 52 週區間較高位置 ${p.position}%，觀察回檔風險。`;
    case 'financialWatchLowRange':
      return `價格位於 52 週區間較低位置 ${p.position}%，觀察是否基本面惡化導致折價。`;
    case 'actionAccumulate':
      return `建議操作：總分維持 ${p.score}/100 時，可考慮分批佈局。`;
    case 'actionReduceOrExit':
      return `建議操作：除非總分從 ${p.score}/100 明顯修復，否則考慮降低倉位或退出。`;
    case 'actionWait':
      return `建議操作：等待確認，現在總分 ${p.score}/100。`;
    case 'actionBuyInBatches':
      return '用分批方式，毋通一次滿倉買入。';
    case 'actionWaitNewsConfirmation':
      return '加碼前等待下一則正面新聞或財報確認。';
    case 'actionUseSmallPosition':
      return `風險分只有 ${p.risk}/100，倉位應保持較小。`;
    case 'actionReduceExposure':
      return `研究評分只有 ${p.score}/100，應考慮降低風險暴露。`;
    case 'actionDoNotAverageDown':
      return '負面新聞事件占優時，不建議越跌越買攤平。';
    case 'actionSetExitReview':
      return '在下一次重大公告或財報後重新評估是否繼續持有。';
    case 'actionNoChase':
      return `毋通追高，目前信心度只有 ${p.score}/100。`;
    case 'actionWatchNewsCatalyst':
      return '觀察是否出現新催化：財報優於預期、指引上修、評級上調、回購或資金流入。';
    case 'actionWatchFinancialRepair':
      return `觀察 ${p.count} 個偏弱財務項是否開始修復。`;
    case 'actionWatchMomentumTurn':
      return '加碼前觀察價格動能是否轉強。';
    case 'actionRespectRisk':
      return `風險分 ${p.risk}/100，必須優先控制下行風險。`;
    case 'actionAvoidLimitDown':
      return `當日跌幅 ${change}%，避免接跌停或急跌中的股票。`;
    case 'actionWaitPriceStabilization':
      return `當日跌幅 ${change}%，等待價格企穩才重新評估。`;
    case 'actionWaitPullback':
      return `回落風險 ${pullbackRisk}/100，等回踩守穩抑是隔日承接確認。`;
    case 'actionRequireNewsEvidence':
      return '需要新的公司級新聞證據，才適合做高信心判斷。';
    case 'tCandidateSummary':
      return `適合做T：T 分 ${p.score}/100，有流動性佮可交易波動。`;
    case 'tWatchSummary':
      return `做T等待確認：T 分 ${p.score}/100，條件猶未完整。`;
    case 'tAvoidSummary':
      return `毋適合做T：T 分 ${p.score}/100，風險報酬無划算。`;
    case 'tLiquidityReady':
      return `流動性分 ${p.score}/100，較有機會順利進出。`;
    case 'tLiquidityThin':
      return `流動性分只有 ${p.score}/100，做T容易有滑價。`;
    case 'tVolatilityReady':
      return `預估可交易波動約 ${range}%，有做差價空間。`;
    case 'tVolatilityLow':
      return `預估波動約 ${range}%，差價空間偏小。`;
    case 'tSetupReady':
      return `短線 setup ${p.score}/100，價格佮成交量有配合。`;
    case 'tTrendWeak':
      return `動能只有 ${p.score}/100，先等轉強。`;
    case 'tPullbackRiskHigh':
      return `回落風險 ${p.risk}/100，毋通追高做T。`;
    case 'tDownsideRiskHigh':
      return `下跌風險 ${p.risk}/100，做T防守優先。`;
    case 'tNoChase':
      return `股價已經漲 ${p.change}%，做T只等回踩，毋追。`;
    case 'tUseBasePositionOnly':
      return '做T應以既有底倉為主，避免用全新倉位追價。';
    case 'tCutIfBreaksSupport':
      return '若跌破低吸區仍無承接，應先停損或降倉。';
    default:
      return point.key;
  }
}

function jaKoDecisionPointLabel(point: DecisionPoint, score: string, count: number, hours: number) {
  if (locale.value !== 'ja' && locale.value !== 'ko') return null;
  const p = point.params;
  const isJa = locale.value === 'ja';
  const positiveScore = Number(p.positiveScore ?? 0).toFixed(1);
  const negativeScore = Number(p.negativeScore ?? 0).toFixed(1);
  const netScore = signedScore(p.netScore);
  const change = Number(p.change ?? 0).toFixed(1);
  const pullbackRisk = Number(p.risk ?? 0).toFixed(1);
  const range = Number(p.range ?? 0).toFixed(1);
  const amount = String(p.amount ?? 'N/A');
  const ratio = Number(p.ratio ?? 0).toFixed(1);
  const continuation = Number(p.continuation ?? 0).toFixed(1);
  const risk = Number(p.risk ?? 0).toFixed(1);
  const distance = Number(p.distance ?? 0).toFixed(1);
  const rsi = Number(p.rsi ?? 0).toFixed(1);
  const heat = Number(p.heat ?? 0).toFixed(1);
  const impact = Number(p.impact ?? 0).toFixed(1);
  const today = Number(p.today ?? 0).toFixed(1);
  const future = Number(p.future ?? 0).toFixed(1);
  const exit = Number(p.exit ?? 0).toFixed(1);

  switch (point.key) {
    case 'buySummary':
      return isJa
        ? `買い候補：総合スコア ${p.score}/100。選択中のニュース重視戦略で相対優位があります。`
        : `매수 후보: 총점 ${p.score}/100, 선택한 뉴스 중심 전략에서 상대 우위가 있습니다.`;
    case 'watchSummary':
      return isJa
        ? `注視：総合スコア ${p.score}/100。エントリーまたは撤退の確認はまだ不十分です。`
        : `관찰: 총점 ${p.score}/100, 진입 또는 이탈 확인이 아직 충분하지 않습니다.`;
    case 'sellSummary':
      return isJa
        ? `売却リスク：総合スコア ${p.score}/100。この戦略ではリスク・リターンが弱めです。`
        : `매도 리스크: 총점 ${p.score}/100, 이 전략에서는 위험 대비 보상이 약합니다.`;
    case 'newsSupport':
      return isJa
        ? `ニュースは支援的です。ポジティブ ${positiveScore}/100、ネガティブ ${negativeScore}/100、ネット ${netScore}。`
        : `뉴스가 긍정적입니다. 긍정 강도 ${positiveScore}/100, 부정 ${negativeScore}/100, 순점수 ${netScore}.`;
    case 'newsPressure':
      return isJa
        ? `ニュースが判断を圧迫しています。ネガティブ ${negativeScore}/100、ポジティブ ${positiveScore}/100、ネット ${netScore}、関連シグナル ${count} 件。`
        : `뉴스가 판단을 압박합니다. 부정 강도 ${negativeScore}/100, 긍정 ${positiveScore}/100, 순점수 ${netScore}, 관련 신호 ${count}개.`;
    case 'insufficientNews':
      return isJa
        ? '直近ニュースの根拠が不足しているため、確信度は抑えるべきです。'
        : '최근 뉴스 근거가 부족하므로 확신도는 제한해야 합니다.';
    case 'freshNews':
      return isJa
        ? `最新の関連ニュースは約 ${hours} 時間前で、鮮度があります。`
        : `최신 관련 뉴스는 약 ${hours}시간 전으로 신선합니다.`;
    case 'momentumSupport':
      return isJa
        ? `価格モメンタムは ${score}/100 で支援的です。`
        : `가격 모멘텀은 ${score}/100으로 우호적입니다.`;
    case 'weakMomentum':
      return isJa
        ? `モメンタムは ${score}/100 と弱めです。価格確認前の追随買いは避けます。`
        : `모멘텀은 ${score}/100으로 약합니다. 가격 확인 전 추격 매수는 피합니다.`;
    case 'watchBreakout':
      return isJa
        ? 'モメンタムが 60/100 を上回れるか確認します。'
        : '모멘텀이 60/100 이상으로 개선되는지 확인합니다.';
    case 'breakoutSetup':
      return isJa
        ? `初期ブレイクアウト設定は ${score}/100。価格と出来高の確認があります。`
        : `초기 돌파 설정은 ${score}/100이며 가격과 거래량 확인이 있습니다.`;
    case 'valuationSupport':
      return isJa
        ? `バリュエーションスコアは ${score}/100 で、割高感は強くありません。`
        : `밸류에이션 점수는 ${score}/100으로, 가격 부담이 크지 않습니다.`;
    case 'expensiveValuation':
      return isJa
        ? `バリュエーションは ${score}/100 と伸び切っています。好材料織り込み後の反落に注意します。`
        : `밸류에이션은 ${score}/100으로 부담스럽습니다. 호재 반영 후 되돌림을 경계합니다.`;
    case 'watchValuation':
      return isJa
        ? '次回決算またはガイダンス後に、バリュエーションが妥当化するか確認します。'
        : '다음 실적 또는 가이던스 이후 밸류에이션이 합리화되는지 확인합니다.';
    case 'riskControlled':
      return isJa
        ? `リスクスコアは ${score}/100 で管理可能な範囲です。`
        : `리스크 점수는 ${score}/100으로 관리 가능한 범위입니다.`;
    case 'riskHigh':
      return isJa
        ? `リスクスコアは ${score}/100 と低く、下値保護が弱いです。`
        : `리스크 점수는 ${score}/100으로 낮아 하방 보호가 약합니다.`;
    case 'watchRisk':
      return isJa
        ? 'ボラティリティとドローダウンが安定するか確認します。'
        : '변동성과 낙폭이 안정되는지 확인합니다.';
    case 'priceActionSevereDrop':
      return isJa
        ? `本日 ${change}% 下落。急落状態のため、高品質な買い判断はブロックされます。`
        : `당일 ${change}% 하락. 급락 상태라 우량 매수 판단을 차단합니다.`;
    case 'priceActionWeak':
      return isJa
        ? `本日 ${change}% 下落。価格が安定するまでは注視に留めます。`
        : `당일 ${change}% 하락. 가격 안정 전에는 관찰이 우선입니다.`;
    case 'overheatedPriceAction':
      return isJa
        ? `株価はすでに ${change}% 上昇。新規買い設定ではなく追随リスクとして扱います。`
        : `주가는 이미 ${change}% 상승했습니다. 신규 매수 설정이 아니라 추격 리스크로 봅니다.`;
    case 'pullbackRisk':
      return isJa
        ? `反落リスクは ${pullbackRisk}/100。追随よりも継続確認または整理された押し目を待ちます。`
        : `되돌림 리스크는 ${pullbackRisk}/100입니다. 후속 확인 또는 통제된 눌림을 기다립니다.`;
    case 'qualitySupport':
      return isJa
        ? `品質スコアは ${score}/100 と強く、中期保有を支えます。`
        : `품질 점수는 ${score}/100으로 강해 중기 보유를 뒷받침합니다.`;
    case 'weakQuality':
      return isJa
        ? `品質スコアは ${score}/100 と弱めです。`
        : `품질 점수는 ${score}/100으로 약합니다.`;
    case 'watchNewsFlow':
      return isJa
        ? `ニュースはまだ混在しています。ポジティブ ${positiveScore}/100、ネガティブ ${negativeScore}/100、ネット ${netScore}。`
        : `뉴스 흐름은 아직 혼재되어 있습니다. 긍정 ${positiveScore}/100, 부정 ${negativeScore}/100, 순점수 ${netScore}.`;
    case 'fundFlowSupport':
      return isJa
        ? `当日主力資金は ${amount}、比率 ${ratio}% の純流入で、需給面を支えています。`
        : `당일 주력 자금은 ${amount}, 비중 ${ratio}% 순유입으로 수급을 지지합니다.`;
    case 'fundFlowPressure':
      return isJa
        ? `当日主力資金は ${amount}、比率 ${ratio}% の純流出で、需給面の圧力です。`
        : `당일 주력 자금은 ${amount}, 비중 ${ratio}% 순유출로 수급 압력입니다.`;
    case 'fundFlowWatch':
      return isJa
        ? `当日主力資金は ${amount}、比率 ${ratio}% で、方向感はまだ限定的です。`
        : `당일 주력 자금은 ${amount}, 비중 ${ratio}%로 방향성이 아직 제한적입니다.`;
    case 'newsHeatHotPositiveSummary':
      return isJa ? `ニュース注目度は ${heat}/100、影響は ${impact}/100 でポジティブです。` : `뉴스 관심도는 ${heat}/100, 영향은 ${impact}/100으로 긍정적입니다.`;
    case 'newsHeatHotNegativeSummary':
      return isJa ? `ニュース注目度は ${heat}/100、影響は ${impact}/100 でリスク寄りです。` : `뉴스 관심도는 ${heat}/100, 영향은 ${impact}/100으로 리스크 쪽입니다.`;
    case 'newsHeatHotMixedSummary':
      return isJa ? `ニュース注目度は ${heat}/100 ですが、強弱はまだ混在しています。` : `뉴스 관심도는 ${heat}/100이지만 방향성은 아직 혼재되어 있습니다.`;
    case 'newsHeatColdSummary':
      return isJa ? `ニュース注目度は ${heat}/100 で、材料の広がりは限定的です。` : `뉴스 관심도는 ${heat}/100으로 이슈 확산은 제한적입니다.`;
    case 'newsHeatSupport':
      return isJa ? `ニュース注目度の影響は ${impact}/100 で、総合評価を支えます。` : `뉴스 관심도 영향은 ${impact}/100으로 종합 평가를 지지합니다.`;
    case 'newsHeatRisk':
      return isJa ? `ニュース注目度の影響は ${impact}/100 で、人気材料がリスク要因です。` : `뉴스 관심도 영향은 ${impact}/100으로 인기 이슈가 리스크 요인입니다.`;
    case 'newsHeatWatch':
      return isJa ? `ニュース注目度の影響は ${impact}/100 で、方向確認が必要です。` : `뉴스 관심도 영향은 ${impact}/100으로 방향 확인이 필요합니다.`;
    case 'newsHeatFresh':
      return isJa ? `ニュース鮮度は ${score}/100 で、材料は新しいです。` : `뉴스 신선도는 ${score}/100으로 자료가 최신에 가깝습니다.`;
    case 'newsHeatStale':
      return isJa ? `ニュース鮮度は ${score}/100 で、材料が古くなっています。` : `뉴스 신선도는 ${score}/100으로 자료가 다소 오래되었습니다.`;
    case 'overallStrongBuySummary':
      return isJa
        ? `最終総合評価 ${p.score}/100。今日の買い、今後の上昇、利益確定条件がそろっています。`
        : `최종 종합 평가 ${p.score}/100. 오늘 매수, 향후 상승, 수익 실현 조건이 모두 비교적 갖춰졌습니다.`;
    case 'overallBuySummary':
      return isJa
        ? `最終総合評価 ${p.score}/100。今日の買い価値と今後の利益余地があります。`
        : `최종 종합 평가 ${p.score}/100. 오늘 매수 가치와 이후 수익 여지가 있습니다.`;
    case 'overallWatchSummary':
      return isJa ? `最終総合評価 ${p.score}/100。条件は未完成で注視です。` : `최종 종합 평가 ${p.score}/100. 조건이 아직 완전하지 않아 관찰입니다.`;
    case 'overallAvoidSummary':
      return isJa ? `最終総合評価 ${p.score}/100。今日の新規買いは避けます。` : `최종 종합 평가 ${p.score}/100. 오늘 신규 매수는 피합니다.`;
    case 'overallSellSummary':
      return isJa ? `最終総合評価 ${p.score}/100。リスク優先で縮小または撤退寄りです。` : `최종 종합 평가 ${p.score}/100. 리스크 우선으로 축소 또는 이탈 쪽입니다.`;
    case 'overallTodayBuySupport':
      return isJa ? `今日の買い評価は ${today}/100 で、現時点の買い場を支えます。` : `오늘 매수 평가는 ${today}/100으로 현재 매수 지점을 지지합니다.`;
    case 'overallTodayBuyWeak':
      return isJa ? `今日の買い評価は ${today}/100 で、買い条件が不足しています。` : `오늘 매수 평가는 ${today}/100으로 매수 조건이 부족합니다.`;
    case 'overallTodayBuyWatch':
      return isJa ? `今日の買い評価は ${today}/100 で、追加確認が必要です。` : `오늘 매수 평가는 ${today}/100으로 추가 확인이 필요합니다.`;
    case 'overallFutureRiseSupport':
      return isJa ? `今後の上昇評価は ${future}/100 で、継続余地があります。` : `향후 상승 평가는 ${future}/100으로 지속 여지가 있습니다.`;
    case 'overallFutureRiseWeak':
      return isJa ? `今後の上昇評価は ${future}/100 で、優位性は弱いです。` : `향후 상승 평가는 ${future}/100으로 우위가 약합니다.`;
    case 'overallFutureRiseWatch':
      return isJa ? `今後の上昇評価は ${future}/100 で、方向確認が必要です。` : `향후 상승 평가는 ${future}/100으로 방향 확인이 필요합니다.`;
    case 'overallProfitableExitSupport':
      return isJa ? `利益確定評価は ${exit}/100 で、明日以降に利益を出して売る余地があります。` : `수익 실현 평가는 ${exit}/100으로 내일 이후 수익 매도 여지가 있습니다.`;
    case 'overallProfitableExitWeak':
      return isJa ? `利益確定評価は ${exit}/100 で、明日以降の売却利益は不明瞭です。` : `수익 실현 평가는 ${exit}/100으로 내일 이후 수익 매도 여지가 불명확합니다.`;
    case 'overallProfitableExitWatch':
      return isJa ? `利益確定評価は ${exit}/100 で、次の出来高と価格確認が必要です。` : `수익 실현 평가는 ${exit}/100으로 다음 거래량과 가격 확인이 필요합니다.`;
    case 'overallNewsHeatSupport':
      return isJa ? `ニュース注目度の影響は ${impact}/100 で、総合評価を押し上げます。` : `뉴스 관심도 영향은 ${impact}/100으로 종합 평가를 끌어올립니다.`;
    case 'overallNewsHeatRisk':
      return isJa ? `ニュース注目度の影響は ${impact}/100 で、総合評価を押し下げます。` : `뉴스 관심도 영향은 ${impact}/100으로 종합 평가를 낮춥니다.`;
    case 'overallNewsHeatWatch':
      return isJa ? `ニュース注目度の影響は ${impact}/100 で、明確な加点・減点はまだありません。` : `뉴스 관심도 영향은 ${impact}/100으로 뚜렷한 가감점은 아직 없습니다.`;
    case 'overallRiskTooHigh':
      return isJa ? `下落または反転リスクは ${risk}/100 で、総合評価を下げます。` : `하락 또는 반전 리스크는 ${risk}/100으로 종합 평가를 낮춥니다.`;
    case 'trendBullishSummary':
      return isJa
        ? `日足の継続性は ${continuation}/100、翌日反転リスクは ${risk}/100 です。`
        : `일봉 지속성은 ${continuation}/100, 다음 세션 반전 리스크는 ${risk}/100입니다.`;
    case 'trendConstructiveSummary':
      return isJa
        ? `日足の継続性は ${continuation}/100 で、追加確認が必要です。`
        : `일봉 지속성은 ${continuation}/100이며 추가 확인이 필요합니다.`;
    case 'trendNeutralSummary':
      return isJa
        ? `日足の継続性は ${continuation}/100 で、方向感はまだ中立です。`
        : `일봉 지속성은 ${continuation}/100이며 방향성은 아직 중립입니다.`;
    case 'trendRiskSummary':
      return isJa
        ? `翌日反転リスクは ${risk}/100 で、今日の優位性が続かない可能性があります。`
        : `다음 세션 반전 리스크는 ${risk}/100이라 오늘의 우위가 이어지지 않을 수 있습니다.`;
    case 'trendContinuationSupport':
      return isJa
        ? `翌日継続性 ${continuation}/100、反転リスク ${risk}/100 で、短期継続を支えます。`
        : `다음 세션 지속성 ${continuation}/100, 반전 리스크 ${risk}/100으로 단기 지속을 지지합니다.`;
    case 'trendContinuationWeak':
      return isJa
        ? `翌日継続性 ${continuation}/100、反転リスク ${risk}/100 です。今日の優位性を翌日まで固定しません。`
        : `다음 세션 지속성 ${continuation}/100, 반전 리스크 ${risk}/100입니다. 오늘의 우위를 다음 세션까지 고정하지 않습니다.`;
    case 'trendContinuationWatch':
      return isJa
        ? `翌日継続性 ${continuation}/100 です。次の価格と出来高確認を待ちます。`
        : `다음 세션 지속성 ${continuation}/100입니다. 다음 가격과 거래량 확인이 필요합니다.`;
    case 'trendStructureSupport':
      return isJa
        ? `移動平均構造は ${score}/100 で、日足配列を支えています。`
        : `이동평균 구조는 ${score}/100이며 일봉 배열을 지지합니다.`;
    case 'trendStructureWeak':
      return isJa
        ? `移動平均構造は ${score}/100 で、トレンド配列は弱めです。`
        : `이동평균 구조는 ${score}/100이며 추세 배열이 약합니다.`;
    case 'trendRsiHealthy':
      return isJa ? `RSI は ${rsi} で、明確な過熱ではありません。` : `RSI는 ${rsi}로 뚜렷한 과열은 아닙니다.`;
    case 'trendOverextended':
      return isJa ? `RSI は ${rsi} で、短期過熱リスクが上がっています。` : `RSI는 ${rsi}로 단기 과열 리스크가 높아졌습니다.`;
    case 'trendMacdSupport':
      return isJa ? `MACD モメンタムは ${score}/100 で短期を支えます。` : `MACD 모멘텀은 ${score}/100으로 단기를 지지합니다.`;
    case 'trendMacdPressure':
      return isJa ? `MACD モメンタムは ${score}/100 で短期が弱まっています。` : `MACD 모멘텀은 ${score}/100으로 단기가 약해졌습니다.`;
    case 'trendVolumeConfirm':
      return isJa ? `出来高確認は ${score}/100 で、価格変動を支えます。` : `거래량 확인은 ${score}/100으로 가격 변동을 지지합니다.`;
    case 'trendVolumeDivergence':
      return isJa ? `出来高確認は ${score}/100 で、価格と出来高の整合性が弱いです。` : `거래량 확인은 ${score}/100으로 가격과 거래량의 정합성이 약합니다.`;
    case 'trendNearResistance':
      return isJa ? `直近レジスタンスまで約 ${distance}% です。突破確認が必要です。` : `가까운 저항까지 약 ${distance}%입니다. 돌파 확인이 필요합니다.`;
    case 'trendNearSupport':
      return isJa ? `直近サポートから約 ${distance}% です。維持できるか確認します。` : `가까운 지지선에서 약 ${distance}%입니다. 지지 유지 여부를 확인합니다.`;
    case 'newsBullishSummary':
      return isJa
        ? `ニュースはネットで強気です。ポジティブ ${positiveScore}/100、ネガティブ ${negativeScore}/100、ネット ${netScore}、直近記事 ${p.total} 件。`
        : `뉴스는 순긍정입니다. 긍정 ${positiveScore}/100, 부정 ${negativeScore}/100, 순점수 ${netScore}, 최근 기사 ${p.total}건.`;
    case 'newsBearishSummary':
      return isJa
        ? `ニュースはネットで弱気です。ネガティブ ${negativeScore}/100、ポジティブ ${positiveScore}/100、ネット ${netScore}。`
        : `뉴스는 순부정입니다. 부정 ${negativeScore}/100, 긍정 ${positiveScore}/100, 순점수 ${netScore}.`;
    case 'newsMixedSummary':
      return isJa
        ? `ニュースは強弱混在です。ポジティブ ${positiveScore}/100、ネガティブ ${negativeScore}/100、ネット ${netScore}。`
        : `뉴스는 혼재되어 있습니다. 긍정 ${positiveScore}/100, 부정 ${negativeScore}/100, 순점수 ${netScore}.`;
    case 'newsNoEvidence':
      return isJa ? '利用できる直近ニュース根拠は見つかりませんでした。' : '사용 가능한 최근 뉴스 근거를 찾지 못했습니다.';
    case 'financialStrongSummary':
      return isJa
        ? `決算 / ファンダメンタル確認は強めです。利用可能指標 ${p.count} 件を確認しました。`
        : `실적 / 펀더멘털 점검은 강합니다. 사용 가능한 지표 ${p.count}개를 확인했습니다.`;
    case 'financialWeakSummary':
      return isJa
        ? `決算 / ファンダメンタル確認は弱めです。利用可能指標 ${p.count} 件を確認しました。`
        : `실적 / 펀더멘털 점검은 약합니다. 사용 가능한 지표 ${p.count}개를 확인했습니다.`;
    case 'financialMixedSummary':
      return isJa
        ? `決算 / ファンダメンタル確認は強弱混在です。利用可能指標 ${p.count} 件を確認しました。`
        : `실적 / 펀더멘털 점검은 혼재되어 있습니다. 사용 가능한 지표 ${p.count}개를 확인했습니다.`;
    case 'financialDataMissing':
      return isJa ? '財務データが限られています。より完全な開示またはデータを待ちます。' : '재무 데이터가 제한적입니다. 더 완전한 공시나 데이터를 기다립니다.';
    case 'financialValuationReasonable':
      return isJa ? `バリュエーションは妥当で、PE は約 ${p.value} です。` : `밸류에이션은 합리적이며 PE는 약 ${p.value}입니다.`;
    case 'financialValuationRich':
      return isJa
        ? `バリュエーションは割高で、PE は約 ${p.value}。織り込み済みの楽観に高く払いすぎないよう注意します。`
        : `밸류에이션은 비싸고 PE는 약 ${p.value}입니다. 이미 반영된 낙관에 과도한 가격을 지불하지 않도록 합니다.`;
    case 'financialWatchValuation':
      return isJa
        ? `バリュエーションは中立で、PE は約 ${p.value}。業績上方修正または価格調整を確認します。`
        : `밸류에이션은 중립이며 PE는 약 ${p.value}입니다. 실적 상향 또는 가격 조정을 확인합니다.`;
    case 'financialGrowthSupport':
      return isJa ? `成長指標は支援的で、スコアは ${p.score}/100 です。` : `성장 지표는 우호적이며 점수는 ${p.score}/100입니다.`;
    case 'financialGrowthWeak':
      return isJa ? `成長指標は弱く、スコアは ${p.score}/100 です。` : `성장 지표는 약하며 점수는 ${p.score}/100입니다.`;
    case 'financialWatchNextReport':
      return isJa ? '次回決算で売上高と EPS の確認を重視します。' : '다음 실적에서 매출과 EPS 확인을 중점적으로 봅니다.';
    case 'financialProfitabilitySupport':
      return isJa ? `収益性は支援的で、スコアは ${p.score}/100 です。` : `수익성은 우호적이며 점수는 ${p.score}/100입니다.`;
    case 'financialProfitabilityWeak':
      return isJa ? `収益性は弱く、スコアは ${p.score}/100 です。` : `수익성은 약하며 점수는 ${p.score}/100입니다.`;
    case 'financialDebtControlled':
      return isJa ? `負債リスクは管理可能で、スコアは ${p.score}/100 です。` : `부채 리스크는 관리 가능하며 점수는 ${p.score}/100입니다.`;
    case 'financialDebtRisk':
      return isJa ? `負債圧力が高く、スコアは ${p.score}/100 です。` : `부채 부담이 높고 점수는 ${p.score}/100입니다.`;
    case 'financialLiquiditySupport':
      return isJa
        ? `流動性と市場規模の代理指標は支援的で、スコアは ${p.score}/100 です。`
        : `유동성과 시가총액 대체 지표는 우호적이며 점수는 ${p.score}/100입니다.`;
    case 'financialLiquidityRisk':
      return isJa
        ? `流動性と市場規模の代理指標は弱く、スコアは ${p.score}/100 です。`
        : `유동성과 시가총액 대체 지표는 약하며 점수는 ${p.score}/100입니다.`;
    case 'financialAnalystUpside':
      return isJa
        ? `アナリスト目標は約 ${p.upside}% の上値余地を示し、${p.count} 件の意見に基づきます。`
        : `애널리스트 목표가는 약 ${p.upside}% 상승 여력을 시사하며 ${p.count}개 의견 기반입니다.`;
    case 'financialAnalystDownside':
      return isJa ? `アナリスト目標は約 ${p.upside}% の下値余地を示します。` : `애널리스트 목표가는 약 ${p.upside}% 하락 여력을 시사합니다.`;
    case 'financialDividendSupport':
      return isJa ? `配当利回り約 ${p.yield}% が株主還元の支えになります。` : `배당수익률 약 ${p.yield}%가 주주환원을 뒷받침합니다.`;
    case 'financialWatchHighRange':
      return isJa
        ? `株価は 52 週レンジの上位 ${p.position}% 付近です。反落リスクを確認します。`
        : `가격은 52주 범위의 상단 ${p.position}% 부근입니다. 되돌림 리스크를 확인합니다.`;
    case 'financialWatchLowRange':
      return isJa
        ? `株価は 52 週レンジの下位 ${p.position}% 付近です。割安の理由がファンダメンタル悪化か確認します。`
        : `가격은 52주 범위의 하단 ${p.position}% 부근입니다. 할인 원인이 펀더멘털 악화인지 확인합니다.`;
    case 'actionAccumulate':
      return isJa ? `提案アクション：スコアが ${p.score}/100 を保つ間は慎重に分割して集めます。` : `제안 행동: 점수가 ${p.score}/100을 유지하면 신중하게 분할 접근합니다.`;
    case 'actionReduceOrExit':
      return isJa ? `提案アクション：スコアが ${p.score}/100 から回復しなければ、縮小または撤退を検討します。` : `제안 행동: 점수가 ${p.score}/100에서 회복되지 않으면 축소 또는 이탈을 검토합니다.`;
    case 'actionWait':
      return isJa ? `提案アクション：確認を待ちます。現在のスコアは ${p.score}/100 です。` : `제안 행동: 확인을 기다립니다. 현재 점수는 ${p.score}/100입니다.`;
    case 'actionBuyInBatches':
      return isJa ? '一括で全ポジションを入れず、分割で入ります。' : '한 번에 전량 진입하지 말고 분할로 접근합니다.';
    case 'actionWaitNewsConfirmation':
      return isJa ? '増やす前に、追加の好材料ニュースまたは決算確認を待ちます。' : '비중 확대 전 추가 긍정 뉴스나 실적 확인을 기다립니다.';
    case 'actionUseSmallPosition':
      return isJa ? `リスクスコアが ${p.risk}/100 にとどまるため、ポジションは小さく保ちます。` : `리스크 점수가 ${p.risk}/100에 그치므로 포지션은 작게 유지합니다.`;
    case 'actionReduceExposure':
      return isJa ? `リサーチスコアが ${p.score}/100 にとどまるため、リスク露出を減らします。` : `리서치 점수가 ${p.score}/100에 그치므로 위험 노출을 줄입니다.`;
    case 'actionDoNotAverageDown':
      return isJa ? 'ネガティブニュースが優勢な間はナンピンしません。' : '부정 뉴스가 우세한 동안에는 물타기를 하지 않습니다.';
    case 'actionSetExitReview':
      return isJa ? '次の重要開示後に、短期の撤退レビューを設定します。' : '다음 주요 공시 이후 단기 이탈 검토를 설정합니다.';
    case 'actionNoChase':
      return isJa ? `追随買いは避けます。現在の確信度は ${p.score}/100 にとどまります。` : `추격 매수는 피합니다. 현재 확신도는 ${p.score}/100에 그칩니다.`;
    case 'actionWatchNewsCatalyst':
      return isJa
        ? '新しい触媒を確認します：決算上振れ、ガイダンス上方修正、格上げ、自社株買い、資金流入。'
        : '새 촉매를 확인합니다: 실적 서프라이즈, 가이던스 상향, 등급 상향, 자사주 매입, 자금 유입.';
    case 'actionWatchFinancialRepair':
      return isJa ? `${p.count} 個の弱い財務項目が改善し始めるか確認します。` : `약한 재무 항목 ${p.count}개가 회복되기 시작하는지 확인합니다.`;
    case 'actionWatchMomentumTurn':
      return isJa ? '比率を増やす前に、価格モメンタムの反転を確認します。' : '비중 확대 전 가격 모멘텀이 돌아서는지 확인합니다.';
    case 'actionRespectRisk':
      return isJa ? `リスクスコアは ${p.risk}/100。下値リスクを優先して管理します。` : `리스크 점수는 ${p.risk}/100입니다. 하방 리스크 관리를 우선합니다.`;
    case 'actionAvoidLimitDown':
      return isJa ? `本日 ${change}% 下落中の新規買いは避けます。` : `당일 ${change}% 하락 중인 신규 매수는 피합니다.`;
    case 'actionWaitPriceStabilization':
      return isJa ? `本日 ${change}% 下落後、価格安定を待って再評価します。` : `당일 ${change}% 하락 후 가격 안정화를 기다렸다가 재평가합니다.`;
    case 'actionWaitPullback':
      return isJa ? `反落リスクは ${pullbackRisk}/100。追随せず、整理または翌日の支えを待ちます。` : `되돌림 리스크는 ${pullbackRisk}/100입니다. 추격하지 말고 조정 또는 다음 거래일 지지를 기다립니다.`;
    case 'actionRequireNewsEvidence':
      return isJa ? '強い判断には、新しい会社固有ニュースの根拠が必要です。' : '강한 판단에는 새로운 회사별 뉴스 근거가 필요합니다.';
    case 'tCandidateSummary':
      return isJa ? `T候補：T適性 ${p.score}/100。流動性と売買可能な値幅があります。` : `T 후보: T 적합도 ${p.score}/100, 유동성과 거래 가능한 변동폭이 있습니다.`;
    case 'tWatchSummary':
      return isJa ? `T注視：T適性 ${p.score}/100。ただし確認条件はまだ不十分です。` : `T 관찰: T 적합도 ${p.score}/100, 다만 확인 조건이 아직 부족합니다.`;
    case 'tAvoidSummary':
      return isJa ? `T回避：T適性 ${p.score}/100。リスク・リターンがまだ明確ではありません。` : `T 회피: T 적합도 ${p.score}/100, 위험 대비 보상이 충분히 명확하지 않습니다.`;
    case 'tLiquidityReady':
      return isJa ? `流動性スコアは ${p.score}/100。エントリーと手仕舞いは比較的行いやすいです。` : `유동성 점수는 ${p.score}/100으로 진입과 청산이 비교적 수월합니다.`;
    case 'tLiquidityThin':
      return isJa ? `流動性スコアは ${p.score}/100 にとどまり、スリッページが T 取引に不利です。` : `유동성 점수는 ${p.score}/100에 그쳐 슬리피지가 T 매매에 불리할 수 있습니다.`;
    case 'tVolatilityReady':
      return isJa ? `推定売買可能変動は約 ${range}% で、日中の値幅取りに十分です。` : `예상 거래 가능 변동폭은 약 ${range}%로 장중 스프레드 작업에 충분합니다.`;
    case 'tVolatilityLow':
      return isJa ? `推定売買可能変動は ${range}% にとどまり、値幅が薄いです。` : `예상 거래 가능 변동폭은 ${range}%에 그쳐 스프레드가 얇습니다.`;
    case 'tSetupReady':
      return isJa ? `短期設定は ${p.score}/100。価格と出来高の支えがあります。` : `단기 설정은 ${p.score}/100이며 가격과 거래량 지지가 있습니다.`;
    case 'tTrendWeak':
      return isJa ? `モメンタムは ${p.score}/100 にとどまります。価格が強くなるのを待ちます。` : `모멘텀은 ${p.score}/100에 그칩니다. 가격이 강해지는지 기다립니다.`;
    case 'tPullbackRiskHigh':
      return isJa ? `反落リスクは ${p.risk}/100。T 取引で追随しません。` : `되돌림 리스크는 ${p.risk}/100입니다. T 매매로 추격하지 않습니다.`;
    case 'tDownsideRiskHigh':
      return isJa ? `下落リスクは ${p.risk}/100。値幅取りより防御を優先します。` : `하방 리스크는 ${p.risk}/100입니다. 스프레드 매매보다 방어가 우선입니다.`;
    case 'tNoChase':
      return isJa ? `株価はすでに ${p.change}% 上昇。追随ではなく、管理された押し目だけを検討します。` : `주가는 이미 ${p.change}% 상승했습니다. 추격이 아니라 통제된 눌림만 검토합니다.`;
    case 'tUseBasePositionOnly':
      return isJa ? 'これはベースポジションでの T 取引として扱い、新規の全力追随は避けます。' : '기존 기본 포지션 기반 T 매매로 사용하고, 신규 전량 추격 진입은 피합니다.';
    case 'tCutIfBreaksSupport':
      return isJa ? 'エントリーゾーンを支えなく下抜けた場合は、先に損切りまたは縮小します。' : '진입 구간을 지지 없이 이탈하면 먼저 손절하거나 축소합니다.';
    default:
      return null;
  }
}

function pointLabel(point: DecisionPoint) {
  const p = point.params;
  const score = p.score !== undefined ? Number(p.score).toFixed(1) : '';
  const count = Number(p.count ?? 0);
  const hours = Number(p.hours ?? 0);
  const positiveScore = Number(p.positiveScore ?? 0).toFixed(1);
  const negativeScore = Number(p.negativeScore ?? 0).toFixed(1);
  const netScore = signedScore(p.netScore);
  const change = Number(p.change ?? 0).toFixed(1);
  const pullbackRisk = Number(p.risk ?? 0).toFixed(1);
  const range = Number(p.range ?? 0).toFixed(1);
  const amount = String(p.amount ?? 'N/A');
  const ratio = Number(p.ratio ?? 0).toFixed(1);
  const continuation = Number(p.continuation ?? 0).toFixed(1);
  const risk = Number(p.risk ?? 0).toFixed(1);
  const distance = Number(p.distance ?? 0).toFixed(1);
  const rsi = Number(p.rsi ?? 0).toFixed(1);
  const heat = Number(p.heat ?? 0).toFixed(1);
  const impact = Number(p.impact ?? 0).toFixed(1);
  const today = Number(p.today ?? 0).toFixed(1);
  const future = Number(p.future ?? 0).toFixed(1);
  const exit = Number(p.exit ?? 0).toFixed(1);
  if (locale.value === 'nan-TW') {
    return nanDecisionPointLabel(point, score, count, hours);
  }
  const jaKoLabel = jaKoDecisionPointLabel(point, score, count, hours);
  if (jaKoLabel) return jaKoLabel;

  const text: Record<DecisionPoint['key'], LocalizedText> = {
    buySummary: {
      en: `Worth buying: total score ${p.score}/100, with enough relative strength under the selected news-led strategy.`,
      'zh-CN': `值得投资：总分 ${p.score}/100，在当前新闻权重策略下具备相对优势。`,
      'zh-TW': `值得投資：總分 ${p.score}/100，在目前新聞權重策略下具備相對優勢。`
    },
    watchSummary: {
      en: `Watch closely: total score ${p.score}/100, but confirmation is still incomplete.`,
      'zh-CN': `重点观察：总分 ${p.score}/100，但进场或离场确认还不完整。`,
      'zh-TW': `重點觀察：總分 ${p.score}/100，但進場或離場確認還不完整。`
    },
    sellSummary: {
      en: `Exit risk: total score ${p.score}/100, with weak risk/reward under this strategy.`,
      'zh-CN': `需要抛出：总分 ${p.score}/100，当前策略下风险报酬偏弱。`,
      'zh-TW': `需要拋出：總分 ${p.score}/100，目前策略下風險報酬偏弱。`
    },
    newsSupport: {
      en: `News is supportive: positive strength ${positiveScore}/100 vs negative ${negativeScore}/100, net ${netScore}.`,
      'zh-CN': `新闻正面强度 ${positiveScore}/100、负面 ${negativeScore}/100、净分 ${netScore}，对投资判断有支撑。`,
      'zh-TW': `新聞正面強度 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}，對投資判斷有支撐。`
    },
    newsPressure: {
      en: `News is pressuring the call: negative strength ${negativeScore}/100 vs positive ${positiveScore}/100, net ${netScore}.`,
      'zh-CN': `新闻负面强度 ${negativeScore}/100，高于正面 ${positiveScore}/100，净分 ${netScore}，且已有 ${count} 条相关信号。`,
      'zh-TW': `新聞負面強度 ${negativeScore}/100，高於正面 ${positiveScore}/100，淨分 ${netScore}，且已有 ${count} 則相關訊號。`
    },
    insufficientNews: {
      en: 'There is not enough recent news evidence, so confidence should be capped.',
      'zh-CN': '近期新闻证据不足，不能只靠行情分数做高信心判断。',
      'zh-TW': '近期新聞證據不足，不能只靠行情分數做高信心判斷。'
    },
    freshNews: {
      en: `Latest relevant news is fresh, about ${hours} hours old.`,
      'zh-CN': `最新相关新闻约 ${hours} 小时前，时效性较强。`,
      'zh-TW': `最新相關新聞約 ${hours} 小時前，時效性較強。`
    },
    momentumSupport: {
      en: `Price momentum is supportive at ${score}/100.`,
      'zh-CN': `价格动能 ${score}/100，对上涨延续有帮助。`,
      'zh-TW': `價格動能 ${score}/100，對上漲延續有幫助。`
    },
    weakMomentum: {
      en: `Momentum is weak at ${score}/100; avoid chasing before price confirms.`,
      'zh-CN': `动能偏弱，仅 ${score}/100，价格确认前不宜追高。`,
      'zh-TW': `動能偏弱，僅 ${score}/100，價格確認前不宜追高。`
    },
    watchBreakout: {
      en: `Watch whether momentum can improve above 60/100.`,
      'zh-CN': `观察动能能否提升到 60/100 以上。`,
      'zh-TW': `觀察動能能否提升到 60/100 以上。`
    },
    breakoutSetup: {
      en: `Early breakout setup scores ${score}/100 with price and volume confirmation.`,
      'zh-CN': `早期突破 setup ${score}/100，已有价格与成交量确认。`,
      'zh-TW': `早期突破 setup ${score}/100，已有價格與成交量確認。`
    },
    valuationSupport: {
      en: `Valuation score is healthy at ${score}/100.`,
      'zh-CN': `估值分 ${score}/100，价格相对没有明显过贵。`,
      'zh-TW': `估值分 ${score}/100，價格相對沒有明顯過貴。`
    },
    expensiveValuation: {
      en: `Valuation is stretched at ${score}/100.`,
      'zh-CN': `估值偏贵，只有 ${score}/100，需要防止利好兑现后回落。`,
      'zh-TW': `估值偏貴，只有 ${score}/100，需要防止利多兌現後回落。`
    },
    watchValuation: {
      en: 'Watch valuation change after the next earnings or guidance update.',
      'zh-CN': '观察下一次财报或指引后，估值是否重新变得合理。',
      'zh-TW': '觀察下一次財報或指引後，估值是否重新變得合理。'
    },
    riskControlled: {
      en: `Risk score is controlled at ${score}/100.`,
      'zh-CN': `风险控制 ${score}/100，波动和 beta 暂时可接受。`,
      'zh-TW': `風險控制 ${score}/100，波動和 beta 暫時可接受。`
    },
    riskHigh: {
      en: `Risk score is low at ${score}/100; downside protection is weak.`,
      'zh-CN': `风险分仅 ${score}/100，下行保护偏弱。`,
      'zh-TW': `風險分僅 ${score}/100，下行保護偏弱。`
    },
    watchRisk: {
      en: 'Watch volatility and whether drawdowns stabilize.',
      'zh-CN': '观察波动率和回撤是否收敛。',
      'zh-TW': '觀察波動率和回撤是否收斂。'
    },
    priceActionSevereDrop: {
      en: `Price fell ${change}% today; severe downside action blocks a quality-buy call.`,
      'zh-CN': `当日跌幅 ${change}%，大跌/跌停状态会拦截优质买入判断。`,
      'zh-TW': `當日跌幅 ${change}%，大跌/跌停狀態會攔截優質買入判斷。`
    },
    priceActionWeak: {
      en: `Price fell ${change}% today; wait for stabilization before considering entry.`,
      'zh-CN': `当日跌幅 ${change}%，价格企稳前只适合观察。`,
      'zh-TW': `當日跌幅 ${change}%，價格企穩前只適合觀察。`
    },
    overheatedPriceAction: {
      en: `Price is already up ${change}%; this is treated as chase risk, not a fresh buy setup.`,
      'zh-CN': `股价已上涨 ${change}%，这属于追高回落风险，不算新的买入 setup。`,
      'zh-TW': `股價已上漲 ${change}%，這屬於追高回落風險，不算新的買入 setup。`
    },
    pullbackRisk: {
      en: `Pullback risk is ${pullbackRisk}/100; wait for follow-through or a controlled reset.`,
      'zh-CN': `回落风险 ${pullbackRisk}/100，等待承接确认或有控制的回踩。`,
      'zh-TW': `回落風險 ${pullbackRisk}/100，等待承接確認或有控制的回踩。`
    },
    qualitySupport: {
      en: `Quality score is strong at ${score}/100.`,
      'zh-CN': `基本面质量 ${score}/100，对中期持有有支撑。`,
      'zh-TW': `基本面品質 ${score}/100，對中期持有有支撐。`
    },
    weakQuality: {
      en: `Quality score is weak at ${score}/100.`,
      'zh-CN': `基本面质量偏弱，仅 ${score}/100。`,
      'zh-TW': `基本面品質偏弱，僅 ${score}/100。`
    },
    watchNewsFlow: {
      en: `News is still mixed: positive ${positiveScore}/100, negative ${negativeScore}/100, net ${netScore}.`,
      'zh-CN': `新闻多空仍混合：正面 ${positiveScore}/100、负面 ${negativeScore}/100、净分 ${netScore}；重点看后续新闻转正还是转负。`,
      'zh-TW': `新聞多空仍混合：正面 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}；重點看後續新聞轉正還是轉負。`
    },
    fundFlowSupport: {
      en: `Today main fund flow is positive at ${amount}, ${ratio}% of turnover; liquidity is supportive.`,
      'zh-CN': `当日主力资金净流入 ${amount}，占成交额 ${ratio}%，资金面有支撑。`,
      'zh-TW': `當日主力資金淨流入 ${amount}，占成交額 ${ratio}%，資金面有支撐。`
    },
    fundFlowPressure: {
      en: `Today main fund flow is negative at ${amount}, ${ratio}% of turnover; liquidity is pressuring the setup.`,
      'zh-CN': `当日主力资金净流出 ${amount}，占成交额 ${ratio}%，资金面压制当前 setup。`,
      'zh-TW': `當日主力資金淨流出 ${amount}，占成交額 ${ratio}%，資金面壓制目前 setup。`
    },
    fundFlowWatch: {
      en: `Today main fund flow is ${amount}, ${ratio}% of turnover; flow direction is not decisive yet.`,
      'zh-CN': `当日主力资金 ${amount}，占成交额 ${ratio}%，资金方向暂不明确。`,
      'zh-TW': `當日主力資金 ${amount}，占成交額 ${ratio}%，資金方向暫不明確。`
    },
    newsHeatHotPositiveSummary: {
      en: `News heat is ${heat}/100 with ${impact}/100 positive impact.`,
      'zh-CN': `新闻热度 ${heat}/100，热度影响 ${impact}/100，市场关注偏正面。`,
      'zh-TW': `新聞熱度 ${heat}/100，熱度影響 ${impact}/100，市場關注偏正面。`
    },
    newsHeatHotNegativeSummary: {
      en: `News heat is ${heat}/100 with ${impact}/100 risk-weighted impact.`,
      'zh-CN': `新闻热度 ${heat}/100，热度影响 ${impact}/100，市场关注偏负面。`,
      'zh-TW': `新聞熱度 ${heat}/100，熱度影響 ${impact}/100，市場關注偏負面。`
    },
    newsHeatHotMixedSummary: {
      en: `News heat is ${heat}/100, but the direction is mixed.`,
      'zh-CN': `新闻热度 ${heat}/100，但多空方向仍然混合。`,
      'zh-TW': `新聞熱度 ${heat}/100，但多空方向仍然混合。`
    },
    newsHeatColdSummary: {
      en: `News heat is ${heat}/100; attention is limited.`,
      'zh-CN': `新闻热度 ${heat}/100，题材关注度有限。`,
      'zh-TW': `新聞熱度 ${heat}/100，題材關注度有限。`
    },
    newsHeatSupport: {
      en: `News heat impact is ${impact}/100 and supports the final review.`,
      'zh-CN': `新闻热度影响 ${impact}/100，对最终总评有加分。`,
      'zh-TW': `新聞熱度影響 ${impact}/100，對最終總評有加分。`
    },
    newsHeatRisk: {
      en: `News heat impact is ${impact}/100; attention is risk-weighted.`,
      'zh-CN': `新闻热度影响 ${impact}/100，热门消息反而偏风险。`,
      'zh-TW': `新聞熱度影響 ${impact}/100，熱門消息反而偏風險。`
    },
    newsHeatWatch: {
      en: `News heat impact is ${impact}/100; direction still needs confirmation.`,
      'zh-CN': `新闻热度影响 ${impact}/100，方向仍需要确认。`,
      'zh-TW': `新聞熱度影響 ${impact}/100，方向仍需要確認。`
    },
    newsHeatFresh: {
      en: `News freshness is ${score}/100; evidence is recent.`,
      'zh-CN': `新闻时效 ${score}/100，信息足够新。`,
      'zh-TW': `新聞時效 ${score}/100，資訊足夠新。`
    },
    newsHeatStale: {
      en: `News freshness is ${score}/100; attention may already be stale.`,
      'zh-CN': `新闻时效 ${score}/100，热度信息偏旧。`,
      'zh-TW': `新聞時效 ${score}/100，熱度資訊偏舊。`
    },
    overallStrongBuySummary: {
      en: `Final review ${p.score}/100: today buy, future rise, and profitable exit conditions are all aligned.`,
      'zh-CN': `最终总评 ${p.score}/100：今日值得买、后续上涨、明日及以后盈利卖出条件都较完整。`,
      'zh-TW': `最終總評 ${p.score}/100：今日值得買、後續上漲、明日及以後盈利賣出條件都較完整。`
    },
    overallBuySummary: {
      en: `Final review ${p.score}/100: today's entry has value and later profit-taking is plausible.`,
      'zh-CN': `最终总评 ${p.score}/100：今日有买入价值，后续也有盈利卖出空间。`,
      'zh-TW': `最終總評 ${p.score}/100：今日有買入價值，後續也有盈利賣出空間。`
    },
    overallWatchSummary: {
      en: `Final review ${p.score}/100: the setup is incomplete, so keep it on watch.`,
      'zh-CN': `最终总评 ${p.score}/100：条件还不完整，先列入重点观察。`,
      'zh-TW': `最終總評 ${p.score}/100：條件還不完整，先列入重點觀察。`
    },
    overallAvoidSummary: {
      en: `Final review ${p.score}/100: today's new buying is not clean enough.`,
      'zh-CN': `最终总评 ${p.score}/100：今日不适合新买，等待条件修复。`,
      'zh-TW': `最終總評 ${p.score}/100：今日不適合新買，等待條件修復。`
    },
    overallSellSummary: {
      en: `Final review ${p.score}/100: defense comes first; reduce or exit risk.`,
      'zh-CN': `最终总评 ${p.score}/100：风险优先，偏向减仓或退出。`,
      'zh-TW': `最終總評 ${p.score}/100：風險優先，偏向減倉或退出。`
    },
    overallTodayBuySupport: {
      en: `Today-buy score is ${today}/100, so the current entry has support.`,
      'zh-CN': `今日买入分 ${today}/100，当前买点有支撑。`,
      'zh-TW': `今日買入分 ${today}/100，目前買點有支撐。`
    },
    overallTodayBuyWeak: {
      en: `Today-buy score is ${today}/100, so the current entry is not clean.`,
      'zh-CN': `今日买入分 ${today}/100，当前买入条件不足。`,
      'zh-TW': `今日買入分 ${today}/100，目前買入條件不足。`
    },
    overallTodayBuyWatch: {
      en: `Today-buy score is ${today}/100; wait for confirmation.`,
      'zh-CN': `今日买入分 ${today}/100，需要继续确认。`,
      'zh-TW': `今日買入分 ${today}/100，需要繼續確認。`
    },
    overallFutureRiseSupport: {
      en: `Future-rise score is ${future}/100, supporting follow-through.`,
      'zh-CN': `后续上涨分 ${future}/100，延续机会较好。`,
      'zh-TW': `後續上漲分 ${future}/100，延續機會較好。`
    },
    overallFutureRiseWeak: {
      en: `Future-rise score is ${future}/100; upside edge is weak.`,
      'zh-CN': `后续上涨分 ${future}/100，后势优势不明确。`,
      'zh-TW': `後續上漲分 ${future}/100，後勢優勢不明確。`
    },
    overallFutureRiseWatch: {
      en: `Future-rise score is ${future}/100; direction still needs confirmation.`,
      'zh-CN': `后续上涨分 ${future}/100，方向仍需确认。`,
      'zh-TW': `後續上漲分 ${future}/100，方向仍需確認。`
    },
    overallProfitableExitSupport: {
      en: `Profitable-exit score is ${exit}/100, so later profit-taking is plausible.`,
      'zh-CN': `盈利卖出分 ${exit}/100，明日及以后更有机会卖出赚钱。`,
      'zh-TW': `盈利賣出分 ${exit}/100，明日及以後更有機會賣出賺錢。`
    },
    overallProfitableExitWeak: {
      en: `Profitable-exit score is ${exit}/100; later profit-taking is unclear.`,
      'zh-CN': `盈利卖出分 ${exit}/100，明日及以后卖出赚钱空间不清楚。`,
      'zh-TW': `盈利賣出分 ${exit}/100，明日及以後賣出賺錢空間不清楚。`
    },
    overallProfitableExitWatch: {
      en: `Profitable-exit score is ${exit}/100; watch next price and volume confirmation.`,
      'zh-CN': `盈利卖出分 ${exit}/100，要看后续量价能否延续。`,
      'zh-TW': `盈利賣出分 ${exit}/100，要看後續量價能否延續。`
    },
    overallNewsHeatSupport: {
      en: `News heat impact is ${impact}/100 and lifts the final review.`,
      'zh-CN': `新闻热度影响 ${impact}/100，热度方向抬升最终总评。`,
      'zh-TW': `新聞熱度影響 ${impact}/100，熱度方向抬升最終總評。`
    },
    overallNewsHeatRisk: {
      en: `News heat impact is ${impact}/100 and drags the final review.`,
      'zh-CN': `新闻热度影响 ${impact}/100，热度方向拖累最终总评。`,
      'zh-TW': `新聞熱度影響 ${impact}/100，熱度方向拖累最終總評。`
    },
    overallNewsHeatWatch: {
      en: `News heat impact is ${impact}/100 and is not decisive yet.`,
      'zh-CN': `新闻热度影响 ${impact}/100，尚未形成明确加减分。`,
      'zh-TW': `新聞熱度影響 ${impact}/100，尚未形成明確加減分。`
    },
    overallRiskTooHigh: {
      en: `Downside or reversal risk is ${risk}/100, so the final review is downgraded.`,
      'zh-CN': `下跌或反转风险 ${risk}/100，最终总评需要降级。`,
      'zh-TW': `下跌或反轉風險 ${risk}/100，最終總評需要降級。`
    },
    trendBullishSummary: {
      en: `Daily trend continuation is ${continuation}/100 with next-session reversal risk at ${risk}/100.`,
      'zh-CN': `日线延续分 ${continuation}/100，次日反转风险 ${risk}/100，趋势仍有支撑。`,
      'zh-TW': `日線延續分 ${continuation}/100，次日反轉風險 ${risk}/100，趨勢仍有支撐。`
    },
    trendConstructiveSummary: {
      en: `Daily trend continuation is ${continuation}/100; the setup is constructive but needs confirmation.`,
      'zh-CN': `日线延续分 ${continuation}/100，形态有条件，但仍需要确认。`,
      'zh-TW': `日線延續分 ${continuation}/100，型態有條件，但仍需要確認。`
    },
    trendNeutralSummary: {
      en: `Daily trend continuation is ${continuation}/100; direction is not decisive yet.`,
      'zh-CN': `日线延续分 ${continuation}/100，方向暂不明确。`,
      'zh-TW': `日線延續分 ${continuation}/100，方向暫不明確。`
    },
    trendRiskSummary: {
      en: `Next-session reversal risk is ${risk}/100; today's edge may not carry forward.`,
      'zh-CN': `次日反转风险 ${risk}/100，今天爬到的优势不一定能延续。`,
      'zh-TW': `次日反轉風險 ${risk}/100，今天爬到的優勢不一定能延續。`
    },
    trendContinuationSupport: {
      en: `Next-session continuation is ${continuation}/100 while reversal risk is ${risk}/100.`,
      'zh-CN': `次日延续分 ${continuation}/100，反转风险 ${risk}/100，短线延续性较好。`,
      'zh-TW': `次日延續分 ${continuation}/100，反轉風險 ${risk}/100，短線延續性較好。`
    },
    trendContinuationWeak: {
      en: `Next-session continuation is only ${continuation}/100 and reversal risk is ${risk}/100; do not treat today's edge as durable.`,
      'zh-CN': `次日延续分只有 ${continuation}/100，反转风险 ${risk}/100，不能把今天的优势当成明天仍有效。`,
      'zh-TW': `次日延續分只有 ${continuation}/100，反轉風險 ${risk}/100，不能把今天的優勢當成明天仍有效。`
    },
    trendContinuationWatch: {
      en: `Next-session continuation is ${continuation}/100; wait for the next price and volume confirmation.`,
      'zh-CN': `次日延续分 ${continuation}/100，需要等下一交易日量价确认。`,
      'zh-TW': `次日延續分 ${continuation}/100，需要等下一交易日量價確認。`
    },
    trendStructureSupport: {
      en: `Moving-average structure scores ${score}/100 and supports the daily trend.`,
      'zh-CN': `均线结构 ${score}/100，日线排列仍有支撑。`,
      'zh-TW': `均線結構 ${score}/100，日線排列仍有支撐。`
    },
    trendStructureWeak: {
      en: `Moving-average structure scores ${score}/100, so the daily trend is weak.`,
      'zh-CN': `均线结构 ${score}/100，日线趋势排列偏弱。`,
      'zh-TW': `均線結構 ${score}/100，日線趨勢排列偏弱。`
    },
    trendRsiHealthy: {
      en: `RSI is ${rsi}, so momentum is not obviously overheated.`,
      'zh-CN': `RSI 为 ${rsi}，动能暂未明显过热。`,
      'zh-TW': `RSI 為 ${rsi}，動能暫未明顯過熱。`
    },
    trendOverextended: {
      en: `RSI is ${rsi}; short-term overextension risk is rising.`,
      'zh-CN': `RSI 为 ${rsi}，短线过热风险上升。`,
      'zh-TW': `RSI 為 ${rsi}，短線過熱風險上升。`
    },
    trendMacdSupport: {
      en: `MACD momentum scores ${score}/100 and supports follow-through.`,
      'zh-CN': `MACD 动能 ${score}/100，支持后续延续。`,
      'zh-TW': `MACD 動能 ${score}/100，支持後續延續。`
    },
    trendMacdPressure: {
      en: `MACD momentum scores ${score}/100, showing short-term pressure.`,
      'zh-CN': `MACD 动能 ${score}/100，短线有转弱压力。`,
      'zh-TW': `MACD 動能 ${score}/100，短線有轉弱壓力。`
    },
    trendVolumeConfirm: {
      en: `Volume confirmation scores ${score}/100, so price movement has participation.`,
      'zh-CN': `量能确认 ${score}/100，价格变化有成交量配合。`,
      'zh-TW': `量能確認 ${score}/100，價格變化有成交量配合。`
    },
    trendVolumeDivergence: {
      en: `Volume confirmation scores ${score}/100; price and volume are not aligned enough.`,
      'zh-CN': `量能确认 ${score}/100，价量配合不足。`,
      'zh-TW': `量能確認 ${score}/100，價量配合不足。`
    },
    trendNearResistance: {
      en: `Nearest resistance is about ${distance}% away; wait for a clean breakout.`,
      'zh-CN': `距离近端压力约 ${distance}%，需要等待有效突破。`,
      'zh-TW': `距離近端壓力約 ${distance}%，需要等待有效突破。`
    },
    trendNearSupport: {
      en: `Nearest support is about ${distance}% away; watch whether it holds.`,
      'zh-CN': `距离近端支撑约 ${distance}%，重点观察是否守住。`,
      'zh-TW': `距離近端支撐約 ${distance}%，重點觀察是否守住。`
    },
    newsBullishSummary: {
      en: `News is net positive: positive strength ${positiveScore}/100 vs negative ${negativeScore}/100, net ${netScore}, from ${p.total} recent articles.`,
      'zh-CN': `新闻净偏多：正面强度 ${positiveScore}/100、负面 ${negativeScore}/100、净分 ${netScore}，来自 ${p.total} 条近期新闻。`,
      'zh-TW': `新聞淨偏多：正面強度 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}，來自 ${p.total} 則近期新聞。`
    },
    newsBearishSummary: {
      en: `News is net negative: negative strength ${negativeScore}/100 vs positive ${positiveScore}/100, net ${netScore}.`,
      'zh-CN': `新闻净偏空：负面强度 ${negativeScore}/100、高于正面 ${positiveScore}/100，净分 ${netScore}。`,
      'zh-TW': `新聞淨偏空：負面強度 ${negativeScore}/100、高於正面 ${positiveScore}/100，淨分 ${netScore}。`
    },
    newsMixedSummary: {
      en: `News is mixed: positive strength ${positiveScore}/100, negative ${negativeScore}/100, net ${netScore}.`,
      'zh-CN': `新闻多空混合：正面强度 ${positiveScore}/100、负面 ${negativeScore}/100、净分 ${netScore}。`,
      'zh-TW': `新聞多空混合：正面強度 ${positiveScore}/100、負面 ${negativeScore}/100、淨分 ${netScore}。`
    },
    newsNoEvidence: {
      en: 'No usable recent news evidence was found.',
      'zh-CN': '没有找到可用的近期新闻证据。',
      'zh-TW': '沒有找到可用的近期新聞證據。'
    },
    financialStrongSummary: {
      en: `Financial report check is strong across ${p.count} available metrics.`,
      'zh-CN': `财报/基本面检查偏强，覆盖 ${p.count} 个可用指标。`,
      'zh-TW': `財報/基本面檢查偏強，涵蓋 ${p.count} 個可用指標。`
    },
    financialWeakSummary: {
      en: `Financial report check is weak across ${p.count} available metrics.`,
      'zh-CN': `财报/基本面检查偏弱，覆盖 ${p.count} 个可用指标。`,
      'zh-TW': `財報/基本面檢查偏弱，涵蓋 ${p.count} 個可用指標。`
    },
    financialMixedSummary: {
      en: `Financial report check is mixed across ${p.count} available metrics.`,
      'zh-CN': `财报/基本面检查多空混合，覆盖 ${p.count} 个可用指标。`,
      'zh-TW': `財報/基本面檢查多空混合，涵蓋 ${p.count} 個可用指標。`
    },
    financialDataMissing: {
      en: 'Financial report data is limited; wait for more complete disclosure.',
      'zh-CN': '财报数据不足，需等待更完整的披露或数据源。',
      'zh-TW': '財報資料不足，需等待更完整的揭露或資料源。'
    },
    financialValuationReasonable: {
      en: `Valuation is reasonable with PE around ${p.value}.`,
      'zh-CN': `估值相对合理，PE 约 ${p.value}。`,
      'zh-TW': `估值相對合理，PE 約 ${p.value}。`
    },
    financialValuationRich: {
      en: `Valuation is rich with PE around ${p.value}; avoid paying for fully priced optimism.`,
      'zh-CN': `估值偏贵，PE 约 ${p.value}，避免为已兑现的乐观预期付太高价格。`,
      'zh-TW': `估值偏貴，PE 約 ${p.value}，避免為已兌現的樂觀預期付太高價格。`
    },
    financialWatchValuation: {
      en: `Valuation is neutral with PE around ${p.value}; watch earnings upgrades or price pullback.`,
      'zh-CN': `估值中性，PE 约 ${p.value}；观察盈利上修或价格回调。`,
      'zh-TW': `估值中性，PE 約 ${p.value}；觀察獲利上修或價格回檔。`
    },
    financialGrowthSupport: {
      en: `Growth metrics support the case, scoring ${p.score}/100.`,
      'zh-CN': `成长指标有支撑，评分 ${p.score}/100。`,
      'zh-TW': `成長指標有支撐，評分 ${p.score}/100。`
    },
    financialGrowthWeak: {
      en: `Growth metrics are weak, scoring ${p.score}/100.`,
      'zh-CN': `成长指标偏弱，评分 ${p.score}/100。`,
      'zh-TW': `成長指標偏弱，評分 ${p.score}/100。`
    },
    financialWatchNextReport: {
      en: 'Watch the next financial report for revenue and EPS confirmation.',
      'zh-CN': '重点观察下一份财报的营收与 EPS 是否确认改善。',
      'zh-TW': '重點觀察下一份財報的營收與 EPS 是否確認改善。'
    },
    financialProfitabilitySupport: {
      en: `Profitability is supportive at ${p.score}/100.`,
      'zh-CN': `盈利能力有支撑，评分 ${p.score}/100。`,
      'zh-TW': `獲利能力有支撐，評分 ${p.score}/100。`
    },
    financialProfitabilityWeak: {
      en: `Profitability is weak at ${p.score}/100.`,
      'zh-CN': `盈利能力偏弱，评分 ${p.score}/100。`,
      'zh-TW': `獲利能力偏弱，評分 ${p.score}/100。`
    },
    financialDebtControlled: {
      en: `Debt risk looks controlled, scoring ${p.score}/100.`,
      'zh-CN': `负债风险相对可控，评分 ${p.score}/100。`,
      'zh-TW': `負債風險相對可控，評分 ${p.score}/100。`
    },
    financialDebtRisk: {
      en: `Debt pressure is elevated, scoring ${p.score}/100.`,
      'zh-CN': `负债压力偏高，评分 ${p.score}/100。`,
      'zh-TW': `負債壓力偏高，評分 ${p.score}/100。`
    },
    financialLiquiditySupport: {
      en: `Liquidity and market-size proxy are supportive at ${p.score}/100.`,
      'zh-CN': `流动性和市值规模代理指标有支撑，评分 ${p.score}/100。`,
      'zh-TW': `流動性和市值規模代理指標有支撐，評分 ${p.score}/100。`
    },
    financialLiquidityRisk: {
      en: `Liquidity and market-size proxy are weak at ${p.score}/100.`,
      'zh-CN': `流动性和市值规模代理指标偏弱，评分 ${p.score}/100。`,
      'zh-TW': `流動性和市值規模代理指標偏弱，評分 ${p.score}/100。`
    },
    financialAnalystUpside: {
      en: `Analyst target implies about ${p.upside}% upside across ${p.count} opinions.`,
      'zh-CN': `分析师目标价隐含约 ${p.upside}% 上行空间，来自 ${p.count} 个意见。`,
      'zh-TW': `分析師目標價隱含約 ${p.upside}% 上行空間，來自 ${p.count} 個意見。`
    },
    financialAnalystDownside: {
      en: `Analyst target implies about ${p.upside}% downside.`,
      'zh-CN': `分析师目标价隐含约 ${p.upside}% 下行空间。`,
      'zh-TW': `分析師目標價隱含約 ${p.upside}% 下行空間。`
    },
    financialDividendSupport: {
      en: `Dividend yield around ${p.yield}% adds shareholder-return support.`,
      'zh-CN': `股息率约 ${p.yield}%，提供股东回报支撑。`,
      'zh-TW': `股息率約 ${p.yield}%，提供股東回報支撐。`
    },
    financialWatchHighRange: {
      en: `Price is near the upper part of its 52-week range at ${p.position}%; watch for pullback risk.`,
      'zh-CN': `价格位于 52 周区间较高位置（${p.position}%），观察回调风险。`,
      'zh-TW': `價格位於 52 週區間較高位置（${p.position}%），觀察回檔風險。`
    },
    financialWatchLowRange: {
      en: `Price is near the lower part of its 52-week range at ${p.position}%; watch whether fundamentals explain the discount.`,
      'zh-CN': `价格位于 52 周区间较低位置（${p.position}%），观察是否基本面恶化导致折价。`,
      'zh-TW': `價格位於 52 週區間較低位置（${p.position}%），觀察是否基本面惡化導致折價。`
    },
    actionAccumulate: {
      en: `Suggested action: accumulate carefully while the score remains ${p.score}/100.`,
      'zh-CN': `建议操作：在总分维持 ${p.score}/100 时，可考虑谨慎分批布局。`,
      'zh-TW': `建議操作：在總分維持 ${p.score}/100 時，可考慮謹慎分批布局。`
    },
    actionReduceOrExit: {
      en: `Suggested action: reduce or exit unless the score recovers from ${p.score}/100.`,
      'zh-CN': `建议操作：除非总分从 ${p.score}/100 明显修复，否则考虑降低仓位或退出。`,
      'zh-TW': `建議操作：除非總分從 ${p.score}/100 明顯修復，否則考慮降低倉位或退出。`
    },
    actionWait: {
      en: `Suggested action: wait for confirmation; current score is ${p.score}/100.`,
      'zh-CN': `建议操作：等待确认，目前总分 ${p.score}/100。`,
      'zh-TW': `建議操作：等待確認，目前總分 ${p.score}/100。`
    },
    actionBuyInBatches: {
      en: 'Use batches rather than a single full-position entry.',
      'zh-CN': '用分批方式，不要一次性满仓买入。',
      'zh-TW': '用分批方式，不要一次性滿倉買入。'
    },
    actionWaitNewsConfirmation: {
      en: 'Wait for another positive news or earnings confirmation before increasing size.',
      'zh-CN': '加仓前等待下一条正面新闻或财报确认。',
      'zh-TW': '加碼前等待下一則正面新聞或財報確認。'
    },
    actionUseSmallPosition: {
      en: `Keep position size small because risk score is only ${p.risk}/100.`,
      'zh-CN': `风险分只有 ${p.risk}/100，仓位应保持较小。`,
      'zh-TW': `風險分只有 ${p.risk}/100，倉位應保持較小。`
    },
    actionReduceExposure: {
      en: `Reduce exposure because the research score is only ${p.score}/100.`,
      'zh-CN': `研究评分只有 ${p.score}/100，应考虑降低风险暴露。`,
      'zh-TW': `研究評分只有 ${p.score}/100，應考慮降低風險暴露。`
    },
    actionDoNotAverageDown: {
      en: 'Do not average down while negative news events dominate.',
      'zh-CN': '负面新闻事件占优时，不建议越跌越买摊平。',
      'zh-TW': '負面新聞事件占優時，不建議越跌越買攤平。'
    },
    actionSetExitReview: {
      en: 'Set a near-term exit review after the next major disclosure.',
      'zh-CN': '在下一次重大公告或财报后重新评估是否继续持有。',
      'zh-TW': '在下一次重大公告或財報後重新評估是否繼續持有。'
    },
    actionNoChase: {
      en: `Do not chase; current conviction is only ${p.score}/100.`,
      'zh-CN': `不要追高，目前信心度只到 ${p.score}/100。`,
      'zh-TW': `不要追高，目前信心度只到 ${p.score}/100。`
    },
    actionWatchNewsCatalyst: {
      en: 'Watch for a new catalyst: earnings beat, guidance raise, upgrade, buyback, or fund inflow.',
      'zh-CN': '观察是否出现新催化：财报超预期、指引上修、评级上调、回购或资金流入。',
      'zh-TW': '觀察是否出現新催化：財報優於預期、指引上修、評級上調、回購或資金流入。'
    },
    actionWatchFinancialRepair: {
      en: `Watch whether ${p.count} weak financial item(s) start to repair.`,
      'zh-CN': `观察 ${p.count} 个偏弱财务项是否开始修复。`,
      'zh-TW': `觀察 ${p.count} 個偏弱財務項是否開始修復。`
    },
    actionWatchMomentumTurn: {
      en: 'Watch for price momentum to turn up before adding exposure.',
      'zh-CN': '加仓前观察价格动能是否转强。',
      'zh-TW': '加碼前觀察價格動能是否轉強。'
    },
    actionRespectRisk: {
      en: `Respect downside risk because risk score is ${p.risk}/100.`,
      'zh-CN': `风险分 ${p.risk}/100，必须优先控制下行风险。`,
      'zh-TW': `風險分 ${p.risk}/100，必須優先控制下行風險。`
    },
    actionAvoidLimitDown: {
      en: `Avoid new buying while the stock is down ${change}% today.`,
      'zh-CN': `当日跌幅 ${change}%，避免接跌停或急跌中的股票。`,
      'zh-TW': `當日跌幅 ${change}%，避免接跌停或急跌中的股票。`
    },
    actionWaitPriceStabilization: {
      en: `Wait for price stabilization after today's ${change}% drop.`,
      'zh-CN': `当日跌幅 ${change}%，等待价格企稳后再重新评估。`,
      'zh-TW': `當日跌幅 ${change}%，等待價格企穩後再重新評估。`
    },
    actionWaitPullback: {
      en: `Do not chase while pullback risk is ${pullbackRisk}/100; wait for a reset or next-session support.`,
      'zh-CN': `回落风险 ${pullbackRisk}/100，不追高；等待回踩或隔日承接确认。`,
      'zh-TW': `回落風險 ${pullbackRisk}/100，不追高；等待回踩或隔日承接確認。`
    },
    actionRequireNewsEvidence: {
      en: 'Require fresh company-specific news before making a strong call.',
      'zh-CN': '需要新的公司级新闻证据，才适合做高信心判断。',
      'zh-TW': '需要新的公司級新聞證據，才適合做高信心判斷。'
    },
    tCandidateSummary: {
      en: `T candidate: T suitability ${p.score}/100 with enough liquidity and tradable movement.`,
      'zh-CN': `适合做T：T适配 ${p.score}/100，具备流动性与可交易波动。`,
      'zh-TW': `適合做T：T適配 ${p.score}/100，具備流動性與可交易波動。`
    },
    tWatchSummary: {
      en: `T watch: T suitability ${p.score}/100, but confirmation is incomplete.`,
      'zh-CN': `做T等待确认：T适配 ${p.score}/100，条件还不完整。`,
      'zh-TW': `做T等待確認：T適配 ${p.score}/100，條件還不完整。`
    },
    tAvoidSummary: {
      en: `Avoid T: T suitability ${p.score}/100; risk/reward is not clean enough.`,
      'zh-CN': `不适合做T：T适配 ${p.score}/100，风险收益不够干净。`,
      'zh-TW': `不適合做T：T適配 ${p.score}/100，風險收益不夠乾淨。`
    },
    tLiquidityReady: {
      en: `Liquidity score is ${p.score}/100, so entries and exits should be more workable.`,
      'zh-CN': `流动性分 ${p.score}/100，进出场可操作性较好。`,
      'zh-TW': `流動性分 ${p.score}/100，進出場可操作性較好。`
    },
    tLiquidityThin: {
      en: `Liquidity score is only ${p.score}/100; slippage can hurt T trades.`,
      'zh-CN': `流动性分只有 ${p.score}/100，做T容易被滑点影响。`,
      'zh-TW': `流動性分只有 ${p.score}/100，做T容易被滑價影響。`
    },
    tVolatilityReady: {
      en: `Estimated tradable movement is about ${range}%, enough for intraday spread work.`,
      'zh-CN': `预估可交易波动约 ${range}%，具备日内差价空间。`,
      'zh-TW': `預估可交易波動約 ${range}%，具備日內差價空間。`
    },
    tVolatilityLow: {
      en: `Estimated tradable movement is only ${range}%, so spread is too thin.`,
      'zh-CN': `预估可交易波动只有 ${range}%，差价空间偏小。`,
      'zh-TW': `預估可交易波動只有 ${range}%，差價空間偏小。`
    },
    tSetupReady: {
      en: `Short-term setup scores ${p.score}/100 with price and volume support.`,
      'zh-CN': `短线 setup ${p.score}/100，价格与成交量有配合。`,
      'zh-TW': `短線 setup ${p.score}/100，價格與成交量有配合。`
    },
    tTrendWeak: {
      en: `Momentum is only ${p.score}/100; wait for price to turn stronger.`,
      'zh-CN': `动能只有 ${p.score}/100，先等价格转强。`,
      'zh-TW': `動能只有 ${p.score}/100，先等價格轉強。`
    },
    tPullbackRiskHigh: {
      en: `Pullback risk is ${p.risk}/100; do not chase for a T trade.`,
      'zh-CN': `回落风险 ${p.risk}/100，不适合追高做T。`,
      'zh-TW': `回落風險 ${p.risk}/100，不適合追高做T。`
    },
    tDownsideRiskHigh: {
      en: `Downside risk is ${p.risk}/100, so defense comes before spread trading.`,
      'zh-CN': `下跌风险 ${p.risk}/100，做T前必须先考虑防守。`,
      'zh-TW': `下跌風險 ${p.risk}/100，做T前必須先考慮防守。`
    },
    tNoChase: {
      en: `Price is already up ${p.change}%; only consider a controlled pullback, not chasing.`,
      'zh-CN': `股价已上涨 ${p.change}%，只等受控回踩，不追高。`,
      'zh-TW': `股價已上漲 ${p.change}%，只等受控回踩，不追高。`
    },
    tUseBasePositionOnly: {
      en: 'Use this as a base-position T trade, not a full fresh chase entry.',
      'zh-CN': '做T应以已有底仓为主，不要用全新仓位追价。',
      'zh-TW': '做T應以已有底倉為主，不要用全新倉位追價。'
    },
    tCutIfBreaksSupport: {
      en: 'If price breaks the entry zone without support, cut or reduce first.',
      'zh-CN': '如果跌破低吸区仍无承接，先止损或降仓。',
      'zh-TW': '如果跌破低吸區仍無承接，先停損或降倉。'
    }
  };
  return text[point.key][locale.value as StandardLocale] ?? text[point.key].en;
}

function eventLabel(event: NewsEvent) {
  if (locale.value === 'nan-TW') {
    const labels: Record<string, string> = {
      earningsPositive: '正面財報 / 業績事件',
      earningsNegative: '負面財報 / 業績事件',
      guidancePositive: '指引上修或展望改善',
      guidanceNegative: '指引下修或展望轉弱',
      analystPositive: '分析師上調評級 / 目標價',
      analystNegative: '分析師下調評級 / 目標價',
      capitalReturn: '回購 / 配息股東回報',
      shareholderSale: '股東或內部人賣壓',
      legalRegulatoryRisk: '法律或監管風險',
      demandPositive: '需求 / 訂單催化',
      demandNegative: '需求 / 訂單轉弱',
      fundFlowPositive: '資金流入 / 機構買入',
      fundFlowNegative: '資金流出 / 機構賣出',
      marketMomentumPositive: '市場動能正面事件',
      marketMomentumNegative: '市場動能負面事件',
      generalPositiveNews: '整體新聞氣口偏好',
      generalNegativeNews: '整體新聞氣口偏歹'
    };
    return labels[event.key] ?? event.key;
  }

  const labels: Record<string, LocalizedText> = {
    earningsPositive: { en: 'Positive earnings/report event', 'zh-CN': '正面财报/业绩事件', 'zh-TW': '正面財報/業績事件', ja: '決算 / 業績のポジティブ材料', ko: '긍정적 실적 / 보고서 이벤트' },
    earningsNegative: { en: 'Negative earnings/report event', 'zh-CN': '负面财报/业绩事件', 'zh-TW': '負面財報/業績事件', ja: '決算 / 業績のネガティブ材料', ko: '부정적 실적 / 보고서 이벤트' },
    guidancePositive: { en: 'Guidance raised or outlook improved', 'zh-CN': '指引上修或展望改善', 'zh-TW': '指引上修或展望改善', ja: 'ガイダンス上方修正 / 見通し改善', ko: '가이던스 상향 또는 전망 개선' },
    guidanceNegative: { en: 'Guidance cut or outlook weakened', 'zh-CN': '指引下修或展望转弱', 'zh-TW': '指引下修或展望轉弱', ja: 'ガイダンス下方修正 / 見通し悪化', ko: '가이던스 하향 또는 전망 약화' },
    analystPositive: { en: 'Analyst upgrade / target raised', 'zh-CN': '分析师上调评级/目标价', 'zh-TW': '分析師上調評級/目標價', ja: 'アナリスト格上げ / 目標株価引き上げ', ko: '애널리스트 등급 / 목표가 상향' },
    analystNegative: { en: 'Analyst downgrade / target cut', 'zh-CN': '分析师下调评级/目标价', 'zh-TW': '分析師下調評級/目標價', ja: 'アナリスト格下げ / 目標株価引き下げ', ko: '애널리스트 등급 / 목표가 하향' },
    capitalReturn: { en: 'Buyback/dividend shareholder return', 'zh-CN': '回购/分红股东回报', 'zh-TW': '回購/配息股東回報', ja: '自社株買い / 配当による株主還元', ko: '자사주 매입 / 배당 주주환원' },
    shareholderSale: { en: 'Shareholder or insider selling pressure', 'zh-CN': '股东/内部人减持压力', 'zh-TW': '股東/內部人減持壓力', ja: '株主 / インサイダー売り圧力', ko: '주주 / 내부자 매도 압력' },
    legalRegulatoryRisk: { en: 'Legal or regulatory risk', 'zh-CN': '法律或监管风险', 'zh-TW': '法律或監管風險', ja: '法務 / 規制リスク', ko: '법률 또는 규제 리스크' },
    demandPositive: { en: 'Demand/order catalyst', 'zh-CN': '需求/订单催化', 'zh-TW': '需求/訂單催化', ja: '需要 / 受注の好材料', ko: '수요 / 주문 촉매' },
    demandNegative: { en: 'Demand/order weakness', 'zh-CN': '需求/订单转弱', 'zh-TW': '需求/訂單轉弱', ja: '需要 / 受注の弱含み', ko: '수요 / 주문 약화' },
    fundFlowPositive: { en: 'Capital inflow / institutional buying', 'zh-CN': '资金流入/机构买入', 'zh-TW': '資金流入/機構買入', ja: '資金流入 / 機関投資家買い', ko: '자금 유입 / 기관 매수' },
    fundFlowNegative: { en: 'Capital outflow / institutional selling', 'zh-CN': '资金流出/机构卖出', 'zh-TW': '資金流出/機構賣出', ja: '資金流出 / 機関投資家売り', ko: '자금 유출 / 기관 매도' },
    marketMomentumPositive: { en: 'Positive market momentum event', 'zh-CN': '市场动能正面事件', 'zh-TW': '市場動能正面事件', ja: '市場モメンタムのポジティブ材料', ko: '시장 모멘텀 긍정 이벤트' },
    marketMomentumNegative: { en: 'Negative market momentum event', 'zh-CN': '市场动能负面事件', 'zh-TW': '市場動能負面事件', ja: '市場モメンタムのネガティブ材料', ko: '시장 모멘텀 부정 이벤트' },
    generalPositiveNews: { en: 'Broadly positive news tone', 'zh-CN': '整体新闻语气偏正面', 'zh-TW': '整體新聞語氣偏正面', ja: '全体的にポジティブなニューストーン', ko: '전반적으로 긍정적인 뉴스 분위기' },
    generalNegativeNews: { en: 'Broadly negative news tone', 'zh-CN': '整体新闻语气偏负面', 'zh-TW': '整體新聞語氣偏負面', ja: '全体的にネガティブなニューストーン', ko: '전반적으로 부정적인 뉴스 분위기' }
  };
  return labels[event.key]?.[locale.value as StandardLocale] ?? labels[event.key]?.en ?? event.key;
}

function financialMetricLabel(metric: FinancialMetric) {
  if (locale.value === 'nan-TW') {
    const labels: Record<string, string> = {
      pe: 'PE',
      priceToBook: 'PB',
      revenueGrowth: '營收成長',
      earningsGrowth: '獲利成長',
      returnOnEquity: 'ROE',
      profitMargins: '利潤率',
      debtToEquity: '負債 / 權益',
      analystTargetUpside: '分析師目標價空間',
      dividendYield: '股息率',
      liquidityQuality: '流動性 / 規模代理',
      etfTrend: 'ETF 趨勢',
      etfDrawdownControl: 'ETF 回撤控制',
      etfVolatility: 'ETF 波動控制',
      etfLiquidity: 'ETF 流動性',
      etfAssets: 'ETF 規模',
      etfExpenseRatio: 'ETF 費用率',
      etfDividendYield: 'ETF 收益率',
      etfRangePosition: 'ETF 區間位置',
      fundFlowMain: '主力資金流',
      fundFlowSuperLarge: '超大單資金流',
      fundFlowLarge: '大單資金流',
      fiftyTwoWeekPosition: '52 週位置'
    };
    return labels[metric.key] ?? metric.key;
  }

  const labels: Record<string, LocalizedText> = {
    pe: { en: 'PE', 'zh-CN': '市盈率', 'zh-TW': '本益比', ja: 'PER', ko: 'PER' },
    priceToBook: { en: 'PB', 'zh-CN': '市净率', 'zh-TW': '股價淨值比', ja: 'PBR', ko: 'PBR' },
    revenueGrowth: { en: 'Revenue growth', 'zh-CN': '营收增长', 'zh-TW': '營收成長', ja: '売上成長率', ko: '매출 성장률' },
    earningsGrowth: { en: 'Earnings growth', 'zh-CN': '利润增长', 'zh-TW': '獲利成長', ja: '利益成長率', ko: '이익 성장률' },
    returnOnEquity: { en: 'ROE', 'zh-CN': '净资产收益率', 'zh-TW': '股東權益報酬率', ja: 'ROE', ko: 'ROE' },
    profitMargins: { en: 'Profit margin', 'zh-CN': '利润率', 'zh-TW': '利潤率', ja: '利益率', ko: '이익률' },
    debtToEquity: { en: 'Debt/equity', 'zh-CN': '负债权益比', 'zh-TW': '負債權益比', ja: '負債資本倍率', ko: '부채 / 자기자본' },
    analystTargetUpside: { en: 'Analyst target upside', 'zh-CN': '分析师目标价空间', 'zh-TW': '分析師目標價空間', ja: 'アナリスト目標上値余地', ko: '애널리스트 목표가 상승 여력' },
    dividendYield: { en: 'Dividend yield', 'zh-CN': '股息率', 'zh-TW': '股息率', ja: '配当利回り', ko: '배당수익률' },
    liquidityQuality: { en: 'Liquidity/size proxy', 'zh-CN': '流动性/规模代理', 'zh-TW': '流動性/規模代理', ja: '流動性 / 規模代理', ko: '유동성 / 규모 대체 지표' },
    etfTrend: { en: 'ETF trend', 'zh-CN': 'ETF 趋势', 'zh-TW': 'ETF 趨勢', ja: 'ETF トレンド', ko: 'ETF 추세' },
    etfDrawdownControl: { en: 'Drawdown control', 'zh-CN': '回撤控制', 'zh-TW': '回撤控制', ja: 'ドローダウン管理', ko: '낙폭 관리' },
    etfVolatility: { en: 'Volatility control', 'zh-CN': '波动控制', 'zh-TW': '波動控制', ja: '変動性管理', ko: '변동성 관리' },
    etfLiquidity: { en: 'ETF liquidity', 'zh-CN': 'ETF 流动性', 'zh-TW': 'ETF 流動性', ja: 'ETF 流動性', ko: 'ETF 유동성' },
    etfAssets: { en: 'Fund assets', 'zh-CN': '基金规模', 'zh-TW': '基金規模', ja: 'ファンド規模', ko: '펀드 규모' },
    etfExpenseRatio: { en: 'Expense ratio', 'zh-CN': '费用率', 'zh-TW': '費用率', ja: '経費率', ko: '보수율' },
    etfDividendYield: { en: 'Distribution yield', 'zh-CN': '分配收益率', 'zh-TW': '配息收益率', ja: '分配利回り', ko: '분배 수익률' },
    etfRangePosition: { en: 'Range position', 'zh-CN': '区间位置', 'zh-TW': '區間位置', ja: 'レンジ位置', ko: '범위 위치' },
    fundFlowMain: { en: 'Main fund flow', 'zh-CN': '主力资金流', 'zh-TW': '主力資金流', ja: '主力資金フロー', ko: '주력 자금 흐름' },
    fundFlowSuperLarge: { en: 'Super-large order flow', 'zh-CN': '超大单资金流', 'zh-TW': '超大單資金流', ja: '超大口注文フロー', ko: '초대형 주문 흐름' },
    fundFlowLarge: { en: 'Large order flow', 'zh-CN': '大单资金流', 'zh-TW': '大單資金流', ja: '大口注文フロー', ko: '대형 주문 흐름' },
    fiftyTwoWeekPosition: { en: '52-week position', 'zh-CN': '52 周区间位置', 'zh-TW': '52 週區間位置', ja: '52週レンジ位置', ko: '52주 구간 위치' }
  };
  return labels[metric.key]?.[locale.value as StandardLocale] ?? labels[metric.key]?.en ?? metric.key;
}

function trendMetricLabel(metric: FinancialMetric) {
  if (locale.value === 'nan-TW') {
    const labels: Record<string, string> = {
      trendContinuation: '隔日延續',
      trendReversalRisk: '隔日反轉風險',
      trendMaStructure: '均線結構',
      trendShortReturns: '短中期漲跌',
      trendRsi14: 'RSI 14',
      trendMacd: 'MACD',
      trendVolume: '量能確認',
      trendSupportResistance: '支撐 / 壓力'
    };
    return labels[metric.key] ?? metric.key;
  }
  const labels: Record<string, LocalizedText> = {
    trendContinuation: { en: 'Next-session continuation', 'zh-CN': '次日延续', 'zh-TW': '次日延續', ja: '翌日継続性', ko: '다음 세션 지속성' },
    trendReversalRisk: { en: 'Next-session reversal risk', 'zh-CN': '次日反转风险', 'zh-TW': '次日反轉風險', ja: '翌日反転リスク', ko: '다음 세션 반전 리스크' },
    trendMaStructure: { en: 'Moving-average structure', 'zh-CN': '均线结构', 'zh-TW': '均線結構', ja: '移動平均構造', ko: '이동평균 구조' },
    trendShortReturns: { en: 'Short/medium returns', 'zh-CN': '短中期涨跌', 'zh-TW': '短中期漲跌', ja: '短中期リターン', ko: '단기 / 중기 수익률' },
    trendRsi14: { en: 'RSI 14', 'zh-CN': 'RSI 14', 'zh-TW': 'RSI 14', ja: 'RSI 14', ko: 'RSI 14' },
    trendMacd: { en: 'MACD', 'zh-CN': 'MACD', 'zh-TW': 'MACD', ja: 'MACD', ko: 'MACD' },
    trendVolume: { en: 'Volume confirmation', 'zh-CN': '量能确认', 'zh-TW': '量能確認', ja: '出来高確認', ko: '거래량 확인' },
    trendSupportResistance: { en: 'Support/resistance', 'zh-CN': '支撑/压力', 'zh-TW': '支撐/壓力', ja: 'サポート / レジスタンス', ko: '지지 / 저항' }
  };
  return labels[metric.key]?.[locale.value as StandardLocale] ?? labels[metric.key]?.en ?? metric.key;
}

function newsHeatMetricLabel(metric: FinancialMetric) {
  if (locale.value === 'nan-TW') {
    const labels: Record<string, string> = {
      newsHeat: '新聞熱度',
      newsHeatImpact: '熱度影響',
      newsFreshness: '新聞時效',
      newsSourceBreadth: '來源廣度',
      newsEventIntensity: '事件強度'
    };
    return labels[metric.key] ?? metric.key;
  }
  const labels: Record<string, LocalizedText> = {
    newsHeat: { en: 'News heat', 'zh-CN': '新闻热度', 'zh-TW': '新聞熱度', ja: 'ニュース注目度', ko: '뉴스 관심도' },
    newsHeatImpact: { en: 'Heat impact', 'zh-CN': '热度影响', 'zh-TW': '熱度影響', ja: '注目度の影響', ko: '관심도 영향' },
    newsFreshness: { en: 'Freshness', 'zh-CN': '时效性', 'zh-TW': '時效性', ja: '鮮度', ko: '신선도' },
    newsSourceBreadth: { en: 'Source breadth', 'zh-CN': '来源广度', 'zh-TW': '來源廣度', ja: 'ソースの広がり', ko: '출처 다양성' },
    newsEventIntensity: { en: 'Event intensity', 'zh-CN': '事件强度', 'zh-TW': '事件強度', ja: 'イベント強度', ko: '이벤트 강도' }
  };
  return labels[metric.key]?.[locale.value as StandardLocale] ?? labels[metric.key]?.en ?? metric.key;
}

function overallMetricLabel(metric: FinancialMetric) {
  if (locale.value === 'nan-TW') {
    const labels: Record<string, string> = {
      overallTotal: '總評分',
      overallTodayBuy: '今日買入',
      overallFutureRise: '後續上漲',
      overallProfitableExit: '盈利賣出',
      overallNewsHeatImpact: '新聞熱度影響'
    };
    return labels[metric.key] ?? metric.key;
  }
  const labels: Record<string, LocalizedText> = {
    overallTotal: { en: 'Final score', 'zh-CN': '最终总分', 'zh-TW': '最終總分', ja: '最終スコア', ko: '최종 점수' },
    overallTodayBuy: { en: 'Worth buying today', 'zh-CN': '今日是否值得买', 'zh-TW': '今日是否值得買', ja: '今日買う価値', ko: '오늘 매수 가치' },
    overallFutureRise: { en: 'Future rise potential', 'zh-CN': '后续上涨可能', 'zh-TW': '後續上漲可能', ja: '今後の上昇余地', ko: '향후 상승 가능성' },
    overallProfitableExit: { en: 'Profitable exit later', 'zh-CN': '明日以后盈利卖出', 'zh-TW': '明日以後盈利賣出', ja: '後日の利益確定', ko: '이후 수익 매도' },
    overallNewsHeatImpact: { en: 'News heat impact', 'zh-CN': '新闻热度影响', 'zh-TW': '新聞熱度影響', ja: 'ニュース注目度の影響', ko: '뉴스 관심도 영향' }
  };
  return labels[metric.key]?.[locale.value as StandardLocale] ?? labels[metric.key]?.en ?? metric.key;
}

function sectorLabel(pick: Pick) {
  return pick.sector && pick.sector !== 'Unknown' ? pick.sector : t.value.sectorUnavailable;
}

function sectorRecommendationLabel(recommendation: SectorRecommendation) {
  if (recommendation === 'overweight') return t.value.overweight;
  if (recommendation === 'underweight') return t.value.underweight;
  return t.value.sectorNeutral;
}

function sectorMetricValue(sector: SectorAnalysis, factor: keyof StrategyWeights) {
  return Number(sector.metrics[factor] ?? 0);
}

function sectorMetricWidth(sector: SectorAnalysis, factor: keyof StrategyWeights) {
  return `${Math.max(4, Math.min(100, sectorMetricValue(sector, factor)))}%`;
}

function sectorVerdictCount(sector: SectorAnalysis, verdict: Pick['verdict']) {
  return sector.verdictCounts[verdict] ?? 0;
}

function sectorMarketMixLabel(sector: SectorAnalysis) {
  return sector.marketMix.map((item) => `${item.market} ${item.count}`).join(' · ');
}

function sectorTLabel(sector: SectorAnalysis) {
  const count = sector.tCandidateCount ?? 0;
  const score = Number(sector.averageTScore ?? 0).toFixed(1);
  if (locale.value === 'en') return `T candidates ${count} · avg ${score}`;
  if (locale.value === 'zh-CN') return `做T候选 ${count} · 均分 ${score}`;
  if (locale.value === 'ja') return `T候補 ${count} · 平均 ${score}`;
  if (locale.value === 'ko') return `T 후보 ${count} · 평균 ${score}`;
  if (locale.value === 'nan-TW') return `做T候選 ${count} · 均分 ${score}`;
  return `做T候選 ${count} · 均分 ${score}`;
}

function sectorRiskLabel(sector: SectorAnalysis) {
  const score = Number(sector.averageDownsideRiskScore ?? 0).toFixed(1);
  if (locale.value === 'en') return `Avg downside ${score}`;
  if (locale.value === 'zh-CN') return `平均下跌风险 ${score}`;
  if (locale.value === 'ja') return `平均下落リスク ${score}`;
  if (locale.value === 'ko') return `평균 하락 리스크 ${score}`;
  if (locale.value === 'nan-TW') return `平均下跌風險 ${score}`;
  return `平均下跌風險 ${score}`;
}

function sectorInsight(sector: SectorAnalysis) {
  const ranked = weightKeys
    .map((factor) => ({ factor, score: sectorMetricValue(sector, factor) }))
    .sort((left, right) => right.score - left.score);
  const strongest = ranked[0];
  const weakest = ranked[ranked.length - 1];
  const tCount = sector.tCandidateCount ?? 0;
  const tScore = Number(sector.averageTScore ?? 0);
  if (locale.value === 'en') {
    if (sector.recommendation === 'overweight' && tCount > 0) {
      return `${factorLabel(strongest.factor)} leads at ${strongest.score.toFixed(1)}/100, with ${tCount} T candidate(s) and average T score ${tScore.toFixed(1)}.`;
    }
    if (sector.recommendation === 'overweight') {
      return `${factorLabel(strongest.factor)} leads at ${strongest.score.toFixed(1)}/100, while ${factorLabel(weakest.factor)} is the main check.`;
    }
    if (sector.recommendation === 'underweight') {
      return `${factorLabel(weakest.factor)} is dragging the sector at ${weakest.score.toFixed(1)}/100; keep exposure tight.`;
    }
    return `${factorLabel(strongest.factor)} is supportive, but ${factorLabel(weakest.factor)} still needs confirmation.`;
  }
  if (locale.value === 'zh-CN') {
    if (sector.recommendation === 'overweight' && tCount > 0) {
      return `${factorLabel(strongest.factor)} 最强，达到 ${strongest.score.toFixed(1)}/100；板块内有 ${tCount} 个做T候选，平均 T 分 ${tScore.toFixed(1)}。`;
    }
    if (sector.recommendation === 'overweight') {
      return `${factorLabel(strongest.factor)} 最强，达到 ${strongest.score.toFixed(1)}/100；${factorLabel(weakest.factor)} 是主要检查点。`;
    }
    if (sector.recommendation === 'underweight') {
      return `${factorLabel(weakest.factor)} 拖累明显，只有 ${weakest.score.toFixed(1)}/100，板块仓位应收紧。`;
    }
    return `${factorLabel(strongest.factor)} 有支撑，但 ${factorLabel(weakest.factor)} 仍需确认。`;
  }
  if (locale.value === 'ja') {
    if (sector.recommendation === 'overweight' && tCount > 0) {
      return `${factorLabel(strongest.factor)} が ${strongest.score.toFixed(1)}/100 でリードし、T候補は ${tCount} 件、平均Tスコアは ${tScore.toFixed(1)} です。`;
    }
    if (sector.recommendation === 'overweight') {
      return `${factorLabel(strongest.factor)} が ${strongest.score.toFixed(1)}/100 でリードし、${factorLabel(weakest.factor)} が主な確認点です。`;
    }
    if (sector.recommendation === 'underweight') {
      return `${factorLabel(weakest.factor)} が ${weakest.score.toFixed(1)}/100 と重く、セクターのエクスポージャーは控えめに。`;
    }
    return `${factorLabel(strongest.factor)} は支えになりますが、${factorLabel(weakest.factor)} はまだ確認が必要です。`;
  }
  if (locale.value === 'ko') {
    if (sector.recommendation === 'overweight' && tCount > 0) {
      return `${factorLabel(strongest.factor)}가 ${strongest.score.toFixed(1)}/100으로 가장 강하고, T 후보는 ${tCount}개, 평균 T 점수는 ${tScore.toFixed(1)}입니다.`;
    }
    if (sector.recommendation === 'overweight') {
      return `${factorLabel(strongest.factor)}가 ${strongest.score.toFixed(1)}/100으로 가장 강하고, ${factorLabel(weakest.factor)}가 주요 점검 항목입니다.`;
    }
    if (sector.recommendation === 'underweight') {
      return `${factorLabel(weakest.factor)}가 ${weakest.score.toFixed(1)}/100으로 부담이어서 섹터 비중은 타이트하게 관리합니다.`;
    }
    return `${factorLabel(strongest.factor)}는 지지 요인이지만 ${factorLabel(weakest.factor)}는 추가 확인이 필요합니다.`;
  }
  if (locale.value === 'nan-TW') {
    if (sector.recommendation === 'overweight' && tCount > 0) {
      return `${factorLabel(strongest.factor)} 較強，有 ${strongest.score.toFixed(1)}/100；板塊內有 ${tCount} 个做T候選，平均 T 分 ${tScore.toFixed(1)}。`;
    }
    if (sector.recommendation === 'overweight') {
      return `${factorLabel(strongest.factor)} 較強，有 ${strongest.score.toFixed(1)}/100；${factorLabel(weakest.factor)} 是主要檢查點。`;
    }
    if (sector.recommendation === 'underweight') {
      return `${factorLabel(weakest.factor)} 拖累較明顯，只有 ${weakest.score.toFixed(1)}/100，板塊倉位愛收斂。`;
    }
    return `${factorLabel(strongest.factor)} 有支撐，毋過 ${factorLabel(weakest.factor)} 猶愛確認。`;
  }
  if (sector.recommendation === 'overweight' && tCount > 0) {
    return `${factorLabel(strongest.factor)} 最強，達到 ${strongest.score.toFixed(1)}/100；板塊內有 ${tCount} 個做T候選，平均 T 分 ${tScore.toFixed(1)}。`;
  }
  if (sector.recommendation === 'overweight') {
    return `${factorLabel(strongest.factor)} 最強，達到 ${strongest.score.toFixed(1)}/100；${factorLabel(weakest.factor)} 是主要檢查點。`;
  }
  if (sector.recommendation === 'underweight') {
    return `${factorLabel(weakest.factor)} 拖累明顯，只有 ${weakest.score.toFixed(1)}/100，板塊倉位應收斂。`;
  }
  return `${factorLabel(strongest.factor)} 有支撐，但 ${factorLabel(weakest.factor)} 仍需確認。`;
}

function startLoadingFeedback() {
  stopLoadingFeedback();
  loadingRunId += 1;
  const currentRunId = loadingRunId;
  loading.value = true;
  loadingStartedAt.value = Date.now();
  loadingElapsedSeconds.value = 0;
  loadingStepIndex.value = 0;
  loadingTimer = window.setInterval(() => {
    if (currentRunId !== loadingRunId) return;
    loadingElapsedSeconds.value = Math.floor((Date.now() - loadingStartedAt.value) / 1000);
    loadingStepIndex.value = Math.max(
      loadingStepIndex.value,
      Math.min(analysisSteps.value.length - 1, Math.floor(loadingElapsedSeconds.value / 6))
    );
  }, 1000);
}

function stopLoadingFeedback() {
  loadingRunId += 1;
  if (loadingTimer !== undefined) {
    window.clearInterval(loadingTimer);
    loadingTimer = undefined;
  }
  loading.value = false;
}

function abortActiveAnalysis() {
  if (!analysisAbortController) return;
  analysisAbortController.abort();
  analysisAbortController = undefined;
}

function cancelAnalysis() {
  if (!loading.value) return;
  abortActiveAnalysis();
}

function isAnalysisAbort(cause: unknown) {
  return cause instanceof Error && cause.name === 'AbortError';
}

function isYogurtLocale(value: Locale) {
  return value === 'zh-TW' || value === 'nan-TW';
}

function toggleLanguageMenu() {
  languageMenuOpen.value = !languageMenuOpen.value;
}

function closeLanguageMenu() {
  languageMenuOpen.value = false;
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target;
  if (target instanceof Node && languageMenuRef.value?.contains(target)) return;
  closeLanguageMenu();
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeStockDetail();
    closeLanguageMenu();
  }
}

function setLocale(nextLocale: Locale) {
  const shouldPlayAppear = isYogurtLocale(nextLocale);
  locale.value = nextLocale;
  closeLanguageMenu();
  if (shouldPlayAppear) {
    playYogurtSound('appear');
  }
}

function getYogurtAudioContext() {
  if (typeof window === 'undefined') return null;
  const AudioContextCtor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextCtor) return null;
  if (!yogurtAudioContext) {
    yogurtAudioContext = new AudioContextCtor();
  }
  return yogurtAudioContext;
}

function playTone(context: AudioContext, startTime: number, frequency: number, duration: number, gainValue: number, type: OscillatorType = 'sine') {
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, startTime);
  gain.gain.setValueAtTime(0.0001, startTime);
  gain.gain.exponentialRampToValueAtTime(gainValue, startTime + 0.018);
  gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(startTime);
  oscillator.stop(startTime + duration + 0.03);
}

function encodeWavDataUri(samples: Int16Array, sampleRate: number) {
  const header = new ArrayBuffer(44);
  const view = new DataView(header);
  const writeString = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.byteLength, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, samples.byteLength, true);

  const bytes = new Uint8Array(header.byteLength + samples.byteLength);
  bytes.set(new Uint8Array(header), 0);
  bytes.set(new Uint8Array(samples.buffer), header.byteLength);
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 2048) {
    binary += String.fromCharCode(...bytes.slice(offset, offset + 2048));
  }
  return `data:audio/wav;base64,${window.btoa(binary)}`;
}

function createYogurtSoundDataUri(cue: YogurtSoundCue) {
  const sampleRate = 22050;
  const duration = cue === 'appear' ? 0.42 : 0.2;
  const samples = new Int16Array(Math.floor(sampleRate * duration));
  const addTone = (start: number, toneDuration: number, frequency: number, volume: number) => {
    const startIndex = Math.floor(start * sampleRate);
    const sampleCount = Math.floor(toneDuration * sampleRate);
    for (let index = 0; index < sampleCount && startIndex + index < samples.length; index += 1) {
      const progress = index / Math.max(1, sampleCount - 1);
      const envelope = Math.sin(Math.PI * progress);
      const sample = Math.sin((2 * Math.PI * frequency * index) / sampleRate) * envelope * volume;
      samples[startIndex + index] += Math.round(sample * 32767);
    }
  };

  if (cue === 'appear') {
    addTone(0, 0.18, 523.25, 0.28);
    addTone(0.055, 0.18, 659.25, 0.24);
    addTone(0.11, 0.2, 783.99, 0.22);
    addTone(0.2, 0.16, 1046.5, 0.14);
  } else {
    addTone(0, 0.09, 880, 0.34);
    addTone(0.045, 0.12, 1320, 0.22);
    addTone(0.1, 0.08, 660, 0.15);
  }

  return encodeWavDataUri(samples, sampleRate);
}

function playYogurtAudioFallback(cue: YogurtSoundCue) {
  if (typeof Audio === 'undefined') return false;
  try {
    yogurtAudioDataUris[cue] = yogurtAudioDataUris[cue] ?? createYogurtSoundDataUri(cue);
    const audio = new Audio(yogurtAudioDataUris[cue]);
    audio.volume = cue === 'appear' ? 0.42 : 0.48;
    void audio.play().catch(() => undefined);
    return true;
  } catch {
    return false;
  }
}

function playYogurtSound(cue: YogurtSoundCue) {
  const context = getYogurtAudioContext();
  if (!context) {
    playYogurtAudioFallback(cue);
    return;
  }
  void context.resume().then(() => {
    const now = context.currentTime;
    if (cue === 'appear') {
      [523.25, 659.25, 783.99].forEach((frequency, index) => {
        playTone(context, now + index * 0.055, frequency, 0.18, 0.035, 'sine');
      });
      playTone(context, now + 0.18, 1046.5, 0.16, 0.018, 'triangle');
      return;
    }

    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = 'triangle';
    oscillator.frequency.setValueAtTime(880, now);
    oscillator.frequency.exponentialRampToValueAtTime(1320, now + 0.06);
    oscillator.frequency.exponentialRampToValueAtTime(660, now + 0.16);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.055, now + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start(now);
    oscillator.stop(now + 0.2);
  }).catch(() => {
    playYogurtAudioFallback(cue);
  });
}

function clearYogurtSecretTimer() {
  if (yogurtSecretTimer !== undefined) {
    window.clearTimeout(yogurtSecretTimer);
    yogurtSecretTimer = undefined;
  }
}

function primeYogurtSecret() {
  clearYogurtSecretTimer();
  if (yogurtSecretLocalized.value) {
    playYogurtSound('tap');
  }
  yogurtSecretPrimed.value = true;
  yogurtSecretTimer = window.setTimeout(() => {
    if (!yogurtSecretOpen.value) {
      yogurtSecretPrimed.value = false;
    }
    yogurtSecretTimer = undefined;
  }, 7000);
}

function openYogurtSecret() {
  clearYogurtSecretTimer();
  yogurtSecretPrimed.value = false;
  yogurtSecretOpen.value = true;
}

function closeYogurtSecret() {
  clearYogurtSecretTimer();
  yogurtSecretPrimed.value = false;
  yogurtSecretOpen.value = false;
}

function stopAppTimers() {
  abortActiveAnalysis();
  stopLoadingFeedback();
  clearYogurtSecretTimer();
}

async function keepOptionalSymbolsVisible(event: Event) {
  const details = event.target as HTMLDetailsElement;
  if (!details.open) return;
  await nextTick();
  details.scrollIntoView({ block: 'end', inline: 'nearest', behavior: 'smooth' });
}

function upsertStreamingPick(pick: Pick) {
  const existing = picks.value.filter((item) => item.symbol !== pick.symbol);
  picks.value = [...existing, pick].sort((left, right) => right.score - left.score);
}

function handleAnalysisEvent(event: AnalysisStreamEvent) {
  if (event.type === 'started') {
    scanInfo.value = event.scan;
    if (event.portfolio) analysisPortfolio.value = event.portfolio;
    generatedAt.value = '';
    sectors.value = [];
    loadingStepIndex.value = 0;
    return;
  }
  if (event.type === 'pick') {
    if (event.picks) {
      picks.value = event.picks;
    } else {
      upsertStreamingPick(event.pick);
    }
    if (event.sectors) {
      sectors.value = event.sectors;
    }
    scanInfo.value = event.scan;
    if (event.portfolio) analysisPortfolio.value = event.portfolio;
    loadingStepIndex.value = Math.max(loadingStepIndex.value, 2);
    return;
  }
  if (event.type === 'error') {
    dataIssues.value = [...dataIssues.value, { symbol: event.symbol, error: event.error }];
    if (event.sectors) {
      sectors.value = event.sectors;
    }
    scanInfo.value = event.scan;
    if (event.portfolio) analysisPortfolio.value = event.portfolio;
    loadingStepIndex.value = Math.max(loadingStepIndex.value, 2);
    return;
  }
  picks.value = event.picks;
  sectors.value = event.sectors;
  dataIssues.value = event.errors;
  scanInfo.value = event.scan;
  analysisPortfolio.value = event.portfolio ?? null;
  generatedAt.value = new Date(event.generatedAt).toLocaleString();
  loadingStepIndex.value = analysisSteps.value.length - 1;
  recordRecommendationHistory(event.picks, event.generatedAt);
  scheduleUserStateSync();
}

async function runAnalysis() {
  if (loading.value) return;
  const portfolioForRequest = importedPortfolio.value ?? analysisPortfolio.value ?? undefined;
  const controller = new AbortController();
  analysisAbortController = controller;
  scanRunId.value += 1;
  signalRefreshStartedAt.value = new Date().toLocaleString();
  startLoadingFeedback();
  error.value = '';
  scanInfo.value = null;
  picks.value = [];
  sectors.value = [];
  dataIssues.value = [];
  analysisPortfolio.value = null;
  generatedAt.value = '';
  try {
    await analyzeStocksStream({
      markets: selectedMarkets.value.length ? selectedMarkets.value : defaultMarkets,
      symbols: symbols.value,
      strategyId: useCustom.value ? undefined : selectedStrategyId.value,
      customWeights: useCustom.value ? { ...customWeights } : undefined,
      refresh: true,
      portfolio: portfolioForRequest
    }, handleAnalysisEvent, { signal: controller.signal });
  } catch (cause) {
    error.value = isAnalysisAbort(cause) ? t.value.scanCancelled : (cause instanceof Error ? cause.message : 'Unknown error');
  } finally {
    if (analysisAbortController === controller) {
      analysisAbortController = undefined;
    }
    refreshDataMode();
    stopLoadingFeedback();
  }
}

watch(
  () => ({
    locale: locale.value,
    selectedMarkets: selectedMarkets.value,
    selectedStrategyId: selectedStrategyId.value,
    useCustom: useCustom.value,
    customWeights: { ...customWeights },
    symbolText: symbolText.value,
    manualHoldingText: manualHoldingText.value,
    displayMode: displayMode.value,
    activeInvestmentTask: activeTaskMode.value,
    activeView: activeView.value,
    resultSortKey: resultSortKey.value,
    resultSortDirection: resultSortDirection.value
  }),
  persistSettings,
  { deep: true }
);

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick);
  document.addEventListener('keydown', handleDocumentKeydown);
  refreshDataMode();
  await resumeAuthSession();
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
  document.removeEventListener('keydown', handleDocumentKeydown);
  stopAppTimers();
  if (userStateSyncTimer) window.clearTimeout(userStateSyncTimer);
});
</script>

<template>
  <main v-if="!authSession" class="auth-shell">
    <section class="auth-card">
      <div class="auth-brand">
        <p>{{ t.openSource }}</p>
        <h1>{{ t.appName }}</h1>
        <span>{{ authSubheading() }}</span>
      </div>

      <div class="auth-mode-tabs" role="tablist">
        <button type="button" :class="{ active: authMode === 'user' }" @click="authMode = 'user'">Key</button>
        <button type="button" :class="{ active: authMode === 'admin' }" @click="authMode = 'admin'">Admin</button>
      </div>

      <form v-if="authMode === 'user'" class="auth-form" @submit.prevent="submitAccessLogin">
        <label>
          <span>{{ authHeading() }}</span>
          <input v-model="accessKeyInput" type="password" autocomplete="current-password" placeholder="輸入你的登入 key" />
        </label>
        <button class="primary-action" type="submit" :disabled="authLoading || !accessKeyInput.trim()">
          <span v-if="authLoading" class="spinner" aria-hidden="true"></span>
          {{ authLoading ? t.loading : authHeading() }}
        </button>
      </form>

      <form v-else class="auth-form" @submit.prevent="submitAdminLogin">
        <label>
          <span>Admin username</span>
          <input v-model="adminUsernameInput" type="text" autocomplete="username" />
        </label>
        <label>
          <span>Admin password</span>
          <input v-model="adminPasswordInput" type="password" autocomplete="current-password" />
        </label>
        <button class="primary-action" type="submit" :disabled="authLoading || !adminUsernameInput.trim() || !adminPasswordInput">
          <span v-if="authLoading" class="spinner" aria-hidden="true"></span>
          {{ authLoading ? t.loading : 'Admin login' }}
        </button>
      </form>

      <p v-if="authError" class="auth-error">{{ authError }}</p>
      <p class="auth-footnote">GitHub Pages 不會內建管理員密碼；key 與管理員驗證都在 Cloud Run 後端完成。</p>
    </section>
  </main>

  <main v-else-if="isAdminSession" class="auth-shell admin-shell">
    <section class="admin-panel">
      <header class="admin-header">
        <div>
          <p>{{ t.openSource }}</p>
          <h1>使用者管理</h1>
          <span>{{ authUserLabel }}</span>
        </div>
        <button class="ghost" type="button" @click="logout">Logout</button>
      </header>

      <form class="admin-create-form" @submit.prevent="submitNewUser">
        <label>
          <span>New user key</span>
          <input v-model="newUserKey" type="password" autocomplete="new-password" placeholder="輸入新使用者 key" />
        </label>
        <label>
          <span>Label</span>
          <input v-model="newUserLabel" type="text" placeholder="使用者名稱/備註" />
        </label>
        <label>
          <span>Notes</span>
          <input v-model="newUserNotes" type="text" placeholder="例如 TW desk / family account" />
        </label>
        <label class="admin-check">
          <input v-model="newUserEnabled" type="checkbox" />
          <span>Enabled</span>
        </label>
        <button class="primary-action" type="submit" :disabled="adminLoading || !newUserKey.trim()">新增使用者</button>
      </form>

      <p v-if="adminError" class="auth-error">{{ adminError }}</p>

      <div class="admin-user-list">
        <article v-for="user in adminUsers" :key="user.id" class="admin-user-card" :class="{ disabled: !user.enabled }">
          <div>
            <strong>{{ user.id }}</strong>
            <span>key {{ user.keyFingerprint || '-' }} · last {{ user.lastLoginAt || '-' }}</span>
          </div>
          <label>
            <span>Label</span>
            <input v-model="user.label" type="text" />
          </label>
          <label>
            <span>Notes</span>
            <input v-model="user.notes" type="text" />
          </label>
          <label class="admin-check">
            <input v-model="user.enabled" type="checkbox" />
            <span>Enabled</span>
          </label>
          <div class="admin-actions">
            <button class="ghost" type="button" @click="saveAdminUser(user)">保存</button>
            <button class="ghost danger" type="button" @click="resetAdminUser(user)">重置資料</button>
          </div>
        </article>
      </div>
    </section>
  </main>

  <main v-else class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">{{ t.openSource }}</p>
        <h1>{{ t.appName }}</h1>
        <p class="subtitle">{{ t.subtitle }}</p>
      </div>

      <div ref="languageMenuRef" class="language-menu">
        <button
          class="language-trigger"
          type="button"
          aria-haspopup="menu"
          :aria-expanded="languageMenuOpen"
          @click="toggleLanguageMenu"
        >
          <span class="flag" :class="activeLanguageOption.flagClass"></span>
          <span>{{ activeLanguageOption.label }}</span>
          <i aria-hidden="true"></i>
        </button>
        <div v-if="languageMenuOpen" class="language-options" role="menu" aria-label="Language">
          <button
            v-for="option in languageOptions"
            :key="option.id"
            type="button"
            role="menuitemradio"
            :aria-checked="locale === option.id"
            :class="{ active: locale === option.id }"
            @click="setLocale(option.id)"
          >
            <span class="flag" :class="option.flagClass"></span>
            <span>{{ option.label }}</span>
            <strong aria-hidden="true">{{ option.shortLabel }}</strong>
          </button>
        </div>
      </div>

      <div class="session-chip">
        <span>{{ authUserLabel }}</span>
        <button type="button" @click="logout">Logout</button>
      </div>
    </header>

    <section class="status-strip">
      <div>
        <span>{{ t.backendStatus }}</span>
        <strong>{{ t.liveData }}</strong>
      </div>
      <div class="mode-status" :class="{ demo: isDemoDataMode }">
        <span>{{ t.dataMode }}</span>
        <strong>{{ dataModeLabel }}</strong>
        <small>{{ dataModeDescription }}</small>
      </div>
      <div>
        <span>{{ t.marketCoverage }}</span>
        <strong>{{ t.allMarkets }}</strong>
        <small>{{ preferredMarketsLabel }}</small>
      </div>
      <div class="mode-status">
        <span>{{ displayModeHint() }}</span>
        <strong>{{ displayModeLabel() }}</strong>
        <small>{{ isProfessionalMode ? detailAnalysisLabel() : decisionToplineLabel() }}</small>
      </div>
      <div>
        <span>{{ isAutoScan ? t.autoScan : t.refresh }}</span>
        <strong>{{ generatedAt || '-' }}</strong>
      </div>
    </section>

    <button
      class="yogurt-secret-tap"
      :class="{ armed: yogurtSecretPrimed, localized: yogurtSecretLocalized }"
      type="button"
      :aria-label="yogurtSecretLocalized ? '菌群雷達' : yogurtSecretPrimed ? 'Ugood Days clue unlocked' : 'Hidden supplier note'"
      @click="primeYogurtSecret"
    >
      <span v-if="yogurtSecretLocalized" class="yogurt-logo-mark" aria-hidden="true">
        <img :src="ugoodaysLogo" alt="" />
        <i class="yogurt-energy-ring ring-one"></i>
        <i class="yogurt-energy-ring ring-two"></i>
        <i class="yogurt-energy-burst"></i>
        <i class="yogurt-logo-bubble bubble-one"></i>
        <i class="yogurt-logo-bubble bubble-two"></i>
        <i class="yogurt-logo-bubble bubble-three"></i>
      </span>
      <span v-else aria-hidden="true"></span>
      <small v-if="yogurtSecretLocalized">{{ yogurtSecretTriggerLabel }}</small>
    </button>
    <button
      v-if="yogurtSecretPrimed && !yogurtSecretOpen"
      class="yogurt-secret-chip"
      :class="{ localized: yogurtSecretLocalized }"
      type="button"
      aria-label="Open Ugood Days supplier note"
      @click="openYogurtSecret"
    >
      {{ yogurtSecretClueLabel }}
    </button>

    <section class="workspace">
      <aside class="control-panel">
        <div class="control-scroll">
          <div class="panel-section task-panel">
            <h2>{{ controlPanelTitle() }}</h2>
            <div class="task-grid">
              <button
                v-for="task in investmentTasks"
                :key="task"
                type="button"
                :class="{ active: activeInvestmentTask === task }"
                @click="selectInvestmentTask(task)"
              >
                <strong>{{ investmentTaskLabel(task) }}</strong>
                <span>{{ investmentTaskHint(task) }}</span>
              </button>
            </div>
          </div>

          <div class="panel-section">
            <div class="section-row">
              <h2>{{ taskInputTitle() }}</h2>
              <span class="mode-pill">{{ scanLabel }}</span>
            </div>
            <template v-if="activeTaskMode !== 'portfolio'">
              <div class="scan-purpose">
                <strong>{{ t.symbolsBlank }}</strong>
                <span>{{ t.scanPurpose }}</span>
              </div>
              <div class="scan-universe-card">
                <div>
                  <span>{{ scanUniverseModeLabel(scanUniverse?.mode) }}</span>
                  <strong>{{ fullMarketAssuranceLabel() }}</strong>
                </div>
                <div class="scan-universe-grid">
                  <span>
                    <b>{{ scanUniverse?.candidatePoolSize ?? 0 }}</b>
                    {{ scanUniverseMetricLabel('candidatePoolSize') }}
                  </span>
                  <span>
                    <b>{{ scanUniverse?.deepAnalysisCount ?? 0 }}</b>
                    {{ scanUniverseMetricLabel('deepAnalysisCount') }}
                  </span>
                  <span>
                    <b>{{ scanUniverse?.displayedCount ?? picks.length }}</b>
                    {{ scanUniverseMetricLabel('displayedCount') }}
                  </span>
                </div>
                <small>{{ scanUniverseSourcePreview() }} · {{ scanUniverseFallbackLabel() }}</small>
              </div>
            </template>
            <div v-else class="portfolio-import portfolio-source-card">
              <div>
                <strong>{{ portfolioImportTitle() }}</strong>
                <span>{{ portfolioImportHint() }}</span>
              </div>
              <input
                ref="portfolioFileInput"
                class="visually-hidden"
                type="file"
                accept=".xls,.xlsx,.csv,.tsv,.txt,text/plain,text/csv,application/vnd.ms-excel"
                @change="onPortfolioFileSelected"
              />
              <div class="portfolio-import-actions">
                <button class="ghost" type="button" :disabled="loading || importingPortfolio" @click="triggerPortfolioImport">
                  {{ portfolioImportButtonLabel() }}
                </button>
                <button v-if="activePortfolio" class="ghost" type="button" :disabled="loading || importingPortfolio" @click="clearImportedPortfolio">
                  {{ clearPortfolioLabel() }}
                </button>
              </div>
              <details class="manual-holdings-entry">
                <summary>
                  <strong>{{ portfolioManualTitle() }}</strong>
                  <span>{{ portfolioManualHint() }}</span>
                </summary>
                <textarea
                  v-model="manualHoldingText"
                  rows="5"
                  spellcheck="false"
                  :placeholder="portfolioManualPlaceholder()"
                ></textarea>
                <button class="ghost" type="button" :disabled="loading || importingPortfolio || !manualHoldingText.trim()" @click="applyManualHoldings">
                  {{ portfolioManualApplyLabel() }}
                </button>
              </details>
              <div v-if="activePortfolio" class="portfolio-summary">
                <span>{{ portfolioReadyLabel(activePortfolio) }}</span>
                <strong>{{ moneyLabel(activePortfolio.totalMarketValue) }}</strong>
                <small>{{ signedMoneyLabel(activePortfolio.totalUnrealizedPnl) }} · {{ percentLabel(activePortfolio.totalUnrealizedPnlPct) }}</small>
                <ul v-if="activePortfolio.warnings?.length">
                  <li v-for="note in activePortfolio.warnings.slice(0, 3)" :key="note.key + JSON.stringify(note.params)" :class="note.severity">
                    {{ holdingNoteLabel(note) }}
                  </li>
                </ul>
              </div>
              <div v-else class="portfolio-source-status">
                <strong>{{ portfolioSourceCtaLabel() }}</strong>
                <span>{{ portfolioEmptyHint() }}</span>
              </div>
              <div v-if="portfolioMemory.length" class="portfolio-memory">
                <div class="portfolio-memory-heading">
                  <strong>{{ portfolioMemoryTitleLabel() }}</strong>
                  <span>{{ portfolioMemoryHintLabel() }}</span>
                </div>
                <article v-for="item in portfolioMemory" :key="item.id" class="portfolio-memory-item">
                  <div>
                    <strong>{{ item.title }}</strong>
                    <small>{{ portfolioMemoryMeta(item) }}</small>
                    <span>{{ item.symbols.slice(0, 4).join(' · ') }}</span>
                    <details class="portfolio-memory-diff">
                      <summary>{{ portfolioMemoryDiffTitle() }}</summary>
                      <small>{{ portfolioMemoryDiffLabel(item) }}</small>
                    </details>
                  </div>
                  <div class="portfolio-memory-actions">
                    <button class="ghost compact" type="button" :disabled="loading || importingPortfolio" @click="restorePortfolioMemory(item)">
                      {{ restorePortfolioLabel() }}
                    </button>
                    <button class="ghost compact danger" type="button" :disabled="loading || importingPortfolio" @click="deletePortfolioMemory(item.id)">
                      {{ deletePortfolioMemoryLabel() }}
                    </button>
                  </div>
                </article>
              </div>
              <p v-if="portfolioImportError" class="portfolio-error">{{ portfolioImportError }}</p>
            </div>
            <details v-if="activeTaskMode !== 'portfolio'" class="optional-symbols" @toggle="keepOptionalSymbolsVisible">
              <summary>{{ t.optionalSymbols }}</summary>
              <textarea v-model="symbolText" rows="4" spellcheck="false" :placeholder="t.symbolsPlaceholder"></textarea>
              <p class="strategy-copy">{{ t.symbolsHint }}</p>
            </details>
          </div>

          <div class="panel-section compact-market-section">
            <div class="section-row">
              <h2>{{ t.marketCoverage }}</h2>
              <span class="mode-pill">{{ preferredMarketsLabel }}</span>
            </div>
            <div class="market-grid compact">
              <button
                v-for="market in marketOptions"
                :key="market.id"
                :title="marketCoverageLabel(market.id)"
                :class="{ active: selectedMarkets.includes(market.id) }"
                @click="toggleMarket(market.id)"
              >
                <strong>{{ market.id }}</strong>
                <span>{{ marketLabel(market.id) }}</span>
                <small>{{ marketCoverageLabel(market.id) }}</small>
              </button>
            </div>
          </div>

          <details class="panel-section advanced-panel">
            <summary>
              <strong>{{ t.strategy }}</strong>
              <span>{{ selectedStrategy ? strategyName(selectedStrategy) : selectedStrategyId }}</span>
            </summary>
            <div class="advanced-body">
              <div class="section-row">
                <h2>{{ t.strategy }}</h2>
                <label class="switch">
                  <input v-model="useCustom" type="checkbox" />
                  <span>{{ t.customWeights }}</span>
                </label>
              </div>

              <select v-model="selectedStrategyId" :disabled="useCustom">
                <option v-for="strategy in strategies" :key="strategy.id" :value="strategy.id">
                  {{ strategyName(strategy) }}
                </option>
              </select>
              <p class="strategy-copy">{{ strategyDescription(selectedStrategy) }}</p>
              <div class="strategy-library-bar">
                <button class="ghost compact" type="button" :disabled="refreshingStrategies || loading" @click="refreshOnlineStrategies">
                  {{ refreshingStrategies ? strategyUi.refreshingStrategies : strategyUi.refreshStrategies }}
                </button>
                <span>{{ strategySourceSummary }}</span>
                <small v-if="strategyUpdatedLabel">{{ strategyUpdatedLabel }}</small>
              </div>
              <p v-if="selectedStrategy?.id === 'ai_smart_blend'" class="strategy-copy compact-copy">{{ strategyUi.aiBlendHint }}</p>
              <p v-if="strategyRefreshError" class="strategy-refresh-error">{{ strategyRefreshError }}</p>

              <div v-if="selectedDetailedWeightEntries.length" class="strategy-detail-box">
                <div class="strategy-detail-heading">
                  <strong>{{ strategyUi.detailedWeights }}</strong>
                  <span>{{ selectedDetailedWeightEntries.length }}</span>
                </div>
                <div class="strategy-weight-grid">
                  <span v-for="entry in selectedDetailedWeightEntries" :key="entry.key">
                    <b>{{ detailedWeightLabel(entry.key) }}</b>
                    <small>{{ entry.value.toFixed(1) }}%</small>
                  </span>
                </div>
              </div>

              <details v-if="selectedStrategySources.length" class="strategy-source-list">
                <summary>
                  <strong>{{ strategyUi.sourceLibrary }}</strong>
                  <span>{{ selectedStrategySources.length }} {{ strategyUi.sources }}</span>
                </summary>
                <a v-for="source in selectedStrategySources" :key="source.id" :href="source.url" target="_blank" rel="noreferrer">
                  <span>{{ source.title }}</span>
                  <small>
                    {{ source.available === true ? strategyUi.sourceAvailable : source.usable === true ? strategyUi.sourceFallback : source.available === false ? strategyUi.sourceFailed : strategyUi.sourcePending }}
                    <template v-if="source.matchedKeywords?.length"> · {{ strategyUi.matchedKeywords }} {{ source.matchedKeywords.length }}</template>
                  </small>
                </a>
              </details>

              <div class="weight-list">
                <label v-for="(_, key) in customWeights" :key="key">
                  <span>{{ t[key] }}</span>
                  <input v-model.number="customWeights[key]" :disabled="!useCustom" type="range" min="0" max="40" />
                  <strong>{{ customWeights[key] }}</strong>
                </label>
              </div>
            </div>
          </details>
        </div>

        <div class="control-actions">
          <div class="action-row">
            <button class="primary-action" type="button" :disabled="loading || primaryActionDisabled" @click="runAnalysis">
              <span v-if="loading" class="spinner" aria-hidden="true"></span>
              {{ primaryActionLabel }}
            </button>
            <button v-if="loading" class="ghost cancel-action" type="button" @click="cancelAnalysis">{{ t.cancelScan }}</button>
          </div>
          <div v-if="loading" class="analysis-inline" role="status" aria-live="polite">
            <span>{{ activeAnalysisStep }}</span>
            <strong>{{ loadingElapsedLabel }}</strong>
          </div>
          <p v-if="error" class="error">{{ error }}</p>
        </div>
      </aside>

      <section class="results">
        <div class="section-row">
          <h2>{{ activeView === 'stocks' ? activeResultTitle() : t.sectorIdeas }}</h2>
          <div class="result-actions">
            <div v-if="activeTaskMode !== 'portfolio'" class="view-toggle" role="tablist" aria-label="Result view">
              <button :class="{ active: activeView === 'stocks' }" type="button" @click="activeView = 'stocks'">
                {{ t.stockView }} <span>{{ filteredPicks.length }}</span>
              </button>
              <button :class="{ active: activeView === 'sectors' }" type="button" @click="activeView = 'sectors'">
                {{ t.sectorView }} <span>{{ sectors.length }}</span>
              </button>
            </div>
            <span v-else class="mode-pill">{{ activePortfolio ? portfolioReadyLabel(activePortfolio) : portfolioEmptyTitle() }}</span>
            <button class="ghost" :disabled="!canSaveScan" type="button" @click="saveCurrentScan">{{ t.saveScan }}</button>
            <button class="ghost" :disabled="!canSaveScan" type="button" @click="exportMarkdown">{{ t.exportMarkdown }}</button>
            <button class="ghost" :disabled="!canSaveScan" type="button" @click="exportJson">{{ t.exportJson }}</button>
            <button v-if="picks.length || scanInfo" class="ghost" :disabled="loading" @click="runAnalysis">{{ t.refresh }}</button>
          </div>
        </div>

        <div v-if="savedScans.length" class="saved-scan-bar">
          <strong>{{ t.savedScans }}</strong>
          <div class="saved-scan-list">
            <article v-for="scan in savedScans" :key="scan.id" class="saved-scan-item">
              <button type="button" @click="loadSavedScan(scan)">
                <span>{{ savedScanTitle(scan) }}</span>
                <small>{{ scan.savedAt }} · {{ scan.strategyName }}</small>
              </button>
              <button class="saved-scan-delete" type="button" :aria-label="t.deleteSavedScan" @click="deleteSavedScan(scan.id)">
                {{ t.deleteSavedScan }}
              </button>
            </article>
          </div>
        </div>

        <div v-if="recommendationReview.count" class="recommendation-review">
          <div>
            <span>{{ recommendationReviewTitle() }}</span>
            <strong>{{ recommendationReview.hitRate.toFixed(0) }}%</strong>
            <small>{{ recommendationReviewHint() }}</small>
          </div>
          <div class="recommendation-review-grid">
            <span>
              <b>{{ recommendationReview.count }}</b>
              {{ recommendationReviewMetricLabel('reviewed') }}
            </span>
            <span>
              <b>{{ recommendationReview.wins }}</b>
              {{ recommendationReviewMetricLabel('wins') }}
            </span>
            <span>
              <b>{{ contributionLabel(recommendationReview.averageReturn) }}%</b>
              {{ recommendationReviewMetricLabel('avg') }}
            </span>
            <span>
              <b>{{ contributionLabel(recommendationReview.worstReturn) }}%</b>
              {{ recommendationReviewMetricLabel('worst') }}
            </span>
          </div>
        </div>

        <div v-if="activeView === 'stocks' && activeTaskMode === 'portfolio'" class="portfolio-workbench">
          <div class="portfolio-workbench-heading">
            <div>
              <span>{{ portfolioActionBoardTitle() }}</span>
              <strong>{{ holdingCommandTitle() }}</strong>
              <p>{{ portfolioWorkbenchSubtitle() }}</p>
            </div>
            <button v-if="activePortfolio" class="ghost compact" type="button" :disabled="loading" @click="runAnalysis">
              {{ t.refresh }}
            </button>
          </div>

          <div v-if="!activePortfolio" class="portfolio-empty-state">
            <strong>{{ portfolioEmptyTitle() }}</strong>
            <p>{{ portfolioEmptyHint() }}</p>
            <button class="ghost compact" type="button" :disabled="loading || importingPortfolio" @click="triggerPortfolioImport">
              {{ portfolioImportButtonLabel() }}
            </button>
          </div>

          <template v-else>
            <div class="portfolio-dashboard-grid">
              <article v-for="metric in portfolioDashboardMetrics" :key="metric.key" :class="metric.tone">
                <span>{{ portfolioDashboardMetricLabel(metric.key) }}</span>
                <strong>{{ metric.value }}</strong>
                <small>{{ metric.detail }}</small>
              </article>
            </div>

            <ul v-if="activePortfolio.warnings?.length" class="holding-command-warnings">
              <li v-for="note in activePortfolio.warnings.slice(0, 4)" :key="note.key + JSON.stringify(note.params)" :class="note.severity">
                {{ holdingNoteLabel(note) }}
              </li>
            </ul>

            <section v-if="holdingActionItems.length" class="portfolio-action-board">
              <div class="portfolio-section-heading">
                <strong>{{ holdingActionListTitle() }}</strong>
                <span>{{ holdingCommandSubtitle() }}</span>
              </div>
              <div class="portfolio-action-table">
                <article v-for="item in holdingActionItems" :key="item.symbol" :class="[holdingActionTone(item.action), item.executionStatus]">
                  <div class="portfolio-action-symbol">
                    <b>{{ item.symbol }}</b>
                    <span>{{ item.name }}</span>
                  </div>
                  <span class="portfolio-action-chip" :class="holdingActionTone(item.action)">
                    {{ holdingActionDisplayLabel(item.action) }}
                  </span>
                  <div>
                    <small>{{ holdingPlannedQuantityTitle() }}</small>
                    <b>{{ holdingPlannedQuantityDisplay(item.plannedQuantityChange) }}</b>
                  </div>
                  <div>
                    <small>{{ holdingExecutableQuantityTitle() }}</small>
                    <b>{{ holdingExecutableQuantityDisplay(item.executableQuantityChange, item.executionStatus) }}</b>
                  </div>
                  <div>
                    <small>{{ t.riskControls }}</small>
                    <b>{{ holdingActionRuleLabel(item) }}</b>
                  </div>
                  <p>{{ holdingActionItemReasonLabel(item) }}</p>
                </article>
              </div>
            </section>

            <section class="portfolio-holding-board">
              <div class="portfolio-section-heading">
                <strong>{{ portfolioHoldingRowsTitle() }}</strong>
                <span>{{ holdingRows.length }} {{ portfolioPositionUnitLabel() }}</span>
              </div>
              <div class="portfolio-holding-list">
                <article v-for="row in holdingRows" :key="row.symbol" :class="[holdingActionTone(row.action), row.executionStatus]">
                  <div class="portfolio-holding-main">
                    <div>
                      <strong>{{ row.symbol }}</strong>
                      <span>{{ row.name }}</span>
                    </div>
                    <span class="portfolio-action-chip" :class="holdingActionTone(row.action)">
                      {{ holdingActionDisplayLabel(row.action) }}
                    </span>
                  </div>
                  <div class="portfolio-holding-metrics">
                    <span>
                      <small>{{ holdingFieldLabel('quantity') }}</small>
                      <b>{{ quantityAbsLabel(row.quantity) }}</b>
                    </span>
                    <span>
                      <small>{{ holdingExecutableQuantityTitle() }}</small>
                      <b>{{ holdingRowAvailableLabel(row) }}</b>
                    </span>
                    <span>
                      <small>{{ holdingFieldLabel('cost') }}</small>
                      <b>{{ moneyLabel(row.costPrice, row.currency) }}</b>
                    </span>
                    <span>
                      <small>{{ currentPriceLabel() }}</small>
                      <b>{{ moneyLabel(row.lastPrice, row.currency) }}</b>
                    </span>
                    <span>
                      <small>{{ holdingFieldLabel('pnl') }}</small>
                      <b>{{ signedMoneyLabel(row.unrealizedPnl, row.currency) }} · {{ percentLabel(row.unrealizedPnlPct) }}</b>
                    </span>
                    <span>
                      <small>{{ t.riskControls }}</small>
                      <b>{{ holdingExecutionStatusLabel(row.executionStatus) }}</b>
                    </span>
                  </div>
                  <details class="portfolio-holding-detail">
                    <summary>{{ holdingRowDetailTitle() }}</summary>
                    <div>
                      <span>{{ holdingRowRuleLabel(row) }}</span>
                      <span>{{ holdingRowPriceSourceLabel(row) }}</span>
                      <span v-if="row.stopLossPrice">{{ t.riskControls }} {{ moneyLabel(row.stopLossPrice, row.currency) }}</span>
                      <span v-if="row.takeProfitPrice">{{ t.actionPlan }} {{ moneyLabel(row.takeProfitPrice, row.currency) }}</span>
                    </div>
                    <ul v-if="row.notes.length">
                      <li v-for="note in row.notes.slice(0, 4)" :key="note.key + JSON.stringify(note.params)" :class="note.severity">
                        {{ holdingNoteLabel(note) }}
                      </li>
                    </ul>
                  </details>
                </article>
              </div>
            </section>
          </template>
        </div>

        <div v-if="activeView === 'stocks' && activeTaskMode !== 'portfolio'" class="decision-workbench">
          <div class="decision-workbench-heading">
            <div>
              <span>{{ scanUniverseModeLabel(scanUniverse?.mode) }}</span>
              <strong>{{ decisionWorkbenchTitle() }}</strong>
              <p>{{ workbenchSubtitle() }}</p>
            </div>
            <div v-if="scanUniverse" class="universe-pill" :class="{ live: scanUniverse.fullMarketSourceActive, fallback: scanUniverse.fallbackActive }">
              <b>{{ scanUniverse.fullMarketSourceActive ? fullMarketAssuranceLabel() : scanUniverseFallbackLabel() }}</b>
              <small>{{ scanUniverseSourcePreview() }}</small>
            </div>
          </div>

          <div class="decision-bucket-grid">
            <button
              v-for="item in decisionBucketItems"
              :key="item.bucket"
              type="button"
              :class="[item.tone, { active: activeWorkbenchBucket === item.bucket }]"
              @click="activeWorkbenchBucket = item.bucket"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.count }}</strong>
              <small>{{ workbenchBucketHint(item.bucket) }}</small>
            </button>
          </div>

          <div v-if="scanUniverse" class="universe-proof-strip">
            <span>
              <b>{{ scanUniverse.candidatePoolSize }}</b>
              {{ scanUniverseMetricLabel('candidatePoolSize') }}
            </span>
            <span>
              <b>{{ scanUniverse.deepAnalysisCount }}</b>
              {{ scanUniverseMetricLabel('deepAnalysisCount') }}
            </span>
            <span>
              <b>{{ scanUniverse.failedCount }}</b>
              {{ t.failures }}
            </span>
            <span v-for="source in scanUniverse.sourceBreakdown.slice(0, 3)" :key="`source-${source.source}`">
              <b>{{ source.count }}</b>
              {{ source.label }} · {{ sourceRoleLabel(source.role) }}
            </span>
          </div>

          <div v-if="topHoldingPicks.length || topEtfPicks.length" class="decision-shortcuts">
            <button v-if="topHoldingPicks.length" class="holding" type="button" @click="selectInvestmentTask('portfolio')">
              <strong>{{ holdingCommandTitle() }}</strong>
              <span>{{ topHoldingPicks.map((pick) => pick.symbol).join(' · ') }}</span>
            </button>
            <button v-if="topEtfPicks.length" class="etf" type="button" @click="activeWorkbenchBucket = 'etf'">
              <strong>{{ workbenchBucketLabel('etf') }}</strong>
              <span>{{ topEtfPicks.map((pick) => pick.symbol).join(' · ') }}</span>
            </button>
          </div>
        </div>

        <div v-if="activeView === 'stocks' && (picks.length || resultFiltersActive)" class="result-filter-bar">
          <div class="display-mode-toggle" role="group" :aria-label="displayModeHint()">
            <button
              type="button"
              :aria-pressed="displayMode === 'simple'"
              :class="{ active: displayMode === 'simple' }"
              @click="displayMode = 'simple'"
            >
              {{ displayModeLabel('simple') }}
            </button>
            <button
              type="button"
              :aria-pressed="displayMode === 'professional'"
              :class="{ active: displayMode === 'professional' }"
              @click="displayMode = 'professional'"
            >
              {{ displayModeLabel('professional') }}
            </button>
          </div>
          <label class="filter-field">
            <span>{{ t.marketCoverage }}</span>
            <select v-model="resultMarketFilter">
              <option value="all">{{ allMarketsFilterLabel() }}</option>
              <option v-for="market in marketOptions" :key="`filter-${market.id}`" :value="market.id">
                {{ market.id }} · {{ marketLabel(market.id) }}
              </option>
            </select>
          </label>
          <div class="filter-field">
            <span>{{ t.reasonTitle }}</span>
            <div class="filter-segment" role="group">
              <button
                v-for="option in verdictFilterOptions"
                :key="`verdict-filter-${option}`"
                type="button"
                :aria-pressed="resultVerdictFilter === option"
                :class="{ active: resultVerdictFilter === option }"
                @click="resultVerdictFilter = option"
              >
                {{ resultVerdictFilterLabel(option) }}
              </button>
            </div>
          </div>
          <label class="filter-field sort-field">
            <span>{{ sortFieldLabel() }}</span>
            <select v-model="resultSortKey">
              <option v-for="option in resultSortOptions" :key="`sort-${option}`" :value="option">
                {{ resultSortLabel(option) }}
              </option>
            </select>
          </label>
          <button class="ghost sort-direction" type="button" @click="resultSortDirection = resultSortDirection === 'desc' ? 'asc' : 'desc'">
            {{ sortDirectionLabel() }}
          </button>
          <strong class="filter-count">{{ resultCountLabel() }}</strong>
        </div>

        <div v-if="loading" class="analysis-wait" role="status" aria-live="polite">
          <div class="wait-meter">
            <span :style="{ width: `${((loadingStepIndex + 1) / analysisSteps.length) * 100}%` }"></span>
          </div>
          <div>
            <strong>{{ activeAnalysisStep }}</strong>
            <p>{{ loadingElapsedLabel }} · {{ scanLabel }}</p>
          </div>
          <button class="ghost wait-cancel" type="button" @click="cancelAnalysis">{{ t.cancelScan }}</button>
        </div>

        <div v-if="activeView === 'stocks'" class="pick-list">
          <article v-if="!loading && !picks.length && !dataIssues.length" class="empty-card">
            <strong>{{ t.emptyTitle }}</strong>
            <p>{{ t.emptyHint }}</p>
          </article>

          <article v-else-if="!loading && picks.length && !filteredPicks.length" class="empty-card">
            <strong>{{ filteredEmptyTitle() }}</strong>
            <p>{{ filteredEmptyHint() }}</p>
          </article>

          <article v-if="dataIssues.length" class="issue-card">
            <strong>{{ t.failures }}</strong>
            <p v-for="issue in dataIssues" :key="issue.symbol">{{ issue.symbol }}: {{ issue.error }}</p>
          </article>

          <article v-for="pick in filteredPicks" :key="pick.symbol" class="pick-card" :class="finalVerdictBucket(pick)">
            <div class="pick-heading">
              <div>
                <span class="market-tag">{{ pick.market }}</span>
                <span class="market-tag instrument-tag" :class="pick.instrumentType || 'stock'">{{ instrumentLabel(pick) }}</span>
                <h3>{{ pick.symbol }} · {{ pick.name }}</h3>
                <p>{{ sectorLabel(pick) }}</p>
              </div>
              <div class="score-pill">
                <span>{{ isProfessionalMode ? primaryScoreCaption(pick) : decisionToplineLabel() }}</span>
                <strong>
                  <template v-if="isProfessionalMode">{{ pick.decisionEngine?.rankScore ?? pick.overallAssessment?.totalScore ?? pick.score }}</template>
                  <template v-else>{{ decisionActionLabel(pick.finalDecision?.action ?? pick.decisionEngine?.action) }}</template>
                </strong>
              </div>
            </div>
            <div class="pick-toolbar">
              <button class="ghost compact" type="button" @click="openStockDetail(pick, 'intraday')">
                {{ strategyUi.openDetail }}
              </button>
            </div>

            <div class="metric-row">
              <span>{{ finalVerdictLabel(pick) }}</span>
              <span>{{ decisionExecutionLabel(pick) }}</span>
              <span class="market-rule-chip" :class="marketRuleStateTone(pick)">{{ marketRuleStateLabel(pick) }}</span>
              <span v-if="pick.decisionEngine" class="engine-chip" :class="pick.decisionEngine.dataQuality.level">{{ dataQualityLabel(pick.decisionEngine.dataQuality.level) }} {{ formatEngineScore(pick.decisionEngine.dataQuality.score) }}</span>
              <span>{{ pick.currency }} {{ pick.price }} · {{ pick.change > 0 ? '+' : '' }}{{ pick.change }}%</span>
              <template v-if="isProfessionalMode">
                <span>{{ t.confidence }} {{ pick.confidence }}%</span>
                <span v-if="pick.decisionEngine" class="engine-chip" :class="pick.decisionEngine.action">{{ decisionRegimeLabel(pick.decisionEngine.regime.name) }}</span>
                <span v-if="pick.decisionEngine?.marketSupport" class="market-source-chip" :class="pick.decisionEngine.marketSupport.coverageTier">{{ marketCoverageTierLabel(pick.decisionEngine.marketSupport.coverageTier) }} {{ formatEngineScore(pick.decisionEngine.marketSupport.score) }}</span>
                <span>{{ predictionScoreLabel('opportunity', pick) }}</span>
                <span>{{ predictionScoreLabel('setup', pick) }}</span>
                <span>{{ predictionScoreLabel('downside', pick) }}</span>
                <span>{{ predictionScoreLabel('pullback', pick) }}</span>
                <span v-if="pick.trendAnalysis">{{ predictionScoreLabel('continuation', pick) }}</span>
                <span v-if="pick.trendAnalysis">{{ predictionScoreLabel('reversal', pick) }}</span>
                <span v-if="pick.tPlan" class="t-score-chip" :class="pick.tPlan.suitability">{{ predictionScoreLabel('t', pick) }} · {{ tSuitabilityLabel(pick) }}</span>
                <span v-if="pick.market === 'CN' || pick.fundFlow?.available" class="fund-flow-chip" :class="fundFlowTone(pick.fundFlow)">{{ fundFlowChipLabel(pick) }}</span>
              </template>
            </div>

            <div v-if="pick.quoteConsensus" class="quote-consensus-strip" :class="pick.quoteConsensus.status">
              <div>
                <span>{{ quoteConsensusLabel(pick.quoteConsensus.status) }}</span>
                <strong>{{ quoteConsensusHint(pick) }}</strong>
              </div>
              <div class="quote-observations">
                <span v-if="!isProfessionalMode">{{ t.confidence }} {{ pick.quoteConsensus.confidence }}%</span>
                <template v-else>
                  <span v-for="observation in pick.quoteConsensus.observations.slice(0, 3)" :key="observation.source + observation.role">
                    {{ observation.source }} {{ pick.currency }} {{ observation.price }}
                  </span>
                </template>
              </div>
            </div>

            <div class="decision-topline" :class="pick.finalDecision?.action || pick.decisionEngine?.action || finalVerdictBucket(pick)">
              <div class="decision-topline-copy">
                <span>{{ decisionToplineLabel() }}</span>
                <strong>{{ finalVerdictLabel(pick) }}</strong>
                <p>{{ reportSummaryTitle(pick) }}</p>
                <ul class="concise-reason-list">
                  <li v-for="reason in conciseReasonItems(pick)" :key="reason">{{ reason }}</li>
                </ul>
              </div>
              <div class="decision-snapshot-grid">
                <div v-for="item in decisionSnapshotItems(pick)" :key="item.key" :class="item.tone">
                  <span>{{ item.label }}</span>
                  <b>{{ item.value }}</b>
                </div>
              </div>
            </div>

            <div v-if="pick.holding && pick.holdingAnalysis" class="research-panel holding-panel priority-panel" :class="pick.holdingAnalysis.action">
              <strong>{{ holdingActionLabel(pick.holdingAnalysis.action) }} · {{ pick.holding.name }}</strong>
              <div class="holding-grid">
                <div>
                  <span>{{ holdingFieldLabel('quantity') }}</span>
                  <b>{{ pick.holding.quantity }}</b>
                </div>
                <div>
                  <span>{{ holdingFieldLabel('cost') }}</span>
                  <b>{{ moneyLabel(pick.holding.costPrice, pick.currency) }}</b>
                </div>
                <div>
                  <span>{{ holdingFieldLabel('pnl') }}</span>
                  <b>{{ signedMoneyLabel(pick.holding.unrealizedPnl, pick.currency) }} · {{ percentLabel(pick.holding.unrealizedPnlPct) }}</b>
                </div>
                <div>
                  <span>{{ holdingFieldLabel('weight') }}</span>
                  <b>{{ pick.holdingAnalysis.positionWeightPct }}%</b>
                </div>
                <div v-if="pick.holdingAnalysis.targetWeightPct !== undefined">
                  <span>{{ holdingPlanTitle() }}</span>
                  <b>{{ pick.holdingAnalysis.targetWeightPct }}%</b>
                </div>
                <div v-if="pick.holdingAnalysis.plannedQuantityChange !== undefined">
                  <span>{{ holdingPlannedQuantityTitle() }}</span>
                  <b>{{ signedQuantityLabel(pick.holdingAnalysis.plannedQuantityChange) }}</b>
                </div>
                <div v-if="pick.holdingAnalysis.suggestedQuantityChange !== undefined">
                  <span>{{ holdingExecutableQuantityTitle() }}</span>
                  <b>{{ signedQuantityLabel(pick.holdingAnalysis.suggestedQuantityChange) }}</b>
                </div>
                <div v-if="pick.holdingAnalysis.executionStatus">
                  <span>{{ t.riskControls }}</span>
                  <b>{{ holdingExecutionStatusLabel(pick.holdingAnalysis.executionStatus) }}</b>
                </div>
                <div v-if="pick.holdingAnalysis.stopLossPrice">
                  <span>{{ t.riskControls }}</span>
                  <b>{{ pick.currency }} {{ pick.holdingAnalysis.stopLossPrice }}</b>
                </div>
                <div v-if="pick.holdingAnalysis.takeProfitPrice">
                  <span>{{ t.actionPlan }}</span>
                  <b>{{ pick.currency }} {{ pick.holdingAnalysis.takeProfitPrice }}</b>
                </div>
              </div>
              <ul class="holding-notes">
                <li v-for="note in pick.holdingAnalysis.notes" :key="note.key + JSON.stringify(note.params)" :class="note.severity">
                  {{ holdingNoteLabel(note) }}
                </li>
              </ul>
            </div>

            <div v-if="pick.instrumentType === 'etf'" class="research-panel etf-panel priority-panel" :class="pick.decisionEngine?.regime.name">
              <strong>{{ etfPanelTitle(pick) }} · {{ finalVerdictLabel(pick) }}</strong>
              <div class="financial-grid etf-profile-grid">
                <div v-for="metric in etfProfileRows(pick)" :key="metric.key">
                  <span>{{ metric.label }}</span>
                  <b>{{ metric.value }}</b>
                  <small>{{ t.score }} {{ Number(metric.score).toFixed(1) }}</small>
                </div>
              </div>
            </div>

            <details class="pick-detail-drawer" :open="isProfessionalMode">
              <summary>
                <strong>{{ detailAnalysisLabel() }}</strong>
                <span>{{ marketRuleStateLabel(pick) }} · {{ quoteConsensusLabel(pick.quoteConsensus?.status) }}</span>
              </summary>

            <div v-if="pick.decisionEngine" class="research-panel decision-engine-panel" :class="[pick.decisionEngine.action, pick.decisionEngine.dataQuality.level]">
              <strong>{{ decisionEngineTitle() }} · {{ decisionActionLabel(pick.decisionEngine.action) }}</strong>
              <div class="engine-summary-grid">
                <div>
                  <span>{{ resultSortLabel('decision') }}</span>
                  <b>{{ formatEngineScore(pick.decisionEngine.rankScore) }}</b>
                  <small>{{ decisionRegimeLabel(pick.decisionEngine.regime.name) }}</small>
                </div>
                <div>
                  <span>{{ t.riskControls }}</span>
                  <b>{{ formatEngineScore(pick.decisionEngine.sellScore) }}</b>
                  <small>{{ formatEngineScore(pick.decisionEngine.riskRewardScore) }} RR</small>
                </div>
                <div>
                  <span>{{ dataQualityLabel(pick.decisionEngine.dataQuality.level) }}</span>
                  <b>{{ formatEngineScore(pick.decisionEngine.dataQuality.score) }}</b>
                  <small>{{ engineCoverageLabel(pick) }}</small>
                </div>
                <div>
                  <span>{{ marketSupportTitle() }}</span>
                  <b>{{ formatEngineScore(pick.decisionEngine.marketSupport?.score ?? pick.decisionEngine.dataQuality.marketSupportScore) }}</b>
                  <small>{{ marketSourceStackLabel(pick) }}</small>
                </div>
                <div>
                  <span>{{ t.confidence }}</span>
                  <b>{{ formatEngineScore(pick.decisionEngine.confidenceScore) }}%</b>
                  <small>{{ decisionReasonLabel('legacyWeights:secondary') }}</small>
                </div>
              </div>
              <div v-if="pick.decisionEngine.gates?.length" class="engine-gate-list">
                <span v-for="gate in pick.decisionEngine.gates" :key="gate.key + gate.kind" :class="gate.severity">
                  {{ decisionGateLabel(gate.key) }}
                </span>
              </div>
              <div class="engine-reason-list">
                <span v-for="reason in pick.decisionEngine.primaryReasons || []" :key="reason">{{ decisionReasonLabel(reason) }}</span>
              </div>
            </div>

            <div v-if="pick.professionalAnalytics" class="research-panel professional-panel" :class="pick.professionalAnalytics.alertMonitor.priority">
              <strong>{{ professionalAnalyticsTitle() }} · {{ benchmarkRankLabel(pick.professionalAnalytics.benchmarkRelative.rank) }}</strong>
              <div class="professional-grid">
                <div class="professional-section">
                  <span>{{ professionalModuleLabel('factor') }}</span>
                  <b>{{ pick.professionalAnalytics.factorModel.style }}</b>
                  <small>{{ professionalModuleLabel('factor') }} {{ formatEngineScore(pick.professionalAnalytics.factorModel.coverageScore) }}/100</small>
                </div>
                <div class="professional-section">
                  <span>{{ professionalModuleLabel('benchmark') }}</span>
                  <b>{{ formatEngineScore(pick.professionalAnalytics.benchmarkRelative.relativeScore) }}/100</b>
                  <small>{{ pick.professionalAnalytics.benchmarkRelative.benchmark.symbol }} · {{ benchmarkRankLabel(pick.professionalAnalytics.benchmarkRelative.rank) }}</small>
                </div>
                <div class="professional-section">
                  <span>{{ professionalModuleLabel('tracker') }}</span>
                  <b>{{ contributionLabel(pick.professionalAnalytics.recommendationTracker.expectedEdgePct) }}%</b>
                  <small>{{ professionalCheckpointLabel(pick) }}</small>
                </div>
                <div class="professional-section">
                  <span>{{ professionalModuleLabel('attribution') }}</span>
                  <b>{{ contributionLabel(pick.professionalAnalytics.attribution.netContribution) }}</b>
                  <small>{{ pick.professionalAnalytics.attribution.drivers.slice(0, 2).map((driver) => driver.label).join(' / ') }}</small>
                </div>
                <div class="professional-section">
                  <span>{{ professionalModuleLabel('optimizer') }}</span>
                  <b>{{ pick.professionalAnalytics.portfolioOptimizer?.targetWeightPct ?? 0 }}%</b>
                  <small>{{ pick.professionalAnalytics.portfolioOptimizer?.concentrationAction ?? 'hold' }} · risk {{ formatEngineScore(pick.professionalAnalytics.portfolioOptimizer?.marginalRiskScore) }}</small>
                </div>
                <div class="professional-section">
                  <span>{{ professionalModuleLabel('alerts') }}</span>
                  <b>{{ alertPriorityLabel(pick.professionalAnalytics.alertMonitor.priority) }}</b>
                  <small>{{ pick.professionalAnalytics.alertMonitor.rules.slice(0, 2).map((rule) => rule.key).join(' / ') }}</small>
                </div>
              </div>
              <div class="factor-strip">
                <span v-for="factor in professionalFactorRows(pick)" :key="factor.key" :class="factor.tone">
                  {{ factor.label }} {{ formatEngineScore(factor.score) }}
                </span>
              </div>
            </div>

            <div class="integrated-report" :class="finalVerdictBucket(pick)">
              <div class="integrated-report-heading">
                <div>
                  <strong>{{ t.finalReview }} · {{ reportSummaryTitle(pick) }}</strong>
                  <p v-if="reportSummarySubtitle(pick)">{{ reportSummarySubtitle(pick) }}</p>
                </div>
                <span v-if="pick.overallAssessment">{{ pick.overallAssessment.totalScore }}/100</span>
              </div>
              <div class="report-metric-strip">
                <div v-for="metric in reportMetricItems(pick)" :key="metric.key">
                  <span>{{ metric.label }}</span>
                  <b>{{ metric.value }}</b>
                </div>
              </div>
              <div class="report-columns">
                <div>
                  <strong>{{ t.positiveReasons }}</strong>
                  <ul>
                    <li v-for="item in reportSupportItems(pick)" :key="item">{{ item }}</li>
                  </ul>
                </div>
                <div>
                  <strong>{{ t.negativeReasons }}</strong>
                  <ul>
                    <li v-for="item in reportRiskItems(pick)" :key="item">{{ item }}</li>
                  </ul>
                </div>
                <div>
                  <strong>{{ t.watchItems }}</strong>
                  <ul>
                    <li v-for="item in reportWatchItems(pick)" :key="item">{{ item }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <div v-if="pick.strategyAssessment" class="research-panel strategy-model-panel" :class="pick.strategyAssessment.recommendation">
              <strong>{{ strategyUi.decisionModel }} · {{ strategyRecommendationLabel(pick) }}</strong>
              <div class="financial-grid strategy-model-grid">
                <div>
                  <span>{{ strategyUi.modelFit }}</span>
                  <b>{{ Number(pick.strategyAssessment.fitScore).toFixed(1) }}/100</b>
                </div>
                <div v-if="pick.strategyAssessment.horizons">
                  <span>{{ strategyUi.shortTermScore }}</span>
                  <b>{{ Number(pick.strategyAssessment.horizons.shortTermScore).toFixed(1) }}/100</b>
                </div>
                <div v-if="pick.strategyAssessment.horizons">
                  <span>{{ strategyUi.midLongTermScore }}</span>
                  <b>{{ Number(pick.strategyAssessment.horizons.midLongTermScore).toFixed(1) }}/100</b>
                </div>
                <div v-if="pick.strategyAssessment.horizons">
                  <span>{{ strategyUi.stableQualityScore }}</span>
                  <b>{{ Number(pick.strategyAssessment.horizons.qualityCompositeScore).toFixed(1) }}/100</b>
                </div>
                <div v-if="pick.strategyAssessment.horizons">
                  <span>{{ strategyUi.horizonType }}</span>
                  <b>{{ strategyHorizonLabel(pick.strategyAssessment.horizons.classification) }}</b>
                </div>
                <div>
                  <span>{{ strategyUi.baseScore }}</span>
                  <b>{{ Number(pick.strategyAssessment.baseScore).toFixed(1) }}/100</b>
                </div>
                <div>
                  <span>{{ strategyUi.adjustedScore }}</span>
                  <b>{{ Number(pick.strategyAssessment.adjustedScore).toFixed(1) }}/100</b>
                </div>
                <div>
                  <span>{{ strategyUi.sortScore }}</span>
                  <b>{{ Number(pick.strategyAssessment.sortScore).toFixed(1) }}/100</b>
                </div>
              </div>
              <div class="strategy-rule-columns">
                <div>
                  <strong>{{ strategyUi.entryGates }}</strong>
                  <ul>
                    <li v-for="gate in pick.strategyAssessment.gates" :key="gate.key + gate.metric" :class="gate.passed ? 'passed' : 'failed'">
                      {{ strategyCheckLabel(gate, 'gate') }}
                    </li>
                  </ul>
                </div>
                <div>
                  <strong>{{ strategyUi.vetoRules }}</strong>
                  <ul>
                    <li v-for="veto in pick.strategyAssessment.vetoes" :key="veto.key + veto.metric" :class="veto.triggered ? 'triggered' : 'clear'">
                      {{ strategyCheckLabel(veto, 'veto') }}
                    </li>
                  </ul>
                </div>
                <div>
                  <strong>{{ strategyUi.focusItems }}</strong>
                  <ul>
                    <li v-for="item in pick.strategyAssessment.focus" :key="item.key + item.metric">
                      {{ strategyFocusLabel(item) }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <div v-if="pick.market === 'CN' || pick.fundFlow?.available" class="research-panel fund-flow-panel" :class="fundFlowTone(pick.fundFlow)">
              <strong>{{ factorLabel('fundFlow') }} · {{ pick.fundFlow?.available ? pointLabel(fundFlowDecisionPoint(pick.fundFlow, pick.currency)) : fundFlowUnavailableLabel(pick) }}</strong>
              <div v-if="pick.fundFlow?.available" class="financial-grid fund-flow-grid">
                <div v-for="metric in fundFlowRows(pick)" :key="metric.key">
                  <span>{{ metric.label }}</span>
                  <b>{{ metric.value }}</b>
                  <small>{{ t.score }} {{ metric.score }} · {{ pick.fundFlow.source || 'Online' }}</small>
                </div>
              </div>
            </div>

            <div v-if="pick.tPlan" class="research-panel t-plan-panel" :class="pick.tPlan.suitability">
              <strong>{{ tSuitabilityLabel(pick) }} · {{ pointLabel(pick.tPlan.summary) }}</strong>
              <div class="t-zone-grid">
                <div>
                  <span>{{ tPlanFieldLabel('entry') }}</span>
                  <b>{{ priceZoneLabel(pick, pick.tPlan.entryZone) }}</b>
                </div>
                <div>
                  <span>{{ tPlanFieldLabel('takeProfit') }}</span>
                  <b>{{ priceZoneLabel(pick, pick.tPlan.takeProfitZone) }}</b>
                </div>
                <div>
                  <span>{{ tPlanFieldLabel('stop') }}</span>
                  <b>{{ pick.currency }} {{ pick.tPlan.stopLoss }}</b>
                </div>
              </div>
              <div class="research-columns">
                <ul>
                  <li><strong>{{ tPlanFieldLabel('basis') }}</strong></li>
                  <li v-for="item in pick.tPlan.reasons" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
                <ul>
                  <li><strong>{{ tPlanFieldLabel('riskControls') }}</strong></li>
                  <li v-for="item in pick.tPlan.riskControls" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
              </div>
            </div>

            <div v-if="pick.trendAnalysis" class="research-panel trend-panel" :class="pick.trendAnalysis.regime">
              <strong>{{ t.dailyTrend }} · {{ pointLabel(pick.trendAnalysis.summary) }}</strong>
              <div class="financial-grid trend-grid">
                <div v-for="metric in pick.trendAnalysis.metrics" :key="metric.key">
                  <span>{{ trendMetricLabel(metric) }}</span>
                  <b>{{ metric.value }}</b>
                  <small>{{ t.score }} {{ Number(metric.score).toFixed(1) }}</small>
                </div>
              </div>
            </div>

            <div v-if="pick.newsHeatAnalysis" class="research-panel heat-panel">
              <strong>{{ t.newsHeat }} · {{ pointLabel(pick.newsHeatAnalysis.summary) }}</strong>
              <div class="financial-grid heat-grid">
                <div v-for="metric in pick.newsHeatAnalysis.metrics" :key="metric.key">
                  <span>{{ newsHeatMetricLabel(metric) }}</span>
                  <b>{{ metric.value }}</b>
                  <small>{{ t.score }} {{ Number(metric.score).toFixed(1) }}</small>
                </div>
              </div>
            </div>

            <div v-if="pick.scoreBreakdown?.length" class="score-breakdown">
              <strong>{{ t.scoreDetail }}</strong>
              <div v-for="item in pick.scoreBreakdown" :key="item.factor" class="score-line">
                <span>{{ factorLabel(item.factor) }}</span>
                <b>{{ item.score }}</b>
                <small>{{ t.weight }} {{ scoreWeightLabel(item) }} · {{ t.contribution }} {{ item.contribution }}</small>
              </div>
            </div>

            <div v-if="pick.newsAnalysis" class="research-panel">
              <strong>{{ t.newsEvents }} · {{ pointLabel(pick.newsAnalysis.summary) }}</strong>
              <div class="event-list">
                <div v-for="event in pick.newsAnalysis.events" :key="event.title + event.key" class="event-line" :class="event.impact">
                  <span>{{ eventLabel(event) }}</span>
                  <p>{{ event.title }}</p>
                  <small>
                    <b class="event-score">{{ signedScore(event.score) }}</b>
                    · {{ event.source }} · {{ event.ageHours }}{{ t.hoursAgo }}
                    <template v-if="event.evidence"> · {{ event.evidence }}</template>
                  </small>
                </div>
              </div>
            </div>

            <div v-if="pick.financialAnalysis" class="research-panel">
              <strong>{{ financialReviewTitle(pick) }} · {{ pointLabel(pick.financialAnalysis.summary) }}</strong>
              <div class="financial-grid">
                <div v-for="metric in pick.financialAnalysis.metrics" :key="metric.key">
                  <span>{{ financialMetricLabel(metric) }}</span>
                  <b>{{ metric.value }}</b>
                  <small>{{ t.score }} {{ metric.score }}</small>
                </div>
              </div>
            </div>
            </details>
          </article>
        </div>

        <div v-else class="sector-list">
          <article v-if="!loading && !sectors.length && !dataIssues.length" class="empty-card">
            <strong>{{ t.sectorEmptyTitle }}</strong>
            <p>{{ t.sectorEmptyHint }}</p>
          </article>

          <article v-for="sector in sectors" :key="sector.id" class="sector-card" :class="sector.recommendation">
            <div class="sector-heading">
              <div>
                <span class="sector-recommendation">{{ sectorRecommendationLabel(sector.recommendation) }}</span>
                <h3>{{ sector.name }}</h3>
                <p>{{ sectorInsight(sector) }}</p>
              </div>
              <div class="score-pill">
                <span>{{ t.score }}</span>
                <strong>{{ sector.score }}</strong>
              </div>
            </div>

            <div class="metric-row sector-stats">
              <span>{{ t.sectorCount }} {{ sector.count }}</span>
              <span>{{ t.buy }} {{ sectorVerdictCount(sector, 'buy') }}</span>
              <span>{{ t.watch }} {{ sectorVerdictCount(sector, 'watch') }}</span>
              <span>{{ t.sell }} {{ sectorVerdictCount(sector, 'sell') }}</span>
              <span>{{ sectorTLabel(sector) }}</span>
              <span>{{ sectorRiskLabel(sector) }}</span>
              <span>{{ t.confidence }} {{ sector.confidence }}%</span>
              <span>{{ t.sectorMarketMix }} {{ sectorMarketMixLabel(sector) }}</span>
            </div>

            <div class="sector-dimensions">
              <strong>{{ t.sectorDimensions }}</strong>
              <div v-for="factor in weightKeys" :key="`${sector.id}-${factor}`" class="sector-dimension">
                <div>
                  <span>{{ factorLabel(factor) }}</span>
                  <b>{{ sectorMetricValue(sector, factor).toFixed(1) }}</b>
                </div>
                <div class="dimension-bar">
                  <span :style="{ width: sectorMetricWidth(sector, factor) }"></span>
                </div>
              </div>
            </div>

            <div class="sector-constituents">
              <div>
                <strong>{{ t.sectorLeaders }}</strong>
                <p v-for="leader in sector.leaders" :key="`${sector.id}-leader-${leader.symbol}`">
                  <span>{{ leader.symbol }}</span>
                  {{ leader.name }} · {{ leader.score }} · {{ verdictLabel(leader.verdict) }}
                </p>
              </div>
              <div v-if="sector.laggards.length">
                <strong>{{ t.sectorLaggards }}</strong>
                <p v-for="laggard in sector.laggards" :key="`${sector.id}-laggard-${laggard.symbol}`">
                  <span>{{ laggard.symbol }}</span>
                  {{ laggard.name }} · {{ laggard.score }} · {{ verdictLabel(laggard.verdict) }}
                </p>
              </div>
            </div>
          </article>
        </div>
      </section>

      <aside class="signal-panel">
        <div class="signal-heading">
          <h2>{{ t.signalFeed }}</h2>
          <span>{{ signalStatusLabel }}</span>
        </div>
        <div class="signal-scroll">
          <article v-if="loading && !flattenedSignals.length" class="signal-empty">
            <span>{{ t.signalRefreshing }}</span>
          </article>
          <article v-else-if="!flattenedSignals.length" class="signal-empty">
            <span>{{ t.signalEmpty }}</span>
          </article>
          <article v-for="signal in flattenedSignals" :key="`${scanRunId}-${signal.symbol}-${signal.title}`" class="signal-item">
            <div>
              <strong>{{ signal.symbol }}</strong>
              <p><a :href="signal.link" target="_blank" rel="noreferrer">{{ signal.title }}</a></p>
              <p v-if="signal.summary" class="signal-summary">{{ signal.summary }}</p>
            </div>
            <span>{{ signal.source }} · {{ signal.ageHours }}{{ t.hoursAgo }}</span>
          </article>
        </div>
      </aside>
    </section>

    <div v-if="detailPick" class="stock-detail-backdrop" role="dialog" aria-modal="true" :aria-label="strategyUi.stockDetail" @click.self="closeStockDetail">
      <article class="stock-detail-panel">
        <header class="stock-detail-header">
          <div>
            <span class="market-tag">{{ detailPick.market }}</span>
            <h2>{{ detailPick.symbol }} · {{ detailPick.name }}</h2>
            <p>{{ detailPick.currency }} {{ detailPick.price }} · {{ detailPick.change > 0 ? '+' : '' }}{{ detailPick.change }}%</p>
          </div>
          <button class="detail-close" type="button" :aria-label="strategyUi.closeDetail" @click="closeStockDetail">×</button>
        </header>

        <div class="chart-tabs" role="tablist">
          <button type="button" :class="{ active: detailChartTab === 'intraday' }" @click="detailChartTab = 'intraday'">{{ strategyUi.intraday }}</button>
          <button type="button" :class="{ active: detailChartTab === 'daily' }" @click="detailChartTab = 'daily'">{{ strategyUi.dailyK }}</button>
        </div>

        <div v-if="detailChartLoading" class="chart-state">{{ strategyUi.loadingChart }}</div>
        <div v-else-if="detailChartError" class="chart-state error-state">
          <strong>{{ strategyUi.chartUnavailable }}</strong>
          <span>{{ detailChartError }}</span>
        </div>
        <div v-else-if="detailChart" class="chart-content">
          <div class="chart-meta">
            <span>{{ strategyUi.chartSource }} · {{ detailChart.source }}</span>
            <span>{{ strategyUi.updated }} {{ new Date(detailChart.refreshedAt).toLocaleString() }}</span>
            <strong>{{ chartChangeLabel(visibleChartPoints) }}</strong>
          </div>

          <div class="chart-shell">
            <svg
              ref="chartSvgRef"
              viewBox="0 0 720 260"
              role="img"
              :aria-label="`${detailPick.symbol} ${detailChartTab}`"
              @mousemove="updateChartPointer"
              @mouseleave="clearChartPointer"
              @touchstart.prevent="updateChartPointer"
              @touchmove.prevent="updateChartPointer"
            >
              <line v-for="tick in [0, 1, 2, 3, 4]" :key="tick" x1="40" x2="680" :y1="40 + tick * 45" :y2="40 + tick * 45" class="chart-grid-line" />
              <text x="682" y="44" class="chart-scale">{{ chartRange.max.toFixed(2) }}</text>
              <text x="682" y="222" class="chart-scale">{{ chartRange.min.toFixed(2) }}</text>
              <template v-if="detailChartTab === 'intraday'">
                <path v-if="chartAreaPath" :d="chartAreaPath" class="chart-area" />
                <path v-if="chartLinePath" :d="chartLinePath" class="chart-line" />
              </template>
              <template v-else>
                <path v-if="chartMa20Path" :d="chartMa20Path" class="chart-ma ma20" />
                <path v-if="chartMa10Path" :d="chartMa10Path" class="chart-ma ma10" />
                <path v-if="chartMa5Path" :d="chartMa5Path" class="chart-ma ma5" />
                <g v-for="candle in chartCandles" :key="`${candle.x}-${candle.yBody}`" class="chart-candle" :class="{ rising: candle.rising, falling: !candle.rising }">
                  <line :x1="candle.x" :x2="candle.x" :y1="candle.yHigh" :y2="candle.yLow" />
                  <rect :x="candle.x - candle.width / 2" :y="candle.yBody" :width="candle.width" :height="candle.bodyHeight" rx="1.5" />
                </g>
                <g v-for="(point, index) in visibleChartPoints" :key="`${point.time}-limit`">
                  <circle
                    v-if="point.isLimitUp"
                    :cx="chartX(index, Math.max(1, visibleChartPoints.length - 1))"
                    cy="28"
                    r="4.5"
                    class="limit-up-marker"
                  />
                </g>
              </template>
              <g v-if="activeChartPoint" class="chart-crosshair">
                <line :x1="activeChartX" :x2="activeChartX" y1="28" y2="228" />
                <line x1="40" x2="680" :y1="activeChartY" :y2="activeChartY" />
                <circle :cx="activeChartX" :cy="activeChartY" r="4" />
              </g>
            </svg>
            <div v-if="activeChartPoint" class="chart-tooltip" :style="chartTooltipStyle">
              <strong>
                {{ chartPointTimeLabel(activeChartPoint.point) }}
                <template v-if="activeChartPoint.point.isLimitUp"> · {{ strategyUi.limitUp }}</template>
              </strong>
              <div>
                <span v-for="row in chartTooltipRows(activeChartPoint.point)" :key="row[0]">
                  <b>{{ row[0] }}</b>
                  <em>{{ row[1] }}</em>
                </span>
              </div>
            </div>
            <div class="chart-axis">
              <span>{{ chartTickLabel(visibleChartPoints[0]) }}</span>
              <span>{{ chartTickLabel(visibleChartPoints[Math.floor(visibleChartPoints.length / 2)]) }}</span>
              <span>{{ chartTickLabel(visibleChartPoints[visibleChartPoints.length - 1]) }}</span>
            </div>
          </div>
        </div>
      </article>
    </div>

    <div v-if="yogurtSecretOpen" class="yogurt-secret-backdrop" role="dialog" aria-modal="true" aria-labelledby="yogurt-secret-title" @click.self="closeYogurtSecret">
      <article class="yogurt-secret-card">
        <button class="yogurt-secret-close" type="button" aria-label="Close Ugood Days note" @click="closeYogurtSecret">×</button>
        <div class="yogurt-secret-header">
          <img :src="ugoodaysLogo" alt="純粹好食 logo" />
          <div>
            <p>台南優格供應商</p>
            <h2 id="yogurt-secret-title">優格一點點，健康多一點</h2>
            <span>純粹好食 Ugood Days</span>
          </div>
        </div>
        <div class="yogurt-products" aria-label="Products">
          <span>希臘優格</span>
          <span>鮮奶優格</span>
          <span>原味優格飲</span>
        </div>
        <p v-if="yogurtSecretNote" class="yogurt-secret-note">{{ yogurtSecretNote }}</p>
        <p class="yogurt-secret-copy">
          嚴選 Kefir 菌種，搭配 A菌、B菌，精選 8 種乳酸菌，每公克高達 4 億活性乳酸菌。
        </p>
        <dl class="yogurt-secret-info">
          <div>
            <dt>客服專線</dt>
            <dd>06-2609986</dd>
          </div>
          <div>
            <dt>信箱</dt>
            <dd><a href="mailto:ugoodays@gmail.com">ugoodays@gmail.com</a></dd>
          </div>
          <div>
            <dt>地址</dt>
            <dd>台南市東區富農街一段294號（後甲派出所正前方）</dd>
          </div>
          <div>
            <dt>統一編號</dt>
            <dd>60505556</dd>
          </div>
        </dl>
        <div class="yogurt-secret-links">
          <a href="https://www.ugoodays.com/" target="_blank" rel="noreferrer">Website</a>
          <a href="https://www.instagram.com/ugoodays/" target="_blank" rel="noreferrer">Instagram</a>
        </div>
      </article>
    </div>
  </main>
</template>
