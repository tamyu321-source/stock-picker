<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { analyzeStocksStream, currentDataMode, fetchConfig, importPortfolioFile, type AnalysisStreamEvent, type AppConfig, type DecisionPoint, type FinancialMetric, type HoldingAction, type HoldingNote, type Market, type NewsEvent, type Pick, type PortfolioAnalysis, type PortfolioImportResponse, type ReasonCode, type SectorAnalysis, type SectorRecommendation, type Strategy, type StrategyWeights } from './api';
import { messages, strategyText, type Locale } from './i18n';
import ugoodaysLogo from './assets/ugoodays-logo.jpg';

type StandardLocale = Exclude<Locale, 'nan-TW'>;
type LocalizedText = Partial<Record<StandardLocale, string>> & { en: string };
type YogurtSoundCue = 'appear' | 'tap';
type ResultMarketFilter = 'all' | Market;
type ResultVerdictFilter = 'all' | Pick['verdict'] | 't';
type DataMode = ReturnType<typeof currentDataMode>;
type DataIssue = { symbol: string; error: string };
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
  scanInfo: { auto: boolean; requested: number; succeeded: number; failed: number } | null;
  portfolio: PortfolioAnalysis | PortfolioImportResponse | null;
};

const locale = ref<Locale>('en');
const languageMenuOpen = ref(false);
const languageMenuRef = ref<HTMLElement | null>(null);
const config = ref<AppConfig | null>(null);
const selectedMarkets = ref<Market[]>(['US', 'CN', 'HK', 'JP', 'KR', 'SG', 'TW']);
const selectedStrategyId = ref('balanced');
const useCustom = ref(false);
const loading = ref(false);
const error = ref('');
const generatedAt = ref('');
const symbolText = ref('');
const picks = ref<Pick[]>([]);
const sectors = ref<SectorAnalysis[]>([]);
const activeView = ref<'stocks' | 'sectors'>('stocks');
const resultMarketFilter = ref<ResultMarketFilter>('all');
const resultVerdictFilter = ref<ResultVerdictFilter>('all');
const dataIssues = ref<DataIssue[]>([]);
const scanInfo = ref<{ auto: boolean; requested: number; succeeded: number; failed: number } | null>(null);
const loadingStartedAt = ref(0);
const loadingElapsedSeconds = ref(0);
const loadingStepIndex = ref(0);
const scanRunId = ref(0);
const signalRefreshStartedAt = ref('');
const dataMode = ref(currentDataMode());
const savedScans = ref<SavedScan[]>([]);
const portfolioFileInput = ref<HTMLInputElement | null>(null);
const importedPortfolio = ref<PortfolioImportResponse | null>(null);
const analysisPortfolio = ref<PortfolioAnalysis | null>(null);
const importingPortfolio = ref(false);
const portfolioImportError = ref('');
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
const defaultMarkets: Market[] = ['US', 'CN', 'HK', 'JP', 'KR', 'SG', 'TW'];
const weightKeys: Array<keyof StrategyWeights> = ['momentum', 'value', 'sentiment', 'risk', 'quality'];
const verdictFilterOptions: ResultVerdictFilter[] = ['all', 'buy', 't', 'watch', 'sell'];
const languageOptions: Array<{ id: Locale; label: string; shortLabel: string; flagClass: string }> = [
  { id: 'en', label: 'English', shortLabel: 'EN', flagClass: 'flag-uk' },
  { id: 'zh-CN', label: '简体中文', shortLabel: '简', flagClass: 'flag-cn' },
  { id: 'zh-TW', label: '繁體中文', shortLabel: '繁', flagClass: 'flag-tw' },
  { id: 'nan-TW', label: '臺語', shortLabel: '臺', flagClass: 'flag-nan' },
  { id: 'ja', label: '日本語', shortLabel: '日', flagClass: 'flag-jp' },
  { id: 'ko', label: '한국어', shortLabel: '한', flagClass: 'flag-kr' }
];

