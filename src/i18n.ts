export type Locale = 'en' | 'zh-CN' | 'zh-TW';

type MessageKey =
  | 'appName'
  | 'subtitle'
  | 'marketCoverage'
  | 'strategy'
  | 'defaultStrategy'
  | 'symbols'
  | 'symbolsHint'
  | 'symbolsBlank'
  | 'autoScan'
  | 'customWeights'
  | 'analyze'
  | 'refresh'
  | 'topIdeas'
  | 'signalFeed'
  | 'score'
  | 'confidence'
  | 'buy'
  | 'watch'
  | 'sell'
  | 'momentum'
  | 'value'
  | 'sentiment'
  | 'risk'
  | 'quality'
  | 'riskTolerance'
  | 'source'
  | 'credibility'
  | 'hoursAgo'
  | 'loading'
  | 'openSource'
  | 'backendStatus'
  | 'allMarkets'
  | 'reasonTitle'
  | 'scoreDetail'
  | 'positiveReasons'
  | 'negativeReasons'
  | 'watchItems'
  | 'actionPlan'
  | 'newsEvents'
  | 'financialReview'
  | 'riskControls'
  | 'weight'
  | 'contribution'
  | 'liveData'
  | 'failures'
  | 'sectorUnavailable';

export const messages: Record<Locale, Record<MessageKey, string>> = {
  en: {
    appName: 'Open Stock Picker',
    subtitle: 'Multilingual AI stock screening for public-market research.',
    marketCoverage: 'Market coverage',
    strategy: 'Strategy',
    defaultStrategy: 'Default strategy',
    symbols: 'Ticker watchlist',
    symbolsHint: 'Leave blank to scan selected markets from local finance news sources. Or use tickers or names such as AAPL, Tencent, D05.SI, 台積電, 贵州茅台, 600519.SS.',
    symbolsBlank: 'Blank means automatic market scan',
    autoScan: 'Automatic market scan',
    customWeights: 'Custom weights',
    analyze: 'Run analysis',
    refresh: 'Refresh',
    topIdeas: 'AI-ranked ideas',
    signalFeed: 'Crawled signal feed',
    score: 'Score',
    confidence: 'Confidence',
    buy: 'Worth buying',
    watch: 'Watch closely',
    sell: 'Exit risk',
    momentum: 'Momentum',
    value: 'Value',
    sentiment: 'News sentiment',
    risk: 'Risk control',
    quality: 'Quality',
    riskTolerance: 'Risk tolerance',
    source: 'Source',
    credibility: 'Credibility',
    hoursAgo: 'h ago',
    loading: 'Analyzing market signals',
    openSource: 'Open-source live research workflow',
    backendStatus: 'Python AI scoring API',
    allMarkets: 'China, Hong Kong, Singapore, United States, Taiwan',
    reasonTitle: 'Decision factors',
    scoreDetail: '100-point score detail',
    positiveReasons: 'Supports investment',
    negativeReasons: 'Exit / risk reasons',
    watchItems: 'What to watch',
    actionPlan: 'Suggested action',
    newsEvents: 'News event analysis',
    financialReview: 'Financial report check',
    riskControls: 'Risk controls',
    weight: 'Weight',
    contribution: 'Contribution',
    liveData: 'Live market data and RSS crawling',
    failures: 'Data issues',
    sectorUnavailable: 'Sector unavailable'
  },
  'zh-CN': {
    appName: '开源智能选股器',
    subtitle: '支持多市场、多策略、新闻情绪权重的 AI 选股研究网页。',
    marketCoverage: '市场范围',
    strategy: '策略',
    defaultStrategy: '默认策略',
    symbols: '股票代码清单',
    symbolsHint: '留空时系统会优先从所选市场的当地财经新闻源自动扫描；也可以输入代码或名称，例如 AAPL、腾讯、D05.SI、台積電、贵州茅台、600519.SS。',
    symbolsBlank: '留空即自动市场扫描',
    autoScan: '自动市场扫描',
    customWeights: '自定义权重',
    analyze: '开始分析',
    refresh: '刷新',
    topIdeas: 'AI 排名结果',
    signalFeed: '爬文信号',
    score: '评分',
    confidence: '置信度',
    buy: '值得投资',
    watch: '重点观察',
    sell: '需要抛出',
    momentum: '动能',
    value: '估值',
    sentiment: '新闻情绪',
    risk: '风险控制',
    quality: '基本面质量',
    riskTolerance: '风险承受度',
    source: '来源',
    credibility: '可信度',
    hoursAgo: '小时前',
    loading: '正在分析市场信号',
    openSource: '开源真实研究工作流',
    backendStatus: 'Python AI 评分 API',
    allMarkets: '中国、香港、新加坡、美国、台湾',
    reasonTitle: '判断依据',
    scoreDetail: '100 分评分明细',
    positiveReasons: '支持投资的理由',
    negativeReasons: '需要抛售/风险理由',
    watchItems: '重点观察什么',
    actionPlan: '建议操作',
    newsEvents: '新闻事件解析',
    financialReview: '财报/基本面检查',
    riskControls: '风险控制',
    weight: '权重',
    contribution: '贡献分',
    liveData: '真实行情与 RSS 爬文',
    failures: '数据问题',
    sectorUnavailable: '行业资料暂缺'
  },
  'zh-TW': {
    appName: '開源智慧選股器',
    subtitle: '支援多市場、多策略、新聞情緒權重的 AI 選股研究網頁。',
    marketCoverage: '市場範圍',
    strategy: '策略',
    defaultStrategy: '預設策略',
    symbols: '股票代碼清單',
    symbolsHint: '留空時系統會優先從所選市場的當地財經新聞源自動掃描；也可以輸入代碼或名稱，例如 AAPL、騰訊、D05.SI、台積電、貴州茅台、600519.SS。',
    symbolsBlank: '留空即自動市場掃描',
    autoScan: '自動市場掃描',
    customWeights: '自訂權重',
    analyze: '開始分析',
    refresh: '刷新',
    topIdeas: 'AI 排名結果',
    signalFeed: '爬文訊號',
    score: '評分',
    confidence: '信心度',
    buy: '值得投資',
    watch: '重點觀察',
    sell: '需要拋出',
    momentum: '動能',
    value: '估值',
    sentiment: '新聞情緒',
    risk: '風險控制',
    quality: '基本面品質',
    riskTolerance: '風險承受度',
    source: '來源',
    credibility: '可信度',
    hoursAgo: '小時前',
    loading: '正在分析市場訊號',
    openSource: '開源真實研究工作流',
    backendStatus: 'Python AI 評分 API',
    allMarkets: '中國、香港、新加坡、美國、台灣',
    reasonTitle: '判斷依據',
    scoreDetail: '100 分評分明細',
    positiveReasons: '支持投資的理由',
    negativeReasons: '需要拋出/風險理由',
    watchItems: '重點觀察什麼',
    actionPlan: '建議操作',
    newsEvents: '新聞事件解析',
    financialReview: '財報/基本面檢查',
    riskControls: '風險控制',
    weight: '權重',
    contribution: '貢獻分',
    liveData: '真實行情與 RSS 爬文',
    failures: '資料問題',
    sectorUnavailable: '產業資料暫缺'
  }
};

