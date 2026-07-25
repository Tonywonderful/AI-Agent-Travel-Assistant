<script setup lang="ts">
import { computed, ref, watch } from "vue";

import AmapTripMap from "../components/AmapTripMap.vue";
import { fetchWeatherForecast, saveTrip } from "../services/api";
import type { Itinerary, WeatherForecastResponse } from "../types";
import {
  clearWeatherInflight,
  getCachedWeather,
  getWeatherInflight,
  hasAutoSavedTrip,
  markTripAutoSaved,
  setCachedWeather,
  setWeatherInflight,
} from "../utils/clientCache";

const props = withDefaults(
  defineProps<{
    itinerary: Itinerary | null;
    /** 当前是否展示结果页（用于保活时触发地图 resize） */
    active?: boolean;
  }>(),
  { active: true }
);

defineEmits<{
  backHome: [];
  updated: [itinerary: Itinerary];
}>();

const weatherLoading = ref(false);
const weatherError = ref("");
const weather = ref<WeatherForecastResponse | null>(null);
const failedImageKeys = ref(new Set<string>());
const lastWeatherCity = ref("");

function formatShortDate(dateText?: string | null): string {
  if (!dateText) return "待定";
  const parts = dateText.split("-");
  return parts.length !== 3 ? dateText : `${parts[1]}-${parts[2]}`;
}

function formatWeatherDate(dateText?: string | null, week?: string | null): string {
  const weekdayMap: Record<string, string> = {
    "1": "周一",
    "2": "周二",
    "3": "周三",
    "4": "周四",
    "5": "周五",
    "6": "周六",
    "7": "周日",
  };
  const weekday = week ? weekdayMap[week] || `周${week}` : "";
  return [formatShortDate(dateText), weekday].filter(Boolean).join(" ");
}

function weatherIcon(description?: string | null): string {
  const text = description || "";
  if (text.includes("雷")) return "⛈️";
  if (text.includes("雪")) return "🌨️";
  if (text.includes("雨")) return "🌧️";
  if (text.includes("晴") && text.includes("云")) return "🌤️";
  if (text.includes("晴")) return "☀️";
  if (text.includes("雾") || text.includes("霾")) return "🌫️";
  if (text.includes("云")) return "⛅";
  return "☁️";
}

const dateRange = computed(() => {
  const days = props.itinerary?.days || [];
  if (!days.length) return "待定";
  return `${days[0]?.date || "待定"} 至 ${days[days.length - 1]?.date || "待定"}`;
});

const budgetItems = computed(() => {
  if (!props.itinerary) return [];
  const budget = props.itinerary.budget_breakdown;
  return [
    { icon: "♟", type: "景点门票", detail: "景点与活动门票", value: budget.tickets, tone: "blue" },
    { icon: "▣", type: "酒店住宿", detail: "全程住宿安排", value: budget.hotel, tone: "indigo" },
    { icon: "♜", type: "餐饮费用", detail: "每日正餐与特色餐饮", value: budget.meals, tone: "orange" },
    { icon: "◆", type: "交通费用", detail: "市内与行程交通", value: budget.transport, tone: "green" },
  ];
});

function tokenCount(value?: number | null): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

const tokenUsageSummary = computed(() => {
  const usage = props.itinerary?.token_usage;
  if (!usage) return null;

  const rawRows = [
    {
      label: "查询改写",
      prompt: tokenCount(usage.rewrite_prompt_tokens),
      completion: tokenCount(usage.rewrite_completion_tokens),
    },
    {
      label: "向量检索",
      prompt: tokenCount(usage.embedding_prompt_tokens),
      completion: tokenCount(usage.embedding_completion_tokens),
    },
    {
      label: "结果重排",
      prompt: tokenCount(usage.rerank_prompt_tokens),
      completion: tokenCount(usage.rerank_completion_tokens),
    },
    {
      label: "行程生成",
      prompt: tokenCount(usage.planner_prompt_tokens),
      completion: tokenCount(usage.planner_completion_tokens),
    },
  ];
  const prompt = rawRows.reduce((sum, row) => sum + row.prompt, 0);
  const completion = rawRows.reduce((sum, row) => sum + row.completion, 0);
  const total = prompt + completion;

  if (total <= 0) return null;

  return {
    total,
    prompt,
    completion,
    rows: rawRows.map((row) => ({
      ...row,
      percent: ((row.prompt + row.completion) / total) * 100,
    })),
  };
});

