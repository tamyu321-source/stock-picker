export type Locale = 'en' | 'zh-CN' | 'zh-TW' | 'nan-TW';

type MessageKey =
  | 'appName'
  | 'subtitle'
  | 'marketCoverage'
  | 'strategy'
  | 'defaultStrategy'
  | 'symbols'
  | 'symbolsHint'
  | 'symbolsBlank'
  | 'scanPurpose'
  | 'optionalSymbols'
  | 'symbolsPlaceholder'
  | 'autoScan'
  | 'customWeights'
  | 'analyze'
  | 'refresh'
  | 'topIdeas'
  | 'emptyTitle'
  | 'emptyHint'
  | 'signalFeed'
  | 'signalRefreshing'
  | 'signalUpdated'
  | 'signalEmpty'
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
    subtitle: 'Direct market scanning to find suitable, higher-quality stocks for investment research.',
    marketCoverage: 'Market coverage',
    strategy: 'Strategy',
    defaultStrategy: 'Default strategy',
    symbols: 'Direct market scan',
    symbolsHint: 'Optional only: enter tickers or names to narrow the scan. Leave it empty for the main no-code market scan.',
    symbolsBlank: 'No ticker input required',
    scanPurpose: 'Scan selected markets and rank investable candidates by quality, valuation, momentum, risk, and fresh news.',
    optionalSymbols: 'Optional: narrow to specific stocks',
    symbolsPlaceholder: 'Optional examples: AAPL, Tencent, D05.SI, 台積電, 贵州茅台, 600519.SS',
    autoScan: 'Automatic market scan',
    customWeights: 'Custom weights',
    analyze: 'Scan for quality stocks',
    refresh: 'Refresh',
    topIdeas: 'AI-ranked investment candidates',
    emptyTitle: 'No scan has run yet',
    emptyHint: 'Review the saved options on the left, then start a scan when you are ready.',
    signalFeed: 'Crawled signal feed',
    signalRefreshing: 'Refreshing this scan\'s news crawl',
    signalUpdated: 'News refreshed',
    signalEmpty: 'No current crawl signals yet',
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
    loading: 'Scanning investment candidates',
    openSource: 'Live no-code stock discovery workflow',
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
    subtitle: '不需要先输入股票代码，直接扫描市场，寻找适合投资的优质股票。',
    marketCoverage: '市场范围',
    strategy: '策略',
    defaultStrategy: '默认策略',
    symbols: '直接市场扫描',
    symbolsHint: '这里只是可选过滤：输入代码或名称会缩小扫描范围；留空才是主流程，系统会直接扫描市场。',
    symbolsBlank: '无需输入股票代码',
    scanPurpose: '扫描所选市场，并按质量、估值、动能、风险与最新新闻排序，找出更适合投资的候选股。',
    optionalSymbols: '可选：只扫描指定股票',
    symbolsPlaceholder: '可选示例：AAPL、腾讯、D05.SI、台積電、贵州茅台、600519.SS',
    autoScan: '自动市场扫描',
    customWeights: '自定义权重',
    analyze: '扫描优质投资标的',
    refresh: '刷新',
    topIdeas: 'AI 排名投资候选',
    emptyTitle: '还没有开始扫描',
    emptyHint: '左侧会恢复上次保存的选项，确认后再手动点击扫描即可。',
    signalFeed: '爬文信号',
    signalRefreshing: '正在重新爬取本轮新闻',
    signalUpdated: '本轮新闻已更新',
    signalEmpty: '本轮还没有新闻信号',
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
    loading: '正在扫描投资候选',
    openSource: '无需代码输入的实时选股流程',
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
    subtitle: '不需要先輸入股票代碼，直接掃描市場，尋找適合投資的優質股票。',
    marketCoverage: '市場範圍',
    strategy: '策略',
    defaultStrategy: '預設策略',
    symbols: '直接市場掃描',
    symbolsHint: '這裡只是可選篩選：輸入代碼或名稱會縮小掃描範圍；留空才是主流程，系統會直接掃描市場。',
    symbolsBlank: '無需輸入股票代碼',
    scanPurpose: '掃描所選市場，並按品質、估值、動能、風險與最新新聞排序，找出更適合投資的候選股。',
    optionalSymbols: '可選：只掃描指定股票',
    symbolsPlaceholder: '可選範例：AAPL、騰訊、D05.SI、台積電、貴州茅台、600519.SS',
    autoScan: '自動市場掃描',
    customWeights: '自訂權重',
    analyze: '掃描優質投資標的',
    refresh: '刷新',
    topIdeas: 'AI 排名投資候選',
    emptyTitle: '還沒有開始掃描',
    emptyHint: '左側會恢復上次保存的選項，確認後再手動點擊掃描即可。',
    signalFeed: '爬文訊號',
    signalRefreshing: '正在重新爬取本輪新聞',
    signalUpdated: '本輪新聞已更新',
    signalEmpty: '本輪還沒有新聞訊號',
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
    loading: '正在掃描投資候選',
    openSource: '無需代碼輸入的即時選股流程',
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
  },
  'nan-TW': {
    appName: 'Open Stock Picker',
    subtitle: '免先輸入股票代碼，直接掃描市場，揣 ㄘㄨㄝ˫ 出較適合投資的優質股票。',
    marketCoverage: '市場範圍',
    strategy: '策略 ㄑㄧㄚㄅ ㄌㄧㄛㄍ',
    defaultStrategy: '預設策略',
    symbols: '直接市場掃描',
    symbolsHint: '可選：輸入 ticker 或公司名，掃描範圍會變較細 ㄎㄚˋ ㄙㄨㄝ˪；留空就是直接掃描市場。',
    symbolsBlank: '毋免 ㄅㄍˊ 輸入股票代碼',
    scanPurpose: '掃描所選市場，照品質、估值、動能、風險佮 ㄍㄚㄅ 最新新聞排序。',
    optionalSymbols: '可選：限定指定股票',
    symbolsPlaceholder: 'AAPL, TSMC, D05.SI, 2330.TW, 600519.SS',
    autoScan: '自動市場掃描',
    customWeights: '自訂權重',
    analyze: '掃描好股 ㄏㄛˋ ㄍㄛˋ',
    refresh: '刷新 ㄒㄧㄣ ㄎㄧˋ',
    topIdeas: 'AI 排名投資候選',
    emptyTitle: '猶未 ㄧㄚˋ ㄅㄨㄝ˫ 開始掃描',
    emptyHint: '看一下左側選項，確認後就開始掃描 ㄙㄠˋ。',
    signalFeed: '爬文訊號',
    signalRefreshing: '重新爬本輪新聞中',
    signalUpdated: '本輪新聞已更新',
    signalEmpty: '本輪猶未有新聞訊號',
    score: '分數',
    confidence: '信心度',
    buy: '會使 ㄟ˫ ㄙㄞˋ 買',
    watch: '重點觀察',
    sell: '退出風險',
    momentum: '動能',
    value: '估值',
    sentiment: '新聞情緒',
    risk: '風險控制',
    quality: '品質',
    riskTolerance: '風險承受度',
    source: '來源',
    credibility: '可信度',
    hoursAgo: ' 小時前',
    loading: '正在掃描投資候選',
    openSource: '免寫 code 的即時選股流程',
    backendStatus: 'Python AI 評分 API',
    allMarkets: '中國、香港、新加坡、美國、台灣 ㄉㄞˊ ㄨㄢˊ',
    reasonTitle: '判斷因素',
    scoreDetail: '100 分明細',
    positiveReasons: '支持投資的理由',
    negativeReasons: '退出 / 風險理由',
    watchItems: '重點看啥物 ㄒㄧㄚˋ ㄇㄧㆷ',
    actionPlan: '建議操作',
    newsEvents: '新聞事件解析',
    financialReview: '財報 / 基本面檢查',
    riskControls: '風險控制',
    weight: '權重',
    contribution: '貢獻分',
    liveData: '即時行情佮 ㄍㄚㄅ RSS 爬文',
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
  },
  'nan-TW': {
    balanced: {
      name: '均衡 AI 核心',
      description: '綜合趨勢、估值、新聞情緒、下行風險佮 ㄍㄚㄅ 基本面品質。'
    },
    growth: {
      name: '成長動能',
      description: '偏重成長敘事、價格動能佮 ㄍㄚㄅ 正向機構 / 媒體覆蓋。'
    },
    defensive: {
      name: '防守價值',
      description: '偏重低回撤、現金流、便宜估值佮 ㄍㄚㄅ 穩定訊號品質。'
    }
  }
};