type PersistedSettings = {
  locale?: Locale;
  selectedMarkets?: Market[];
  selectedStrategyId?: string;
  useCustom?: boolean;
  customWeights?: Partial<StrategyWeights>;
  symbolText?: string;
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
const activeLanguageOption = computed(() => languageOptions.find((option) => option.id === locale.value) ?? languageOptions[0]);
const strategies = computed<Strategy[]>(() => config.value?.strategies ?? []);
const selectedStrategy = computed(() => strategies.value.find((item) => item.id === selectedStrategyId.value));
const marketOptions = computed(() => config.value?.markets ?? []);
const filteredPicks = computed(() => picks.value.filter((pick) => {
  const marketMatches = resultMarketFilter.value === 'all' || pick.market === resultMarketFilter.value;
  const verdictMatches = resultVerdictFilter.value === 'all'
    || (resultVerdictFilter.value === 't' ? pick.tPlan?.suitability === 'candidate' : pick.verdict === resultVerdictFilter.value);
  return marketMatches && verdictMatches;
}));
const flattenedSignals = computed(() => filteredPicks.value.flatMap((pick) => pick.signals.map((signal) => ({ ...signal, symbol: pick.symbol }))));
const resultFiltersActive = computed(() => resultMarketFilter.value !== 'all' || resultVerdictFilter.value !== 'all');
const isDemoDataMode = computed(() => dataMode.value === 'demo');
const dataModeLabel = computed(() => (isDemoDataMode.value ? t.value.demoPreview : t.value.liveBackend));
const dataModeDescription = computed(() => (isDemoDataMode.value ? t.value.demoPreviewDetail : t.value.liveBackendDetail));
const canSaveScan = computed(() => picks.value.length > 0 && !loading.value);
const activePortfolio = computed(() => analysisPortfolio.value ?? importedPortfolio.value);
const portfolioSymbols = computed(() => importedPortfolio.value?.symbols ?? []);
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
    if (activePortfolio.value?.recognizedCount) return portfolioScanLabel(activePortfolio.value.recognizedCount);
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

function normalizeWeight(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? Math.min(40, Math.max(0, value)) : null;
}

function persistSettings() {
  const settings: PersistedSettings = {
    locale: locale.value,
    selectedMarkets: selectedMarkets.value,
    selectedStrategyId: selectedStrategyId.value,
    useCustom: useCustom.value,
    customWeights: { ...customWeights },
    symbolText: symbolText.value
  };
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // Ignore storage failures so the scanner remains usable in private or restricted contexts.
  }
}

function refreshDataMode() {
  dataMode.value = currentDataMode();
}

function restoreSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return;

    const settings = JSON.parse(raw) as PersistedSettings;
    if (isLocale(settings.locale)) {
      locale.value = settings.locale;
    }
    if (Array.isArray(settings.selectedMarkets)) {
      selectedMarkets.value = settings.selectedMarkets.filter(isMarket);
    }
    if (typeof settings.selectedStrategyId === 'string' && settings.selectedStrategyId) {
      selectedStrategyId.value = settings.selectedStrategyId;
    }
    if (typeof settings.useCustom === 'boolean') {
      useCustom.value = settings.useCustom;
    }
    if (settings.customWeights && typeof settings.customWeights === 'object') {
      weightKeys.forEach((key) => {
        const value = normalizeWeight(settings.customWeights?.[key]);
        if (value !== null) {
          customWeights[key] = value;
        }
      });
    }
    if (typeof settings.symbolText === 'string') {
      symbolText.value = settings.symbolText;
    }
  } catch {
    try {
      localStorage.removeItem(SETTINGS_STORAGE_KEY);
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
    const raw = localStorage.getItem(SAVED_SCANS_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return;
    savedScans.value = parsed
      .filter((item): item is SavedScan => item && typeof item.id === 'string' && Array.isArray(item.picks))
      .slice(0, SAVED_SCAN_LIMIT);
  } catch {
    try {
      localStorage.removeItem(SAVED_SCANS_STORAGE_KEY);
    } catch {
      // Ignore storage failures so export and scanning still work.
    }
  }
}

function persistSavedScans() {
  try {
    localStorage.setItem(SAVED_SCANS_STORAGE_KEY, JSON.stringify(savedScans.value.slice(0, SAVED_SCAN_LIMIT)));
  } catch {
    // Ignore storage failures so export and scanning still work.
  }
}

function normalizeStrategySelection() {
  if (!strategies.value.length) return;
  if (!strategies.value.some((strategy) => strategy.id === selectedStrategyId.value)) {
    selectedStrategyId.value = strategies.value[0].id;
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

function marketLabel(market: Market) {
  return marketLabels[locale.value][market] ?? market;
}

function verdictLabel(verdict: Pick['verdict']) {
  return t.value[verdict];
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

function portfolioImportButtonLabel() {
  return importingPortfolio.value ? portfolioText().importing : portfolioText().chooseFile;
}

function clearPortfolioLabel() {
  return portfolioText().clear;
}

function portfolioReadyLabel(portfolio: PortfolioImportResponse | PortfolioAnalysis) {
  return portfolioText().ready(portfolio.recognizedCount, portfolio.ignoredRows || 0);
}

function portfolioCurrency() {
  return 'CNY';
}

function moneyLabel(value: number | null | undefined, currency = portfolioCurrency()) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${currency} ${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function percentLabel(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(1)}%`;
}

function signedMoneyLabel(value: number | null | undefined, currency = portfolioCurrency()) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${Number(value) > 0 ? '+' : ''}${moneyLabel(value, currency)}`;
}

function holdingActionLabel(action: HoldingAction) {
  return portfolioText().actions[action];
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
    symbolText.value = imported.symbols.join(', ');
    const importedMarkets = [...new Set(imported.positions.map((position) => position.market).filter(isMarket))];
    if (importedMarkets.length) selectedMarkets.value = importedMarkets;
    resultMarketFilter.value = 'all';
    resultVerdictFilter.value = 'all';
    activeView.value = 'stocks';
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
    lines.push(`- Verdict: ${verdictLabel(pick.verdict)}`);
    lines.push(`- Score: ${pick.score}/100`);
    lines.push(`- Confidence: ${pick.confidence}%`);
    lines.push(`- Price: ${pick.currency} ${pick.price} (${pick.change > 0 ? '+' : ''}${pick.change}%)`);
    if (pick.decision) lines.push(`- Decision: ${markdownLine(pointLabel(pick.decision.summary))}`);
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

function scoreWeightLabel(item: { weight: number; baseWeight?: number; available?: boolean }) {
  const effective = Number(item.weight).toFixed(1);
  const base = item.baseWeight === undefined ? effective : Number(item.baseWeight).toFixed(1);
  if (item.available === false) return `0.0% (${base}%)`;
  return base !== effective ? `${base}% -> ${effective}%` : `${effective}%`;
}

function predictionScoreLabel(kind: 'opportunity' | 'downside' | 'setup' | 'pullback' | 't', pick: Pick) {
  const value = kind === 'opportunity'
    ? pick.opportunityScore
    : kind === 'downside'
      ? pick.downsideRiskScore
      : kind === 'setup'
        ? pick.breakoutSetupScore
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
    fiftyTwoWeekPosition: { en: '52-week position', 'zh-CN': '52 周区间位置', 'zh-TW': '52 週區間位置', ja: '52週レンジ位置', ko: '52주 구간 위치' }
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
}

async function runAnalysis() {
  if (loading.value) return;
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
      portfolio: importedPortfolio.value ?? undefined
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
    symbolText: symbolText.value
  }),
  persistSettings,
  { deep: true }
);

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick);
  document.addEventListener('keydown', handleDocumentKeydown);
  restoreSettings();
  restoreSavedScans();
  config.value = await fetchConfig();
  refreshDataMode();
  normalizeStrategySelection();
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
  document.removeEventListener('keydown', handleDocumentKeydown);
  stopAppTimers();
});
</script>

