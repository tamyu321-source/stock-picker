<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { analyzeStocks, fetchConfig, type AppConfig, type Market, type Pick, type ReasonCode, type Strategy, type StrategyWeights } from './api';
import { messages, strategyText, type Locale } from './i18n';

const locale = ref<Locale>('zh-CN');
const config = ref<AppConfig | null>(null);
const selectedMarkets = ref<Market[]>(['US', 'CN', 'HK', 'SG', 'TW']);
const selectedStrategyId = ref('balanced');
const useCustom = ref(false);
const loading = ref(false);
const error = ref('');
const generatedAt = ref('');
const symbolText = ref('');
const picks = ref<Pick[]>([]);
const dataIssues = ref<Array<{ symbol: string; error: string }>>([]);
const scanInfo = ref<{ auto: boolean; requested: number; succeeded: number; failed: number } | null>(null);

const customWeights = reactive<StrategyWeights>({
  momentum: 24,
  value: 20,
  sentiment: 24,
  risk: 16,
  quality: 16
});

const t = computed(() => messages[locale.value]);
const strategies = computed<Strategy[]>(() => config.value?.strategies ?? []);
const selectedStrategy = computed(() => strategies.value.find((item) => item.id === selectedStrategyId.value));
const marketOptions = computed(() => config.value?.markets ?? []);
const flattenedSignals = computed(() => picks.value.flatMap((pick) => pick.signals.map((signal) => ({ ...signal, symbol: pick.symbol }))).slice(0, 8));
const symbols = computed(() => symbolText.value.split(/[\s,;]+/).map((symbol) => symbol.trim()).filter(Boolean));
const isAutoScan = computed(() => symbols.value.length === 0);
const scanLabel = computed(() => {
  if (!scanInfo.value) return isAutoScan.value ? t.value.autoScan : `${symbols.value.length}`;
  if (locale.value === 'en') return `${scanInfo.value.succeeded}/${scanInfo.value.requested} scanned`;
  if (locale.value === 'zh-CN') return `已扫 ${scanInfo.value.succeeded}/${scanInfo.value.requested}`;
  return `已掃 ${scanInfo.value.succeeded}/${scanInfo.value.requested}`;
});

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

function verdictLabel(verdict: Pick['verdict']) {
  return t.value[verdict];
}

function factorLabel(value: string | number | undefined) {
  const key = String(value ?? '') as keyof StrategyWeights;
  return t.value[key] ?? String(value ?? '');
}

function reasonLabel(reason: ReasonCode) {
  const params = reason.params;
  if (reason.key === 'strongestFactors') {
    if (locale.value === 'en') return `${factorLabel(params.first)} and ${factorLabel(params.second)} are the strongest factors.`;
    if (locale.value === 'zh-CN') return `${factorLabel(params.first)} 与 ${factorLabel(params.second)} 是最强的评分因子。`;
    return `${factorLabel(params.first)} 與 ${factorLabel(params.second)} 是最強的評分因子。`;
  }
  if (reason.key === 'sentimentImpact') {
    const delta = Number(params.delta).toFixed(1);
    if (locale.value === 'en') return `Live crawled sentiment changes the score by ${Number(params.delta) >= 0 ? '+' : ''}${delta} points.`;
    if (locale.value === 'zh-CN') return `实时爬文情绪让评分变化 ${Number(params.delta) >= 0 ? '+' : ''}${delta} 分。`;
    return `即時爬文情緒讓評分變化 ${Number(params.delta) >= 0 ? '+' : ''}${delta} 分。`;
  }
  if (reason.key === 'belowThreshold') {
    if (locale.value === 'en') return `${factorLabel(params.factor)} is below threshold and should be monitored before adding exposure.`;
    if (locale.value === 'zh-CN') return `${factorLabel(params.factor)} 低于门槛，加仓前需要继续观察。`;
    return `${factorLabel(params.factor)} 低於門檻，加碼前需要繼續觀察。`;
  }
  if (reason.key === 'clearsBuyThreshold') {
    if (locale.value === 'en') return 'Composite score clears the buy threshold under the selected strategy.';
    if (locale.value === 'zh-CN') return '综合评分已通过当前策略的买入门槛。';
    return '綜合評分已通過目前策略的買入門檻。';
  }
  if (reason.key === 'rankedTopOpportunity') {
    if (locale.value === 'en') return `Ranked #${params.rank} within this scan, making it a relative buy candidate.`;
    if (locale.value === 'zh-CN') return `本次扫描排名第 ${params.rank}，属于相对更值得关注的买入候选。`;
    return `本次掃描排名第 ${params.rank}，屬於相對更值得關注的買入候選。`;
  }
  if (locale.value === 'en') return 'Composite score is not strong enough for a high-conviction entry.';
  if (locale.value === 'zh-CN') return '综合评分暂不足以支持高信心进场。';
  return '綜合評分暫不足以支持高信心進場。';
}