const dayBudgetItems = computed(() => {
  if (!props.itinerary) return [];
  return props.itinerary.days.map((day) => {
    const tickets = day.spots.reduce((sum, spot) => sum + (spot.estimated_cost ?? 0), 0);
    const meals = day.meals.reduce((sum, meal) => sum + (meal.estimated_cost ?? 0), 0);
    const transport = day.transport.reduce((sum, item) => sum + (item.estimated_cost ?? 0), 0);
    const hotel = day.hotel?.estimated_cost ?? 0;
    return {
      key: day.day_index,
      date: day.date,
      title: `第 ${day.day_index} 天`,
      subtitle: day.theme || "自由行程",
      tickets,
      meals,
      transport,
      hotel,
      total: tickets + meals + transport + hotel,
    };
  });
});

const maxDayBudget = computed(() =>
  Math.max(...dayBudgetItems.value.map((item) => item.total), 1)
);

function costBarWidth(value: number): string {
  return `${Math.max((value / maxDayBudget.value) * 100, value > 0 ? 1.5 : 0)}%`;
}

const mapPoints = computed(() => {
  if (!props.itinerary) return [];
  return props.itinerary.days.flatMap((day) =>
    day.spots.map((spot) => ({
      key: `${day.day_index}-${spot.name}`,
      dayIndex: day.day_index,
      date: day.date || "待定",
      theme: day.theme || "",
      name: spot.name,
      address: spot.address || spot.location || "待补充",
      latitude: spot.latitude,
      longitude: spot.longitude,
      poiId: spot.poi_id,
      imageUrl: spot.image_url,
      description: spot.description || "暂无说明",
    }))
  );
});

const technicalTipKeywords = ["LLM", "RAG", "LangChain", "Chroma", "演示", "测试", "规则", "模型", "源码"];
const rainWeatherKeywords = ["雨", "阵雨", "雷阵雨", "小雨", "中雨", "大雨"];
const sunnyTipKeywords = ["防晒", "太阳", "日照", "晒"];

const weatherText = computed(() => {
  if (!weather.value) return "";
  return weather.value.days
    .map((day) => `${day.day_weather || ""}${day.night_weather || ""}`)
    .join(" ");
});

const hasRainyWeather = computed(() =>
  rainWeatherKeywords.some((keyword) => weatherText.value.includes(keyword))
);

const displayTips = computed(() => {
  if (!props.itinerary) return [];
  const tips = props.itinerary.tips
    .map((tip) => tip.trim())
    .filter(Boolean)
    .filter((tip) => !technicalTipKeywords.some((keyword) => tip.includes(keyword)));
  const weatherAware = hasRainyWeather.value
    ? tips.filter((tip) => !sunnyTipKeywords.some((keyword) => tip.includes(keyword)))
    : tips;
  if (hasRainyWeather.value) {
    weatherAware.push("天气可能有雨，建议随身带伞或轻便雨衣。");
    weatherAware.push("阴雨天路面湿滑，建议穿防滑鞋。");
  }
  return Array.from(new Set(weatherAware));
});

function markImageAsFailed(pointKey: string) {
  failedImageKeys.value = new Set([...failedImageKeys.value, pointKey]);
}

