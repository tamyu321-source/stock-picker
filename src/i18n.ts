export type Locale = 'en' | 'zh-CN' | 'zh-TW' | 'nan-TW' | 'ja' | 'ko';

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
  | 'saveScan'
  | 'savedScan'
  | 'exportMarkdown'
  | 'exportJson'
  | 'savedScans'
  | 'loadScan'
  | 'deleteSavedScan'
  | 'noSavedScans'
  | 'topIdeas'
  | 'stockView'
  | 'sectorView'
  | 'sectorIdeas'
  | 'sectorEmptyTitle'
  | 'sectorEmptyHint'
  | 'sectorCount'
  | 'sectorRecommendation'
  | 'sectorDimensions'
  | 'sectorLeaders'
  | 'sectorLaggards'
  | 'sectorMarketMix'
  | 'overweight'
  | 'sectorNeutral'
  | 'underweight'
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
  | 'cancelScan'
  | 'scanCancelled'
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
  | 'dataMode'
  | 'liveBackend'
  | 'demoPreview'
  | 'liveBackendDetail'
  | 'demoPreviewDetail'
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
    symbolsPlaceholder: 'Optional examples: AAPL, Tencent, 7203.T, 005930.KS, 台積電, 贵州茅台',
    autoScan: 'Automatic market scan',
    customWeights: 'Custom weights',
    analyze: 'Scan for quality stocks',
    refresh: 'Refresh',
    saveScan: 'Save scan',
    savedScan: 'Saved',
    exportMarkdown: 'Markdown',
    exportJson: 'JSON',
    savedScans: 'Saved scans',
    loadScan: 'Load',
    deleteSavedScan: 'Delete',
    noSavedScans: 'Saved scans will appear here after you save a result.',
    topIdeas: 'AI-ranked investment candidates',
    stockView: 'Stocks',
    sectorView: 'Sectors',
    sectorIdeas: 'Multi-dimensional sector advice',
    sectorEmptyTitle: 'No sector analysis yet',
    sectorEmptyHint: 'Run a scan first; sectors will be ranked from the same scored candidates.',
    sectorCount: 'Constituents',
    sectorRecommendation: 'Recommendation',
    sectorDimensions: 'Sector dimensions',
    sectorLeaders: 'Leaders',
    sectorLaggards: 'Risk drag',
    sectorMarketMix: 'Market mix',
    overweight: 'Overweight',
    sectorNeutral: 'Neutral',
    underweight: 'Underweight',
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
    cancelScan: 'Cancel scan',
    scanCancelled: 'Scan cancelled. Partial picks, if any, remain visible.',
    openSource: 'Live no-code stock discovery workflow',
    backendStatus: 'Python AI scoring API',
    allMarkets: 'China, Hong Kong, Japan, South Korea, Singapore, United States, Taiwan',
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
    dataMode: 'Data mode',
    liveBackend: 'Live backend',
    demoPreview: 'Static demo',
    liveBackendDetail: 'Connected to the Python API',
    demoPreviewDetail: 'Sample data for hosted preview',
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
    symbolsPlaceholder: '可选示例：AAPL、腾讯、7203.T、005930.KS、台積電、贵州茅台',
    autoScan: '自动市场扫描',
    customWeights: '自定义权重',
    analyze: '扫描优质投资标的',
    refresh: '刷新',
    saveScan: '保存扫描',
    savedScan: '已保存',
    exportMarkdown: 'Markdown',
    exportJson: 'JSON',
    savedScans: '已保存扫描',
    loadScan: '载入',
    deleteSavedScan: '删除',
    noSavedScans: '保存结果后，会显示在这里。',
    topIdeas: 'AI 排名投资候选',
    stockView: '个股',
    sectorView: '板块',
    sectorIdeas: '多维度板块投资建议',
    sectorEmptyTitle: '还没有板块分析',
    sectorEmptyHint: '先运行一次扫描，系统会基于同一批评分结果聚合各板块建议。',
    sectorCount: '成分股',
    sectorRecommendation: '投资建议',
    sectorDimensions: '板块维度',
    sectorLeaders: '领先标的',
    sectorLaggards: '拖累风险',
    sectorMarketMix: '市场分布',
    overweight: '建议超配',
    sectorNeutral: '中性配置',
    underweight: '建议低配',
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
    cancelScan: '取消扫描',
    scanCancelled: '扫描已取消；已出现的候选会保留在页面上。',
    openSource: '无需代码输入的实时选股流程',
    backendStatus: 'Python AI 评分 API',
    allMarkets: '中国、香港、日本、韩国、新加坡、美国、台湾',
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
    dataMode: '数据模式',
    liveBackend: '实时后端',
    demoPreview: '静态演示',
    liveBackendDetail: '已连接 Python API',
    demoPreviewDetail: '托管预览使用示例数据',
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
    symbolsPlaceholder: '可選範例：AAPL、騰訊、7203.T、005930.KS、台積電、貴州茅台',
    autoScan: '自動市場掃描',
    customWeights: '自訂權重',
    analyze: '掃描優質投資標的',
    refresh: '刷新',
    saveScan: '保存掃描',
    savedScan: '已保存',
    exportMarkdown: 'Markdown',
    exportJson: 'JSON',
    savedScans: '已保存掃描',
    loadScan: '載入',
    deleteSavedScan: '刪除',
    noSavedScans: '保存結果後，會顯示在這裡。',
    topIdeas: 'AI 排名投資候選',
    stockView: '個股',
    sectorView: '板塊',
    sectorIdeas: '多維度板塊投資建議',
    sectorEmptyTitle: '還沒有板塊分析',
    sectorEmptyHint: '先執行一次掃描，系統會基於同一批評分結果聚合各板塊建議。',
    sectorCount: '成分股',
    sectorRecommendation: '投資建議',
    sectorDimensions: '板塊維度',
    sectorLeaders: '領先標的',
    sectorLaggards: '拖累風險',
    sectorMarketMix: '市場分布',
    overweight: '建議超配',
    sectorNeutral: '中性配置',
    underweight: '建議低配',
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
    cancelScan: '取消掃描',
    scanCancelled: '掃描已取消；已出現的候選會保留在頁面上。',
    openSource: '無需代碼輸入的即時選股流程',
    backendStatus: 'Python AI 評分 API',
    allMarkets: '中國、香港、日本、韓國、新加坡、美國、台灣',
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
    dataMode: '資料模式',
    liveBackend: '即時後端',
    demoPreview: '靜態示範',
    liveBackendDetail: '已連線 Python API',
    demoPreviewDetail: '托管預覽使用範例資料',
    liveData: '真實行情與 RSS 爬文',
    failures: '資料問題',
    sectorUnavailable: '產業資料暫缺'
  },
  'nan-TW': {
    appName: 'Open Stock Picker',
    subtitle: '毋免先輸入股票代號，直接掃市場，替咱揣出較適合做投資研究的好標的。',
    marketCoverage: '市場範圍',
    strategy: '投資策略',
    defaultStrategy: '預設策略',
    symbols: '直接掃市場',
    symbolsHint: '可選：輸入 ticker 或公司名，掃描範圍會較細；留空就是直接掃市場。',
    symbolsBlank: '毋免先輸入股票代號',
    scanPurpose: '掃所選市場，照品質、估值、動能、風險佮最新新聞排序，揣出較適合投資的候選股。',
    optionalSymbols: '可選：限定指定股票',
    symbolsPlaceholder: 'AAPL, TSMC, 7203.T, 005930.KS, 2330.TW',
    autoScan: '自動掃市場',
    customWeights: '家己調權重',
    analyze: '掃好投資標的',
    refresh: '閣再刷新',
    saveScan: '保存掃描',
    savedScan: '已保存',
    exportMarkdown: 'Markdown',
    exportJson: 'JSON',
    savedScans: '已保存掃描',
    loadScan: '載入',
    deleteSavedScan: '刪除',
    noSavedScans: '保存結果了後，會顯示佇遮。',
    topIdeas: 'AI 排名投資候選',
    stockView: '個股',
    sectorView: '板塊',
    sectorIdeas: '多維度板塊投資建議',
    sectorEmptyTitle: '這馬猶未有板塊分析',
    sectorEmptyHint: '先掃一擺，系統會照同一批分數聚合各板塊建議。',
    sectorCount: '成分股',
    sectorRecommendation: '投資建議',
    sectorDimensions: '板塊維度',
    sectorLeaders: '領先標的',
    sectorLaggards: '拖累風險',
    sectorMarketMix: '市場分布',
    overweight: '建議超配',
    sectorNeutral: '中性配置',
    underweight: '建議低配',
    emptyTitle: '這馬猶未開始掃描',
    emptyHint: '先看左爿選項，確認好就會使開始掃描。',
    signalFeed: '爬文訊號',
    signalRefreshing: '這輪新聞咧重新爬',
    signalUpdated: '這輪新聞已更新',
    signalEmpty: '這輪猶未有新聞訊號',
    score: '分數',
    confidence: '信心度',
    buy: '會使投資',
    watch: '重點觀察',
    sell: '退出風險',
    momentum: '動能',
    value: '估值',
    sentiment: '新聞氣口',
    risk: '風險控制',
    quality: '基本面品質',
    riskTolerance: '風險承受度',
    source: '來源',
    credibility: '可信度',
    hoursAgo: ' 小時前',
    loading: '咧掃投資候選',
    cancelScan: '取消掃描',
    scanCancelled: '掃描已取消；已出現的候選會留佇頁面頂懸。',
    openSource: '免寫程式的即時揣股流程',
    backendStatus: 'Python AI 評分 API',
    allMarkets: '中國、香港、日本、韓國、新加坡、美國、臺灣',
    reasonTitle: '判斷依據',
    scoreDetail: '100 分明細',
    positiveReasons: '支持投資的理由',
    negativeReasons: '退出 / 風險理由',
    watchItems: '愛觀察啥物',
    actionPlan: '建議做法',
    newsEvents: '新聞事件解析',
    financialReview: '財報 / 基本面檢查',
    riskControls: '風險控制',
    weight: '權重',
    contribution: '貢獻分',
    dataMode: '資料模式',
    liveBackend: '即時後端',
    demoPreview: '靜態示範',
    liveBackendDetail: '已連線 Python API',
    demoPreviewDetail: '線頂預覽用範例資料',
    liveData: '即時行情佮 RSS 爬文',
    failures: '資料問題',
    sectorUnavailable: '產業資料暫缺'
  },
  ja: {
    appName: 'オープン株式ピッカー',
    subtitle: '銘柄コードを入力しなくても、市場を直接スキャンして投資研究に向く高品質な株を探します。',
    marketCoverage: '対象市場',
    strategy: '戦略',
    defaultStrategy: '標準戦略',
    symbols: '直接市場スキャン',
    symbolsHint: '任意指定です。ティッカーや社名を入力するとスキャン範囲を絞り、空欄なら市場全体を探索します。',
    symbolsBlank: '銘柄コード入力は不要',
    scanPurpose: '選択した市場を品質、バリュエーション、モメンタム、リスク、最新ニュースで評価し、投資候補を順位付けします。',
    optionalSymbols: '任意: 特定銘柄に絞る',
    symbolsPlaceholder: '例: AAPL, Toyota, 7203.T, Samsung, 005930.KS, 台積電',
    autoScan: '自動市場スキャン',
    customWeights: 'カスタム配分',
    analyze: '高品質株をスキャン',
    refresh: '更新',
    saveScan: '保存',
    savedScan: '保存済み',
    exportMarkdown: 'Markdown',
    exportJson: 'JSON',
    savedScans: '保存済みスキャン',
    loadScan: '読み込み',
    deleteSavedScan: '削除',
    noSavedScans: '結果を保存するとここに表示されます。',
    topIdeas: 'AI ランク投資候補',
    stockView: '個別株',
    sectorView: 'セクター',
    sectorIdeas: '多面的なセクター助言',
    sectorEmptyTitle: 'まだセクター分析はありません',
    sectorEmptyHint: '先にスキャンを実行すると、同じ評価結果からセクター順位を作成します。',
    sectorCount: '構成銘柄',
    sectorRecommendation: '推奨',
    sectorDimensions: 'セクター指標',
    sectorLeaders: '上位銘柄',
    sectorLaggards: 'リスク要因',
    sectorMarketMix: '市場構成',
    overweight: '強めに配分',
    sectorNeutral: '中立',
    underweight: '控えめに配分',
    emptyTitle: 'まだスキャンしていません',
    emptyHint: '左側の保存済み設定を確認してから、スキャンを開始してください。',
    signalFeed: 'クロール済みシグナル',
    signalRefreshing: 'このスキャンのニュースを再取得中',
    signalUpdated: 'ニュース更新済み',
    signalEmpty: 'まだニュースシグナルはありません',
    score: 'スコア',
    confidence: '信頼度',
    buy: '買い候補',
    watch: '注視',
    sell: '売却リスク',
    momentum: 'モメンタム',
    value: 'バリュー',
    sentiment: 'ニュース心理',
    risk: 'リスク管理',
    quality: '品質',
    riskTolerance: 'リスク許容度',
    source: 'ソース',
    credibility: '信頼性',
    hoursAgo: '時間前',
    loading: '投資候補をスキャン中',
    cancelScan: 'キャンセル',
    scanCancelled: 'スキャンをキャンセルしました。表示済みの候補は残ります。',
    openSource: 'コード入力不要のリアルタイム株式探索',
    backendStatus: 'Python AI スコアリング API',
    allMarkets: '中国、香港、日本、韓国、シンガポール、米国、台湾',
    reasonTitle: '判断材料',
    scoreDetail: '100 点スコア内訳',
    positiveReasons: '投資を支える理由',
    negativeReasons: '売却 / リスク理由',
    watchItems: '注視ポイント',
    actionPlan: '提案アクション',
    newsEvents: 'ニュースイベント分析',
    financialReview: '決算 / ファンダメンタル確認',
    riskControls: 'リスク管理',
    weight: '重み',
    contribution: '寄与',
    dataMode: 'データモード',
    liveBackend: 'ライブバックエンド',
    demoPreview: '静的デモ',
    liveBackendDetail: 'Python API に接続中',
    demoPreviewDetail: 'ホスト版プレビュー用サンプルデータ',
    liveData: 'リアルタイム市場データと RSS クロール',
    failures: 'データ問題',
    sectorUnavailable: 'セクター情報なし'
  },
  ko: {
    appName: '오픈 주식 피커',
    subtitle: '종목 코드를 먼저 입력하지 않아도 시장을 직접 스캔해 투자 검토에 적합한 우량주를 찾습니다.',
    marketCoverage: '시장 범위',
    strategy: '전략',
    defaultStrategy: '기본 전략',
    symbols: '직접 시장 스캔',
    symbolsHint: '선택 입력입니다. 티커나 회사명을 넣으면 스캔 범위를 좁히고, 비워 두면 시장 전체를 탐색합니다.',
    symbolsBlank: '종목 코드 입력 불필요',
    scanPurpose: '선택한 시장을 품질, 밸류에이션, 모멘텀, 리스크, 최신 뉴스로 평가해 투자 후보를 순위화합니다.',
    optionalSymbols: '선택: 특정 종목만 스캔',
    symbolsPlaceholder: '예: AAPL, Toyota, 7203.T, Samsung, 005930.KS, 台積電',
    autoScan: '자동 시장 스캔',
    customWeights: '사용자 가중치',
    analyze: '우량 투자 후보 스캔',
    refresh: '새로고침',
    saveScan: '스캔 저장',
    savedScan: '저장됨',
    exportMarkdown: 'Markdown',
    exportJson: 'JSON',
    savedScans: '저장된 스캔',
    loadScan: '불러오기',
    deleteSavedScan: '삭제',
    noSavedScans: '결과를 저장하면 여기에 표시됩니다.',
    topIdeas: 'AI 순위 투자 후보',
    stockView: '종목',
    sectorView: '섹터',
    sectorIdeas: '다차원 섹터 조언',
    sectorEmptyTitle: '아직 섹터 분석이 없습니다',
    sectorEmptyHint: '먼저 스캔을 실행하면 같은 평가 결과로 섹터 순위를 만듭니다.',
    sectorCount: '구성 종목',
    sectorRecommendation: '추천',
    sectorDimensions: '섹터 지표',
    sectorLeaders: '상위 종목',
    sectorLaggards: '리스크 요인',
    sectorMarketMix: '시장 구성',
    overweight: '비중 확대',
    sectorNeutral: '중립',
    underweight: '비중 축소',
    emptyTitle: '아직 스캔하지 않았습니다',
    emptyHint: '왼쪽의 저장된 옵션을 확인한 뒤 스캔을 시작하세요.',
    signalFeed: '수집된 시그널',
    signalRefreshing: '이번 스캔의 뉴스를 다시 수집 중',
    signalUpdated: '뉴스 업데이트 완료',
    signalEmpty: '아직 뉴스 시그널이 없습니다',
    score: '점수',
    confidence: '신뢰도',
    buy: '매수 후보',
    watch: '관찰',
    sell: '매도 리스크',
    momentum: '모멘텀',
    value: '가치',
    sentiment: '뉴스 심리',
    risk: '리스크 관리',
    quality: '품질',
    riskTolerance: '리스크 허용도',
    source: '출처',
    credibility: '신뢰도',
    hoursAgo: '시간 전',
    loading: '투자 후보 스캔 중',
    cancelScan: '스캔 취소',
    scanCancelled: '스캔을 취소했습니다. 이미 표시된 후보는 유지됩니다.',
    openSource: '코드 입력 없는 실시간 주식 탐색',
    backendStatus: 'Python AI 점수 API',
    allMarkets: '중국, 홍콩, 일본, 한국, 싱가포르, 미국, 대만',
    reasonTitle: '판단 근거',
    scoreDetail: '100점 점수 상세',
    positiveReasons: '투자를 지지하는 이유',
    negativeReasons: '매도 / 리스크 이유',
    watchItems: '관찰할 항목',
    actionPlan: '제안 행동',
    newsEvents: '뉴스 이벤트 분석',
    financialReview: '실적 / 펀더멘털 점검',
    riskControls: '리스크 관리',
    weight: '가중치',
    contribution: '기여도',
    dataMode: '데이터 모드',
    liveBackend: '실시간 백엔드',
    demoPreview: '정적 데모',
    liveBackendDetail: 'Python API에 연결됨',
    demoPreviewDetail: '호스팅 미리보기용 샘플 데이터',
    liveData: '실시간 시장 데이터와 RSS 수집',
    failures: '데이터 문제',
    sectorUnavailable: '섹터 정보 없음'
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
      description: '綜合趨勢、估值、新聞氣口、下行風險佮基本面品質。'
    },
    growth: {
      name: '成長動能',
      description: '較看重成長題材、價格動能佮正向機構 / 媒體報導。'
    },
    defensive: {
      name: '防守價值',
      description: '較看重低回撤、現金流、便宜估值佮穩定訊號品質。'
    }
  },
  ja: {
    balanced: {
      name: 'バランス AI コア',
      description: 'トレンド、バリュエーション、ニュース心理、下落リスク、品質を総合します。'
    },
    growth: {
      name: '成長モメンタム',
      description: '成長ストーリー、価格モメンタム、前向きな機関投資家/メディア評価を重視します。'
    },
    defensive: {
      name: 'ディフェンシブ・バリュー',
      description: '低いドローダウン、強いキャッシュフロー、割安な評価、安定したシグナルを重視します。'
    }
  },
  ko: {
    balanced: {
      name: '균형 AI 코어',
      description: '추세, 밸류에이션, 뉴스 심리, 하방 리스크, 품질을 종합합니다.'
    },
    growth: {
      name: '성장 모멘텀',
      description: '성장 서사, 가격 모멘텀, 긍정적인 기관/미디어 평가를 중시합니다.'
    },
    defensive: {
      name: '방어적 가치',
      description: '낮은 낙폭, 강한 현금흐름, 저렴한 밸류에이션, 안정적인 시그널을 중시합니다.'
    }
  }
};