function reasonLabels(pick: Pick) {
  return pick.reasonCodes?.length ? pick.reasonCodes.map(reasonLabel) : pick.reasons;
}

function sectorLabel(pick: Pick) {
  return pick.sector && pick.sector !== 'Unknown' ? pick.sector : t.value.sectorUnavailable;
}

async function runAnalysis() {
  loading.value = true;
  error.value = '';
  try {
    const result = await analyzeStocks({
      markets: selectedMarkets.value.length ? selectedMarkets.value : ['US', 'CN', 'HK', 'SG', 'TW'],
      symbols: symbols.value,
      strategyId: useCustom.value ? undefined : selectedStrategyId.value,
      customWeights: useCustom.value ? { ...customWeights } : undefined
    });
    picks.value = result.picks;
    dataIssues.value = result.errors;
    scanInfo.value = result.scan ?? null;
    generatedAt.value = new Date(result.generatedAt).toLocaleString();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Unknown error';
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  config.value = await fetchConfig();
  await runAnalysis();
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

      <div class="locale-switcher" aria-label="Language">
        <button :class="{ active: locale === 'en' }" @click="locale = 'en'"><span class="flag flag-uk"></span>EN</button>
        <button :class="{ active: locale === 'zh-CN' }" @click="locale = 'zh-CN'"><span class="flag flag-cn"></span>简</button>
        <button :class="{ active: locale === 'zh-TW' }" @click="locale = 'zh-TW'"><span class="flag flag-tw"></span>繁</button>
      </div>
    </header>

    <section class="status-strip">
      <div>
        <span>{{ t.backendStatus }}</span>
        <strong>{{ t.liveData }}</strong>
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

    <section class="workspace">
      <aside class="control-panel">
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
              <span>{{ market.label }}</span>
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
          <textarea v-model="symbolText" rows="5" spellcheck="false"></textarea>
          <p class="strategy-copy">{{ t.symbolsHint }}</p>
        </div>

        <button class="primary-action" :disabled="loading" @click="runAnalysis">
          {{ loading ? t.loading : t.analyze }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </aside>

      <section class="results">
        <div class="section-row">
          <h2>{{ t.topIdeas }}</h2>
          <button class="ghost" :disabled="loading" @click="runAnalysis">{{ t.refresh }}</button>
        </div>

        <div class="pick-list">
          <article v-if="dataIssues.length" class="issue-card">
            <strong>{{ t.failures }}</strong>
            <p v-for="issue in dataIssues" :key="issue.symbol">{{ issue.symbol }}: {{ issue.error }}</p>
          </article>

          <article v-for="pick in picks" :key="pick.symbol" class="pick-card" :class="pick.verdict">
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
              <span>{{ pick.currency }} {{ pick.price }} · {{ pick.change > 0 ? '+' : '' }}{{ pick.change }}%</span>
            </div>

            <div class="reason-block">
              <strong>{{ t.reasonTitle }}</strong>
              <ul>
                <li v-for="reason in reasonLabels(pick)" :key="reason">{{ reason }}</li>
              </ul>
            </div>
          </article>
        </div>
      </section>

      <aside class="signal-panel">
        <h2>{{ t.signalFeed }}</h2>
        <article v-for="signal in flattenedSignals" :key="`${signal.symbol}-${signal.title}`" class="signal-item">
          <div>
            <strong>{{ signal.symbol }}</strong>
            <p><a :href="signal.link" target="_blank" rel="noreferrer">{{ signal.title }}</a></p>
            <p v-if="signal.summary" class="signal-summary">{{ signal.summary }}</p>
          </div>
          <span>{{ signal.source }} · {{ signal.ageHours }}{{ t.hoursAgo }}</span>
        </article>
      </aside>
    </section>
  </main>
</template>