export const strategyText: Record<Locale, Record<string, { name: string; description: string }>> = {
  en: {
    balanced: {
      name: 'Balanced AI Core',
      description: 'Balances trend, valuation, news sentiment, downside risk, and quality.'
    },
    growth: {
      name: 'Growth Momentum',
      description: 'Favors accelerating growth narratives, price momentum, and positive institutional coverage.'
    },
    defensive: {
      name: 'Defensive Value',
      description: 'Favors lower drawdown, stronger cash flow, cheaper valuation, and stable signal quality.'
    }
  },
  'zh-CN': {
    balanced: {
      name: '均衡 AI 核心',
      description: '综合趋势、估值、新闻情绪、下行风险和基本面质量。'
    },
    growth: {
      name: '成长动能',
      description: '偏重成长叙事、价格动能和正向机构/媒体覆盖。'
    },
    defensive: {
      name: '防守价值',
      description: '偏重低回撤、现金流、便宜估值和稳定信号质量。'
    }
  },
  'zh-TW': {
    balanced: {
      name: '均衡 AI 核心',
      description: '綜合趨勢、估值、新聞情緒、下行風險和基本面品質。'
    },
    growth: {
      name: '成長動能',
      description: '偏重成長敘事、價格動能和正向機構/媒體覆蓋。'
    },
    defensive: {
      name: '防守價值',
      description: '偏重低回撤、現金流、便宜估值和穩定訊號品質。'
    }
  }
};