<template>
  <main class="shell">
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
          <div class="panel-section">
            <h2>{{ t.marketCoverage }}</h2>
            <div class="market-grid">
              <button
                v-for="market in marketOptions"
                :key="market.id"
                :class="{ active: selectedMarkets.includes(market.id) }"
                @click="toggleMarket(market.id)"
              >
                <strong>{{ market.id }}</strong>
                <span>{{ marketLabel(market.id) }}</span>
              </button>
            </div>
          </div>

          <div class="panel-section">
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

            <div class="weight-list">
              <label v-for="(_, key) in customWeights" :key="key">
                <span>{{ t[key] }}</span>
                <input v-model.number="customWeights[key]" :disabled="!useCustom" type="range" min="0" max="40" />
                <strong>{{ customWeights[key] }}</strong>
              </label>
            </div>
          </div>

          <div class="panel-section">
            <div class="section-row">
              <h2>{{ t.symbols }}</h2>
              <span class="mode-pill">{{ scanLabel }}</span>
            </div>
            <div class="scan-purpose">
              <strong>{{ t.symbolsBlank }}</strong>
              <span>{{ t.scanPurpose }}</span>
            </div>
            <div class="portfolio-import">
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
              <p v-if="portfolioImportError" class="portfolio-error">{{ portfolioImportError }}</p>
            </div>
            <details class="optional-symbols" @toggle="keepOptionalSymbolsVisible">
              <summary>{{ t.optionalSymbols }}</summary>
              <textarea v-model="symbolText" rows="4" spellcheck="false" :placeholder="t.symbolsPlaceholder"></textarea>
              <p class="strategy-copy">{{ t.symbolsHint }}</p>
            </details>
          </div>
        </div>

        <div class="control-actions">
          <div class="action-row">
            <button class="primary-action" type="button" :disabled="loading" @click="runAnalysis">
              <span v-if="loading" class="spinner" aria-hidden="true"></span>
              {{ loading ? t.loading : t.analyze }}
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
          <h2>{{ activeView === 'stocks' ? t.topIdeas : t.sectorIdeas }}</h2>
          <div class="result-actions">
            <div class="view-toggle" role="tablist" aria-label="Result view">
              <button :class="{ active: activeView === 'stocks' }" type="button" @click="activeView = 'stocks'">
                {{ t.stockView }} <span>{{ filteredPicks.length }}</span>
              </button>
              <button :class="{ active: activeView === 'sectors' }" type="button" @click="activeView = 'sectors'">
                {{ t.sectorView }} <span>{{ sectors.length }}</span>
              </button>
            </div>
            <button class="ghost" :disabled="!canSaveScan" type="button" @click="saveCurrentScan">{{ t.saveScan }}</button>
            <button class="ghost" :disabled="!canSaveScan" type="button" @click="exportMarkdown">{{ t.exportMarkdown }}</button>
            <button class="ghost" :disabled="!canSaveScan" type="button" @click="exportJson">{{ t.exportJson }}</button>
            <button class="ghost" :disabled="loading" @click="runAnalysis">{{ t.refresh }}</button>
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

        <div v-if="activeView === 'stocks' && (picks.length || resultFiltersActive)" class="result-filter-bar">
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

          <article v-for="pick in filteredPicks" :key="pick.symbol" class="pick-card" :class="pick.verdict">
            <div class="pick-heading">
              <div>
                <span class="market-tag">{{ pick.market }}</span>
                <h3>{{ pick.symbol }} · {{ pick.name }}</h3>
                <p>{{ sectorLabel(pick) }}</p>
              </div>
              <div class="score-pill">
                <span>{{ t.score }}</span>
                <strong>{{ pick.score }}</strong>
              </div>
            </div>

            <div class="metric-row">
              <span>{{ verdictLabel(pick.verdict) }}</span>
              <span>{{ t.confidence }} {{ pick.confidence }}%</span>
              <span>{{ predictionScoreLabel('opportunity', pick) }}</span>
              <span>{{ predictionScoreLabel('setup', pick) }}</span>
              <span>{{ predictionScoreLabel('downside', pick) }}</span>
              <span>{{ predictionScoreLabel('pullback', pick) }}</span>
              <span v-if="pick.tPlan" class="t-score-chip" :class="pick.tPlan.suitability">{{ predictionScoreLabel('t', pick) }} · {{ tSuitabilityLabel(pick) }}</span>
              <span>{{ pick.currency }} {{ pick.price }} · {{ pick.change > 0 ? '+' : '' }}{{ pick.change }}%</span>
            </div>

            <div v-if="pick.holding && pick.holdingAnalysis" class="research-panel holding-panel" :class="pick.holdingAnalysis.action">
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
              </div>
              <ul class="holding-notes">
                <li v-for="note in pick.holdingAnalysis.notes" :key="note.key + JSON.stringify(note.params)" :class="note.severity">
                  {{ holdingNoteLabel(note) }}
                </li>
              </ul>
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

            <div class="reason-block">
              <strong>{{ pick.decision ? pointLabel(pick.decision.summary) : t.reasonTitle }}</strong>
            </div>

            <div v-if="pick.scoreBreakdown?.length" class="score-breakdown">
              <strong>{{ t.scoreDetail }}</strong>
              <div v-for="item in pick.scoreBreakdown" :key="item.factor" class="score-line">
                <span>{{ factorLabel(item.factor) }}</span>
                <b>{{ item.score }}</b>
                <small>{{ t.weight }} {{ scoreWeightLabel(item) }} · {{ t.contribution }} {{ item.contribution }}</small>
              </div>
            </div>

            <div class="reason-block">
              <strong>{{ t.reasonTitle }}</strong>
              <ul>
                <li v-for="reason in reasonLabels(pick)" :key="reason">{{ reason }}</li>
              </ul>
            </div>

            <div v-if="pick.decision" class="decision-grid">
              <div>
                <strong>{{ t.positiveReasons }}</strong>
                <ul>
                  <li v-for="item in pick.decision.positives" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
              </div>
              <div>
                <strong>{{ t.negativeReasons }}</strong>
                <ul>
                  <li v-for="item in pick.decision.negatives" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
              </div>
              <div>
                <strong>{{ t.watchItems }}</strong>
                <ul>
                  <li v-for="item in pick.decision.watchItems" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
              </div>
            </div>

            <div v-if="pick.actionPlan" class="research-panel action-panel">
              <strong>{{ t.actionPlan }} · {{ pointLabel(pick.actionPlan.summary) }}</strong>
              <div class="research-columns">
                <ul>
                  <li v-for="item in pick.actionPlan.steps" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
                <ul>
                  <li v-for="item in pick.actionPlan.watchItems" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
                <ul>
                  <li v-for="item in pick.actionPlan.riskControls" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                </ul>
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
              <strong>{{ t.financialReview }} · {{ pointLabel(pick.financialAnalysis.summary) }}</strong>
              <div class="financial-grid">
                <div v-for="metric in pick.financialAnalysis.metrics" :key="metric.key">
                  <span>{{ financialMetricLabel(metric) }}</span>
                  <b>{{ metric.value }}</b>
                  <small>{{ t.score }} {{ metric.score }}</small>
                </div>
              </div>
              <div class="decision-grid compact">
                <div>
                  <strong>{{ t.positiveReasons }}</strong>
                  <ul>
                    <li v-for="item in pick.financialAnalysis.positives" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                  </ul>
                </div>
                <div>
                  <strong>{{ t.negativeReasons }}</strong>
                  <ul>
                    <li v-for="item in pick.financialAnalysis.negatives" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                  </ul>
                </div>
                <div>
                  <strong>{{ t.watchItems }}</strong>
                  <ul>
                    <li v-for="item in pick.financialAnalysis.watchItems" :key="item.key + JSON.stringify(item.params)">{{ pointLabel(item) }}</li>
                  </ul>
                </div>
              </div>
            </div>
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