async function loadWeather(force = false) {
  const city = props.itinerary?.destination?.trim() || "";
  if (!city) {
    weather.value = null;
    lastWeatherCity.value = "";
    weatherError.value = "";
    weatherLoading.value = false;
    return;
  }

  // 同城且已有数据：切页/保活场景不再请求
  if (!force && lastWeatherCity.value === city && weather.value) {
    return;
  }

  const cached = !force ? getCachedWeather(city) : null;
  if (cached) {
    weather.value = cached;
    lastWeatherCity.value = city;
    weatherError.value = "";
    weatherLoading.value = false;
    return;
  }

  weatherLoading.value = true;
  weatherError.value = "";
  try {
    let request = getWeatherInflight(city);
    if (!request) {
      request = fetchWeatherForecast(city).then(
        (data) => {
          clearWeatherInflight(city);
          return data;
        },
        (error) => {
          clearWeatherInflight(city);
          throw error;
        }
      );
      setWeatherInflight(city, request);
    }
    const data = await request;
    // 请求返回时目的地可能已切换
    if (props.itinerary?.destination?.trim() !== city) return;
    weather.value = data;
    lastWeatherCity.value = city;
    setCachedWeather(city, data);
  } catch {
    if (props.itinerary?.destination?.trim() !== city) return;
    weather.value = null;
    lastWeatherCity.value = "";
    weatherError.value = "天气信息加载失败。";
  }

  if (props.itinerary?.destination?.trim() === city) {
    weatherLoading.value = false;
  }
}

async function autoSave(itinerary?: Itinerary | null) {
  if (!itinerary?.trip_id || hasAutoSavedTrip(itinerary.trip_id)) return;
  try {
    await saveTrip({ ...itinerary, tips: displayTips.value });
    markTripAutoSaved(itinerary.trip_id);
  } catch {
    // 自动保存失败时保持静默，避免打断用户查看结果。
  }
}

watch(
  () => props.itinerary?.destination,
  () => {
    void loadWeather();
  },
  { immediate: true }
);

watch(
  () => props.itinerary?.trip_id,
  (tripId) => {
    if (tripId) void autoSave(props.itinerary);
  },
  { immediate: true }
);
</script>

<template>
  <section v-if="itinerary" class="result-page">
    <div class="result-content">
      <article class="result-card overview-card">
        <header class="overview-title">
          <h1>{{ itinerary.destination }} {{ itinerary.days.length }} 日游旅游规划</h1>
          <span class="status-badge"><i></i>已完成</span>
        </header>

        <div class="overview-grid">
          <div class="overview-meta">
            <div class="meta-row"><span>行程 ID</span><strong>{{ itinerary.trip_id }}</strong></div>
            <div class="meta-row"><span>起止日期</span><strong>{{ dateRange }}</strong></div>
            <div class="meta-row"><span>行程天数</span><strong>共 {{ itinerary.days.length }} 天</strong></div>
            <div class="meta-row"><span>预估预算</span><strong>¥{{ itinerary.estimated_budget.toFixed(0) }}</strong></div>
          </div>

          <div class="overview-copy">
            <h2>行程概要</h2>
            <p>{{ itinerary.summary || "这是一份为你量身规划的旅行行程。" }}</p>
          </div>

          <div class="overview-tips">
            <h2>旅行提示</h2>
            <ul v-if="displayTips.length">
              <li v-for="(tip, index) in displayTips.slice(0, 5)" :key="tip">
                <span :class="`tip-dot tip-dot--${index % 4}`">{{ ["◉", "◇", "◆", "●"][index % 4] }}</span>
                <span>{{ tip }}</span>
              </li>
            </ul>
            <p v-else class="empty-copy">暂无额外提示</p>
          </div>
        </div>
      </article>

      <div :class="['summary-grid', { 'summary-grid--single': !tokenUsageSummary }]">
        <article class="result-card data-card">
          <h2 class="section-title">预算明细 <small>（预估）</small></h2>
          <div class="table-wrap">
            <table class="data-table budget-table">
              <thead>
                <tr><th>项目</th><th>明细</th><th>预估费用（元）</th></tr>
              </thead>
              <tbody>
                <tr v-for="item in budgetItems" :key="item.type">
                  <td>
                    <span :class="['budget-icon', `budget-icon--${item.tone}`]">{{ item.icon }}</span>
                    {{ item.type }}
                  </td>
                  <td>{{ item.detail }}</td>
                  <td class="number-cell">{{ item.value.toFixed(0) }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr><td colspan="2">预估总费用</td><td>¥{{ itinerary.estimated_budget.toFixed(0) }}</td></tr>
              </tfoot>
            </table>
          </div>
        </article>

        <article v-if="tokenUsageSummary" class="result-card data-card">
          <h2 class="section-title">模型消耗 <small>（Token）</small></h2>
          <div class="table-wrap">
            <table class="data-table token-table">
              <thead>
                <tr><th>阶段</th><th>输入 Token</th><th>输出 Token</th><th>消耗占比</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in tokenUsageSummary.rows" :key="row.label">
                  <td>{{ row.label }}</td>
                  <td>{{ row.prompt.toLocaleString() }}</td>
                  <td>{{ row.completion.toLocaleString() }}</td>
                  <td>
                    <span class="percent-text">{{ row.percent.toFixed(1) }}%</span>
                    <span class="mini-progress"><i :style="{ width: `${row.percent}%` }"></i></span>
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td>合计</td>
                  <td>{{ tokenUsageSummary.prompt.toLocaleString() }}</td>
                  <td>{{ tokenUsageSummary.completion.toLocaleString() }}</td>
                  <td>{{ tokenUsageSummary.total.toLocaleString() }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </article>
      </div>

      <article class="result-card map-card">
        <h2 class="section-title">景点地图</h2>
        <AmapTripMap :points="mapPoints" :active="active" />
      </article>

      <article class="result-card weather-card">
        <h2 class="section-title">天气信息 <small>（{{ weather?.city || itinerary.destination }}）</small></h2>
        <div v-if="weatherLoading" class="empty-panel">正在加载天气信息...</div>
        <div v-else-if="weatherError" class="empty-panel">{{ weatherError }}</div>
        <div v-else-if="weather" class="weather-scroller">
          <div
            v-for="day in weather.days"
            :key="`${day.date}-${day.week}`"
            class="weather-item"
          >
            <div class="weather-date">{{ formatWeatherDate(day.date, day.week) }}</div>
            <div class="weather-symbol">{{ weatherIcon(day.day_weather) }}</div>
            <strong>{{ day.day_weather || "未知" }}</strong>
            <div class="weather-temp">{{ day.night_temp || "-" }} ~ {{ day.day_temp || "-" }}°C</div>
            <div class="weather-wind">{{ day.day_wind || "微风" }}</div>
            <span class="weather-tag">出行适宜</span>
          </div>
        </div>
        <div v-else class="empty-panel">暂无天气信息</div>
      </article>

      <article class="result-card spend-card">
        <h2 class="section-title">按天花费 <small>（元）</small></h2>
        <div class="table-wrap">
          <table class="data-table spend-table">
            <thead>
              <tr>
                <th>日期</th><th>主题</th><th>门票</th><th>餐饮</th><th>交通</th><th>住宿</th><th>当日合计</th><th>费用构成（元）</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in dayBudgetItems" :key="item.key">
                <td>{{ formatShortDate(item.date) }}</td>
                <td>{{ item.subtitle }}</td>
                <td>{{ item.tickets.toFixed(0) }}</td>
                <td>{{ item.meals.toFixed(0) }}</td>
                <td>{{ item.transport.toFixed(0) }}</td>
                <td>{{ item.hotel.toFixed(0) }}</td>
                <td class="number-cell">{{ item.total.toFixed(0) }}</td>
                <td>
                  <span class="cost-bar" :aria-label="`${item.title}费用构成`">
                    <i class="cost-bar__tickets" :style="{ width: costBarWidth(item.tickets) }"></i>
                    <i class="cost-bar__meals" :style="{ width: costBarWidth(item.meals) }"></i>
                    <i class="cost-bar__transport" :style="{ width: costBarWidth(item.transport) }"></i>
                    <i class="cost-bar__hotel" :style="{ width: costBarWidth(item.hotel) }"></i>
                  </span>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td>合计（{{ itinerary.days.length }} 天）</td>
                <td></td>
                <td>{{ itinerary.budget_breakdown.tickets.toFixed(0) }}</td>
                <td>{{ itinerary.budget_breakdown.meals.toFixed(0) }}</td>
                <td>{{ itinerary.budget_breakdown.transport.toFixed(0) }}</td>
                <td>{{ itinerary.budget_breakdown.hotel.toFixed(0) }}</td>
                <td>{{ itinerary.estimated_budget.toFixed(0) }}</td>
                <td>
                  <span class="cost-legend">
                    <i class="legend-dot legend-dot--tickets"></i>门票
                    <i class="legend-dot legend-dot--meals"></i>餐饮
                    <i class="legend-dot legend-dot--transport"></i>交通
                    <i class="legend-dot legend-dot--hotel"></i>住宿
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </article>

      <article class="result-card point-card">
        <h2 class="section-title">地图点位明细</h2>
        <div class="table-wrap">
          <table class="data-table point-table">
            <thead>
              <tr><th>景点</th><th>天数</th><th>日期</th><th>主题</th><th>地址</th><th>描述</th></tr>
            </thead>
            <tbody>
              <tr v-for="(point, index) in mapPoints" :key="point.key">
                <td>
                  <span class="point-number">{{ index + 1 }}</span>
                  <img
                    v-if="point.imageUrl && !failedImageKeys.has(point.key)"
                    :src="point.imageUrl"
                    :alt="`${point.name} 图片`"
                    @error="markImageAsFailed(point.key)"
                  />
                  <span v-else class="point-image-empty">景</span>
                  <strong>{{ point.name }}</strong>
                </td>
                <td>Day {{ point.dayIndex }}</td>
                <td>{{ formatShortDate(point.date) }}</td>
                <td>{{ point.theme }}</td>
                <td>{{ point.address }}</td>
                <td>{{ point.description }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="result-card itinerary-card">
        <h2 class="section-title">每日行程</h2>
        <div class="day-list">
          <details v-for="day in itinerary.days" :key="day.day_index" class="day-panel">
            <summary class="day-panel__head">
              <span class="day-panel__title">
                <b>Day {{ day.day_index }}</b>
                <span>{{ formatShortDate(day.date) }}</span>
                <span class="day-divider"></span>
                <strong>主题：{{ day.theme || "自由行程" }}</strong>
              </span>
              <span class="day-chevron" aria-hidden="true"></span>
            </summary>
            <div class="day-panel__body">
              <div><span>主要景点：</span>{{ day.spots[0]?.name || "未安排" }}</div>
              <div><span>景点地址：</span>{{ day.spots[0]?.address || day.spots[0]?.location || "待补充" }}</div>
              <div><span>餐饮建议：</span>{{ day.meals[0]?.name || "未安排" }}</div>
              <div><span>住宿安排：</span>{{ day.hotel?.name || "未安排" }}</div>
              <div>
                <span>交通信息：</span>{{ day.transport[0]?.distance_km != null
                  ? `${day.transport[0].distance_km.toFixed(2)} km / ${day.transport[0].estimated_minutes ?? 0} 分钟`
                  : day.transport[0]?.duration || "待补充" }}
              </div>
              <div><span>备注：</span>{{ day.notes[day.notes.length - 1] || "无" }}</div>
            </div>
          </details>
        </div>
      </article>
    </div>
  </section>

  <section v-else class="empty-state">
    <div class="result-card empty-state__card">
      <div class="empty-state__icon">⌁</div>
      <h2>还没有生成结果</h2>
      <p>先回到规划页生成一条行程。</p>
      <button type="button" @click="$emit('backHome')">返回规划页</button>
    </div>
  </section>
</template>

<style scoped>
.result-page {
  --mint: #0caf78;
  --mint-dark: #079265;
  --line: #dfe7e5;
  --soft-line: #e9efed;
  --ink: #1d2826;
  --muted: #697774;
  padding: 4px 6px 28px;
  color: var(--ink);
}

.result-content {
  display: grid;
  gap: 14px;
  width: 100%;
}

.result-card {
  min-width: 0;
  border: 1px solid rgba(218, 228, 225, 0.92);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 3px 12px rgba(35, 62, 57, 0.055);
}

.overview-card {
  padding: 24px 28px 22px;
}

.overview-title {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.overview-title h1 {
  margin: 0;
  color: #182321;
  font-size: clamp(24px, 1.75vw, 34px);
  line-height: 1.25;
  font-weight: 760;
  letter-spacing: -0.6px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 9px;
  border-radius: 999px;
  color: #169c70;
  background: #e8f8f1;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}

.status-badge i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(250px, 0.9fr) minmax(300px, 1.25fr) minmax(300px, 1.1fr);
}

.overview-grid > div {
  min-width: 0;
  padding: 2px 28px;
}

.overview-grid > div:first-child { padding-left: 0; }
.overview-grid > div:last-child { padding-right: 0; }
.overview-grid > div + div { border-left: 1px solid var(--soft-line); }

.overview-grid h2 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
  color: #293532;
}

.overview-meta {
  display: grid;
  align-content: start;
  gap: 11px;
}

.meta-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 10px;
  font-size: 13px;
  line-height: 1.5;
}

.meta-row span { color: #687572; }
.meta-row strong { color: #3c4745; font-weight: 550; overflow-wrap: anywhere; }

.overview-copy p {
  margin: 0;
  color: #596663;
  font-size: 13px;
  line-height: 1.95;
}

.overview-tips ul {
  display: grid;
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.overview-tips li {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  align-items: start;
  gap: 6px;
  color: #596663;
  font-size: 12.5px;
  line-height: 1.55;
}

.tip-dot { font-size: 11px; line-height: 1.8; }
.tip-dot--0 { color: #f36e5f; }
.tip-dot--1 { color: #668cf2; }
.tip-dot--2 { color: #f3a321; }
.tip-dot--3 { color: #d8739e; }
.empty-copy { color: var(--muted); font-size: 13px; }

.summary-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px;
}

.summary-grid--single { grid-template-columns: 1fr; }

.data-card,
.map-card,
.weather-card,
.spend-card,
.point-card,
.itinerary-card {
  padding: 18px 20px;
}

.section-title {
  margin: 0 0 13px;
  color: #26312f;
  font-size: 16px;
  line-height: 1.3;
  font-weight: 720;
}

.section-title small {
  color: #8b9794;
  font-size: 11px;
  font-weight: 500;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 5px;
  scrollbar-width: thin;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  color: #52605d;
  font-size: 12px;
}

.data-table th,
.data-table td {
  height: 40px;
  padding: 8px 12px;
  border-right: 1px solid var(--soft-line);
  border-bottom: 1px solid var(--soft-line);
  text-align: left;
  vertical-align: middle;
}

.data-table th:last-child,
.data-table td:last-child { border-right: 0; }

.data-table thead th {
  height: 36px;
  color: #64716e;
  background: #f7f9f8;
  font-size: 11px;
  font-weight: 650;
}

.data-table tbody tr:hover { background: #fbfdfc; }

.data-table tfoot td {
  height: 42px;
  border-bottom: 0;
  color: #34413e;
  background: #fbfcfc;
  font-weight: 700;
}

.budget-table th:nth-child(1) { width: 24%; }
.budget-table th:nth-child(2) { width: 51%; }
.budget-table th:nth-child(3) { width: 25%; }
.budget-table td:first-child { white-space: nowrap; }
.budget-table tfoot td:last-child { color: #f06424; font-size: 18px; text-align: right; }

.budget-icon {
  display: inline-grid;
  width: 20px;
  height: 20px;
  margin-right: 7px;
  place-items: center;
  border-radius: 5px;
  font-size: 10px;
}

.budget-icon--blue { color: #45a8db; background: #e8f7fc; }
.budget-icon--indigo { color: #588fe2; background: #edf3fe; }
.budget-icon--orange { color: #ee8b43; background: #fff1e7; }
.budget-icon--green { color: #35ab86; background: #e8f7f2; }
.number-cell { color: #2e3b38 !important; font-weight: 700; }

.token-table th:first-child { width: 27%; }
.token-table th:nth-child(2),
.token-table th:nth-child(3) { width: 20%; }
.token-table th:last-child { width: 33%; }

.percent-text {
  display: inline-block;
  width: 43px;
  color: #53605d;
}

.mini-progress {
  display: inline-block;
  width: calc(100% - 49px);
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: #e9efed;
  vertical-align: middle;
}

.mini-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--mint);
}

.map-card :deep(.trip-map) {
  height: clamp(320px, 31vw, 510px);
  min-height: 320px;
}

.map-card :deep(.trip-map__canvas),
.map-card :deep(.trip-map__placeholder) {
  min-height: 320px;
  border-radius: 4px;
}

.weather-scroller {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
  gap: 12px;
  padding: 0 18px;
}

.weather-item {
  min-width: 0;
  padding: 14px 10px 12px;
  border: 1px solid var(--soft-line);
  border-radius: 7px;
  text-align: center;
  box-shadow: 0 2px 7px rgba(33, 59, 53, 0.035);
}

.weather-date { color: #6b7774; font-size: 11px; font-weight: 600; }
.weather-symbol { height: 49px; margin: 6px 0 2px; font-size: 37px; line-height: 49px; }
.weather-item strong { display: block; color: #394542; font-size: 12px; }
.weather-temp { margin-top: 5px; color: #293532; font-size: 13px; font-weight: 650; }
.weather-wind { margin: 4px 0 7px; color: #8b9693; font-size: 10px; }

.weather-tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  color: #27a879;
  background: #eaf8f2;
  font-size: 10px;
}

.empty-panel {
  display: grid;
  min-height: 110px;
  place-items: center;
  border: 1px dashed #dce5e2;
  border-radius: 6px;
  color: #8a9693;
  font-size: 13px;
}

.spend-table { min-width: 920px; }
.spend-table th:nth-child(1) { width: 11%; }
.spend-table th:nth-child(2) { width: 17%; }
.spend-table th:nth-child(n+3):nth-child(-n+7) { width: 8%; }
.spend-table th:last-child { width: 32%; }
.spend-table td:nth-child(n+3):nth-child(-n+7) { text-align: center; }

.cost-bar {
  display: flex;
  width: 100%;
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #eef2f1;
}

.cost-bar i { display: block; height: 100%; }
.cost-bar__tickets { background: #5998e8; }
.cost-bar__meals { background: #f5a54b; }
.cost-bar__transport { background: #27b886; }
.cost-bar__hotel { background: #776be2; }

.cost-legend {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #77827f;
  font-size: 10px;
  font-weight: 500;
}

.legend-dot { width: 6px; height: 6px; border-radius: 50%; }
.legend-dot--tickets { background: #5998e8; }
.legend-dot--meals { background: #f5a54b; }
.legend-dot--transport { background: #27b886; }
.legend-dot--hotel { background: #776be2; }

.point-table { min-width: 1060px; }
.point-table th:nth-child(1) { width: 21%; }
.point-table th:nth-child(2),
.point-table th:nth-child(3) { width: 8%; }
.point-table th:nth-child(4) { width: 13%; }
.point-table th:nth-child(5) { width: 23%; }
.point-table th:nth-child(6) { width: 27%; }
.point-table td { line-height: 1.5; }
.point-table td:first-child { display: flex; align-items: center; gap: 8px; }
.point-table td:first-child strong { overflow: hidden; color: #3e4b48; text-overflow: ellipsis; white-space: nowrap; }

.point-number {
  display: grid;
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: var(--mint);
  font-size: 9px;
  font-weight: 700;
}

.point-table img,
.point-image-empty {
  width: 55px;
  height: 34px;
  flex: 0 0 55px;
  border-radius: 3px;
  object-fit: cover;
}

.point-image-empty {
  display: grid;
  place-items: center;
  color: #6ca28f;
  background: linear-gradient(135deg, #e4f1ec, #d5e9e2);
  font-size: 11px;
}

.day-list { display: grid; gap: 12px; }

.day-panel {
  overflow: hidden;
  border: 1px solid #b9e3d3;
  border-radius: 5px;
  background: #fff;
}

.day-panel__head {
  display: flex;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 9px 14px;
  color: #2d765f;
  background: #f2fbf7;
  cursor: pointer;
  list-style: none;
}

.day-panel__head::-webkit-details-marker { display: none; }

.day-panel__title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.day-panel__title b { color: #16a277; font-size: 13px; }
.day-panel__title strong { overflow: hidden; color: #43514e; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
.day-divider { width: 1px; height: 13px; background: #cfe8df; }

.day-chevron {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-right: 1.5px solid #2b9d79;
  border-bottom: 1.5px solid #2b9d79;
  transform: rotate(45deg) translateY(-2px);
  transition: transform 0.18s ease;
}

.day-panel[open] .day-chevron { transform: rotate(225deg) translate(-2px, -2px); }

.day-panel__body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 28px;
  padding: 15px 16px 17px;
  border-top: 1px solid #ddecE6;
  color: #4e5b58;
  font-size: 13px;
  line-height: 1.65;
}

.day-panel__body span { color: #8a9592; }

.empty-state { min-height: 440px; padding: 6px; }
.empty-state__card { max-width: 520px; margin: 80px auto; padding: 48px 24px; text-align: center; }
.empty-state__icon { color: var(--mint, #0caf78); font-size: 42px; }
.empty-state h2 { margin: 8px 0; color: #26322f; }
.empty-state p { margin: 0 0 22px; color: #7a8783; }
.empty-state button {
  padding: 9px 18px;
  border: 0;
  border-radius: 6px;
  color: #fff;
  background: #0caf78;
  cursor: pointer;
}

@media (max-width: 1120px) {
  .overview-grid { grid-template-columns: minmax(220px, 0.8fr) 1.2fr; }
  .overview-tips {
    grid-column: 1 / -1;
    margin-top: 20px;
    padding: 18px 0 0 !important;
    border-top: 1px solid var(--soft-line);
    border-left: 0 !important;
  }
  .overview-tips ul { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .weather-scroller { padding: 0; }
}

@media (max-width: 820px) {
  .result-page { padding-inline: 1px; }
  .summary-grid { grid-template-columns: 1fr; }
  .overview-card { padding: 20px; }
  .overview-grid { grid-template-columns: 1fr; }
  .overview-grid > div { padding: 17px 0; border-left: 0 !important; }
  .overview-grid > div + div { border-top: 1px solid var(--soft-line); }
  .overview-grid > div:first-child { padding-top: 0; }
  .overview-grid > div:last-child { padding-bottom: 0; }
  .overview-tips { grid-column: auto; margin-top: 0; }
  .overview-tips ul { grid-template-columns: 1fr; }
  .day-panel__body { grid-template-columns: 1fr; }
}

@media (max-width: 560px) {
  .result-content { gap: 9px; }
  .overview-card,
  .data-card,
  .map-card,
  .weather-card,
  .spend-card,
  .point-card,
  .itinerary-card { padding: 15px; }
  .overview-title { align-items: flex-start; flex-direction: column; gap: 8px; }
  .overview-title h1 { font-size: 23px; }
  .weather-scroller { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; }
  .weather-item { min-width: 155px; scroll-snap-align: start; }
  .day-panel__title { flex-wrap: wrap; gap: 6px; }
  .day-divider { display: none; }
  .day-panel__title strong { width: 100%; white-space: normal; }
}
</style>
