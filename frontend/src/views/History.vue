<script setup lang="ts">
import { message } from "ant-design-vue";
import { computed, onMounted, ref, watch } from "vue";

import AppIcon from "../components/AppIcon.vue";
import { deleteTrip, fetchTokenStats, getTripDetail, listTrips } from "../services/api";
import type { Itinerary, TokenStatsResponse, TripSummaryItem } from "../types";

type TripTab = "all" | "upcoming" | "ended";

interface TripListItem extends TripSummaryItem {
  itinerary?: Itinerary;
}

const props = defineProps<{
  active: boolean;
}>();

const emit = defineEmits<{
  openTrip: [itinerary: Itinerary];
}>();

const loading = ref(false);
const items = ref<TripListItem[]>([]);
const deletingTripId = ref("");
const openingTripId = ref("");
const tokenStats = ref<TokenStatsResponse | null>(null);
const activeTab = ref<TripTab>("all");
const searchText = ref("");
const sortDirection = ref<"asc" | "desc">("asc");
const hideExpired = ref(false);
const currentPage = ref(1);
const pageSize = ref(5);

const tabs: Array<{ key: TripTab; label: string }> = [
  { key: "all", label: "全部" },
  { key: "upcoming", label: "即将出发" },
  { key: "ended", label: "已结束" },
];

function parseDate(value?: string | null): Date | null {
  if (!value) return null;
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(date.getTime()) ? null : date;
}

function itineraryDates(item: TripListItem): { start: string; end: string } {
  const dates = (item.itinerary?.days || [])
    .map((day) => day.date || "")
    .filter(Boolean)
    .sort();

  if (dates.length) return { start: dates[0], end: dates[dates.length - 1] };

  const fallback = item.trip_id.match(/\d{4}-\d{2}-\d{2}/)?.[0] || "";
  return { start: fallback, end: fallback };
}

function tripStatus(item: TripListItem): "upcoming" | "ended" {
  const { end } = itineraryDates(item);
  const endDate = parseDate(end);
  if (!endDate) return "upcoming";

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return endDate < today ? "ended" : "upcoming";
}

function formatDate(value: string): string {
  const date = parseDate(value);
  if (!date) return "待定";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDateTime(value?: string | null): string {
  if (!value) return "未记录";
  const normalized = value.replace("T", " ").replace(/\.\d+.*$/, "");
  return normalized.slice(0, 16);
}

function tripDuration(item: TripListItem): { days: number; nights: number } {
  const { start, end } = itineraryDates(item);
  const startDate = parseDate(start);
  const endDate = parseDate(end);
  if (startDate && endDate) {
    const days = Math.max(1, Math.round((endDate.getTime() - startDate.getTime()) / 86400000) + 1);
    return { days, nights: Math.max(0, days - 1) };
  }

  const days = Math.max(1, item.itinerary?.days.length || 1);
  return { days, nights: Math.max(0, days - 1) };
}

const coverNames: Record<string, string> = {
  北京: "beijing",
  成都: "chengdu",
  大理: "dali",
  三亚: "sanya",
  厦门: "xiamen",
  西安: "xian",
};
const fallbackCovers = ["beijing", "chengdu", "dali", "sanya", "xiamen", "xian"];

function coverFor(item: TripListItem): string {
  const matched = Object.entries(coverNames).find(([city]) => item.destination.includes(city));
  if (matched) return `/covers/${matched[1]}.png`;

  const hash = [...item.destination].reduce((sum, character) => sum + character.charCodeAt(0), 0);
  return `/covers/${fallbackCovers[hash % fallbackCovers.length]}.png`;
}

const filteredItems = computed(() => {
  const keyword = searchText.value.trim().toLocaleLowerCase();
  const filtered = items.value.filter((item) => {
    const status = tripStatus(item);
    const matchesTab = activeTab.value === "all" || status === activeTab.value;
    const matchesExpiry = !hideExpired.value || status === "upcoming";
    const matchesSearch = !keyword || `${item.destination} ${item.summary}`.toLocaleLowerCase().includes(keyword);
    return matchesTab && matchesExpiry && matchesSearch;
  });

  return [...filtered].sort((left, right) => {
    const leftTime = parseDate(itineraryDates(left).start)?.getTime() ?? Number.MAX_SAFE_INTEGER;
    const rightTime = parseDate(itineraryDates(right).start)?.getTime() ?? Number.MAX_SAFE_INTEGER;
    return sortDirection.value === "asc" ? leftTime - rightTime : rightTime - leftTime;
  });
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / pageSize.value)));
const pagedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredItems.value.slice(start, start + pageSize.value);
});
const visiblePages = computed(() => Array.from({ length: totalPages.value }, (_, index) => index + 1));

async function loadTrips(options?: { silent?: boolean }) {
  // 已有列表时静默刷新，避免切换页时整页闪「正在加载」
  const silent = options?.silent ?? items.value.length > 0;
  if (!silent) loading.value = true;
  try {
    const [listResponse, statsResponse] = await Promise.all([
      listTrips(),
      fetchTokenStats().catch(() => null),
    ]);

    const details = await Promise.allSettled(
      listResponse.items.map((item) => getTripDetail(item.trip_id)),
    );

    items.value = listResponse.items.map((item, index) => {
      const detail = details[index];
      return detail.status === "fulfilled"
        ? { ...item, itinerary: detail.value.itinerary }
        : item;
    });
    tokenStats.value = statsResponse;
  } catch (error) {
    console.error(error);
    message.error("行程列表加载失败。");
  } finally {
    loading.value = false;
  }
}

async function openTrip(item: TripListItem) {
  openingTripId.value = item.trip_id;
  try {
    const itinerary = item.itinerary || (await getTripDetail(item.trip_id)).itinerary;
    emit("openTrip", itinerary);
  } catch (error) {
    console.error(error);
    message.error("读取行程详情失败。");
  } finally {
    openingTripId.value = "";
  }
}

async function removeTrip(tripId: string) {
  const confirmed = window.confirm("确定要删除这条已保存行程吗？删除后无法恢复。");
  if (!confirmed) return;

  deletingTripId.value = tripId;
  try {
    await deleteTrip(tripId);
    items.value = items.value.filter((item) => item.trip_id !== tripId);
    tokenStats.value = await fetchTokenStats().catch(() => tokenStats.value);
    message.success("行程已删除。");
  } catch (error) {
    console.error(error);
    message.error("删除行程失败。");
  } finally {
    deletingTripId.value = "";
  }
}

function clearFilters() {
  searchText.value = "";
  activeTab.value = "all";
  hideExpired.value = false;
  sortDirection.value = "asc";
}

watch([activeTab, searchText, sortDirection, hideExpired, pageSize], () => {
  currentPage.value = 1;
});

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages;
});

onMounted(() => {
  if (props.active) void loadTrips();
});

// 保活后再次进入：有缓存就静默刷新，不再全屏 loading
watch(
  () => props.active,
  (active, wasActive) => {
    if (active && !wasActive && items.value.length > 0) {
      void loadTrips({ silent: true });
    } else if (active && !wasActive) {
      void loadTrips();
    }
  },
);
</script>

<template>
  <section class="trips-page">
    <div class="overview-card">
      <div class="saved-summary">
        <span class="summary-icon"><AppIcon name="calendar" :size="30" /></span>
        <div>
          <div class="saved-summary__title">
            已保存行程 <strong>{{ tokenStats?.trip_count ?? items.length }}</strong> 条
          </div>
          <p>精心规划每一段旅程，让旅行更美好</p>
        </div>
      </div>

      <div class="token-overview">
        <span class="token-overview__icon"><AppIcon name="pie-chart" :size="29" /></span>
        <div class="token-metric">
          <span>输入 Token</span>
          <strong>{{ tokenStats?.total_prompt_tokens.toLocaleString() ?? "--" }}</strong>
        </div>
        <div class="token-metric">
          <span>输出 Token</span>
          <strong>{{ tokenStats?.total_completion_tokens.toLocaleString() ?? "--" }}</strong>
        </div>
        <div class="token-metric token-metric--total">
          <span>总 Token</span>
          <strong>{{ tokenStats?.total_tokens.toLocaleString() ?? "--" }}</strong>
        </div>
      </div>
    </div>

    <div class="search-row">
      <label class="search-box">
        <AppIcon name="search" :size="22" />
        <input v-model="searchText" type="search" placeholder="搜索目的地或行程摘要" />
      </label>

      <div class="search-row__actions">
        <button class="refresh-button" type="button" :disabled="loading" @click="loadTrips()">
          <AppIcon name="refresh" :size="20" />
          <span>{{ loading ? "刷新中" : "刷新行程" }}</span>
        </button>
        <button
          class="sort-button"
          type="button"
          @click="sortDirection = sortDirection === 'asc' ? 'desc' : 'asc'"
        >
          排序：出发日期
          <AppIcon :name="sortDirection === 'asc' ? 'chevron-down' : 'chevron-up'" :size="17" />
        </button>
      </div>
    </div>

    <div class="journey-panel">
      <div class="panel-toolbar">
        <div class="trip-tabs" role="tablist" aria-label="行程状态筛选">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :class="['trip-tab', { 'trip-tab--active': activeTab === tab.key }]"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.key"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="filter-actions">
          <button
            :class="['filter-button', { 'filter-button--active': hideExpired }]"
            type="button"
            @click="hideExpired = !hideExpired"
          >
            <AppIcon name="filter" :size="18" />
            仅看未过期
          </button>
          <button class="clear-button" type="button" @click="clearFilters">清除筛选</button>
        </div>
      </div>

      <div v-if="searchText.trim()" class="search-result-tip">
        <AppIcon name="search" :size="17" />
        <span>搜索“{{ searchText.trim() }}”的结果</span>
        <i></i>
        <span>共 {{ filteredItems.length }} 条</span>
        <button type="button" @click="searchText = ''">清除搜索</button>
      </div>

      <div v-if="loading" class="list-state">
        <span class="loading-ring"></span>
        正在加载您的行程...
      </div>

      <div v-else-if="pagedItems.length === 0" class="list-state">
        <span class="empty-calendar"><AppIcon name="calendar" :size="34" /></span>
        <strong>{{ items.length ? "没有符合条件的行程" : "还没有已保存的行程" }}</strong>
        <p>{{ items.length ? "试试切换筛选条件或清除搜索" : "完成旅行规划后，记得保存到这里" }}</p>
      </div>

      <div v-else class="trip-list">
        <article v-for="item in pagedItems" :key="item.trip_id" class="trip-card">
          <img class="trip-card__cover" :src="coverFor(item)" :alt="`${item.destination}行程封面`" />

          <div class="trip-card__content">
            <div class="trip-card__heading">
              <h3>{{ item.destination }}</h3>
              <span :class="['status-badge', `status-badge--${tripStatus(item)}`]">
                <AppIcon :name="tripStatus(item) === 'upcoming' ? 'plane' : 'check-circle'" :size="15" />
                {{ tripStatus(item) === "upcoming" ? "即将出发" : "已结束" }}
              </span>
            </div>

            <p class="trip-card__tags">
              {{ tripDuration(item).days }}天{{ tripDuration(item).nights }}晚
              <span>｜</span>深度旅行 <span>｜</span>城市探索 <span>｜</span>精选住宿
            </p>

            <div class="trip-card__dates">
              <div class="date-block">
                <AppIcon name="calendar" :size="21" />
                <span><small>出发日期</small>{{ formatDate(itineraryDates(item).start) }}</span>
              </div>
              <i></i>
              <div class="date-block">
                <AppIcon name="calendar" :size="21" />
                <span><small>结束日期</small>{{ formatDate(itineraryDates(item).end) }}</span>
              </div>
              <i></i>
              <div class="date-block date-block--updated">
                <AppIcon name="clock" :size="21" />
                <span><small>最近更新时间</small>{{ formatDateTime(item.updated_at) }}</span>
              </div>
            </div>
          </div>

          <div class="trip-card__actions">
            <button
              class="detail-button"
              type="button"
              :disabled="openingTripId === item.trip_id"
              @click="openTrip(item)"
            >
              {{ openingTripId === item.trip_id ? "加载中" : "查看详情" }}
            </button>
            <button class="square-button" type="button" aria-label="编辑行程" @click="openTrip(item)">
              <AppIcon name="edit" :size="19" />
            </button>
            <button
              class="square-button square-button--danger"
              type="button"
              aria-label="删除行程"
              :disabled="deletingTripId === item.trip_id"
              @click="removeTrip(item.trip_id)"
            >
              <AppIcon name="trash" :size="19" />
            </button>
          </div>
        </article>
      </div>

      <div v-if="!loading && filteredItems.length" class="pagination">
        <button type="button" :disabled="currentPage === 1" aria-label="上一页" @click="currentPage--">
          <AppIcon name="chevron-left" :size="17" />
        </button>
        <button
          v-for="page in visiblePages"
          :key="page"
          type="button"
          :class="{ active: currentPage === page }"
          @click="currentPage = page"
        >
          {{ page }}
        </button>
        <button type="button" :disabled="currentPage === totalPages" aria-label="下一页" @click="currentPage++">
          <AppIcon name="chevron-right" :size="17" />
        </button>
        <label class="page-size">
          每页
          <select v-model.number="pageSize">
            <option :value="5">5 条</option>
            <option :value="10">10 条</option>
            <option :value="20">20 条</option>
          </select>
        </label>
      </div>
    </div>
  </section>
</template>

<style scoped>
.trips-page {
  min-height: 100%;
  padding: calc(18px * var(--ui-scale)) calc(20px * var(--ui-scale)) calc(24px * var(--ui-scale));
  color: #172033;
}

button,
input,
select {
  font: inherit;
}

button {
  color: inherit;
}

.overview-card,
.journey-panel {
  border: 1px solid #e7edf5;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 4px 13px rgba(29, 57, 91, 0.08);
}

.overview-card {
  min-height: calc(112px * var(--ui-scale));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(24px * var(--ui-scale));
  padding: calc(15px * var(--ui-scale)) calc(16px * var(--ui-scale));
  border-radius: calc(14px * var(--ui-scale));
}

.saved-summary {
  display: flex;
  align-items: center;
  gap: calc(18px * var(--ui-scale));
  padding-left: calc(4px * var(--ui-scale));
}

.summary-icon {
  width: calc(62px * var(--ui-scale));
  height: calc(62px * var(--ui-scale));
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  color: #1576f6;
  background: #edf5ff;
}

.saved-summary__title {
  font-size: calc(18px * var(--ui-scale));
  font-weight: 650;
  line-height: 1.4;
}

.saved-summary__title strong {
  margin: 0 calc(3px * var(--ui-scale));
  color: #126ef2;
  font-size: calc(23px * var(--ui-scale));
}

.saved-summary p {
  margin: calc(7px * var(--ui-scale)) 0 0;
  color: #6b7890;
  font-size: calc(14px * var(--ui-scale));
}

.token-overview {
  min-width: calc(555px * var(--ui-scale));
  min-height: calc(80px * var(--ui-scale));
  display: grid;
  grid-template-columns: calc(66px * var(--ui-scale)) repeat(3, minmax(calc(100px * var(--ui-scale)), 1fr));
  align-items: center;
  padding: calc(10px * var(--ui-scale)) calc(14px * var(--ui-scale));
  border-radius: calc(13px * var(--ui-scale));
  background: linear-gradient(105deg, #f3f8ff, #f7faff);
}

.token-overview__icon {
  width: calc(48px * var(--ui-scale));
  height: calc(48px * var(--ui-scale));
  display: grid;
  place-items: center;
  color: #247af4;
  border-radius: 50%;
  background: #e7f2ff;
}

.token-metric {
  min-width: 0;
  display: grid;
  gap: calc(5px * var(--ui-scale));
  padding: 0 calc(25px * var(--ui-scale));
  border-left: 1px solid #dde7f4;
}

.token-metric span {
  color: #65728a;
  font-size: calc(13px * var(--ui-scale));
  white-space: nowrap;
}

.token-metric strong {
  color: #14213a;
  font-size: calc(20px * var(--ui-scale));
  font-weight: 650;
}

.token-metric--total strong {
  color: #176de7;
  font-size: calc(30px * var(--ui-scale));
  line-height: 1;
}

.search-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(20px * var(--ui-scale));
  margin: calc(22px * var(--ui-scale)) 0 calc(18px * var(--ui-scale));
}

.search-box {
  width: min(calc(700px * var(--ui-scale)), 54%);
  height: calc(54px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(13px * var(--ui-scale));
  padding: 0 calc(20px * var(--ui-scale));
  color: #42516d;
  border: 1px solid #d6deea;
  border-radius: calc(9px * var(--ui-scale));
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-box:focus-within {
  border-color: #4c94f8;
  box-shadow: 0 0 0 3px rgba(30, 116, 244, 0.1);
}

.search-box input {
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  outline: 0;
  color: #172033;
  background: transparent;
  font-size: calc(15px * var(--ui-scale));
}

.search-box input::placeholder {
  color: #7c899f;
}

.search-row__actions {
  display: flex;
  gap: calc(10px * var(--ui-scale));
}

.refresh-button,
.sort-button,
.filter-button,
.clear-button,
.trip-tab,
.detail-button,
.square-button,
.pagination button {
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s, transform 0.18s;
}

.refresh-button:active,
.sort-button:active,
.filter-button:active,
.detail-button:active,
.square-button:active,
.pagination button:active {
  transform: scale(0.97);
}

.refresh-button,
.sort-button {
  height: calc(50px * var(--ui-scale));
  display: flex;
  align-items: center;
  justify-content: center;
  gap: calc(10px * var(--ui-scale));
  padding: 0 calc(18px * var(--ui-scale));
  border: 1px solid #d5deeb;
  border-radius: calc(10px * var(--ui-scale));
  background: #fff;
  font-size: calc(15px * var(--ui-scale));
}

.refresh-button:hover,
.sort-button:hover,
.filter-button:hover {
  color: #076bf3;
  border-color: #8dbafb;
}

.sort-button {
  min-width: calc(205px * var(--ui-scale));
  justify-content: space-between;
}

.journey-panel {
  overflow: hidden;
  border-radius: calc(14px * var(--ui-scale));
}

.panel-toolbar {
  min-height: calc(78px * var(--ui-scale));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(20px * var(--ui-scale));
  padding: calc(12px * var(--ui-scale)) calc(25px * var(--ui-scale));
  border-bottom: 1px solid #e4eaf2;
}

.trip-tabs {
  display: flex;
  align-items: center;
  padding: calc(3px * var(--ui-scale));
  border-radius: calc(11px * var(--ui-scale));
  background: #f5f8fc;
}

.trip-tab {
  min-width: calc(100px * var(--ui-scale));
  height: calc(46px * var(--ui-scale));
  padding: 0 calc(18px * var(--ui-scale));
  border: 0;
  border-radius: calc(10px * var(--ui-scale));
  color: #1c2638;
  background: transparent;
  font-size: calc(15px * var(--ui-scale));
  font-weight: 500;
}

.trip-tab--active {
  color: #fff;
  background: linear-gradient(135deg, #1476f7, #0068ed);
  box-shadow: 0 4px 9px rgba(14, 109, 241, 0.2);
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
}

.filter-button {
  height: calc(44px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  padding: 0 calc(16px * var(--ui-scale));
  border: 1px solid #d7e0ec;
  border-radius: calc(9px * var(--ui-scale));
  background: #fff;
  font-size: calc(14px * var(--ui-scale));
}

.filter-button--active {
  color: #076bf3;
  border-color: #8dbafb;
  background: #eff6ff;
}

.clear-button {
  padding: calc(10px * var(--ui-scale));
  border: 0;
  color: #0875f8;
  background: transparent;
  font-size: calc(14px * var(--ui-scale));
}

.search-result-tip {
  height: calc(43px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  padding: 0 calc(26px * var(--ui-scale));
  color: #65738b;
  border-bottom: 1px solid #edf1f6;
  font-size: calc(13px * var(--ui-scale));
}

.search-result-tip i {
  width: 1px;
  height: calc(16px * var(--ui-scale));
  background: #dce3ed;
}

.search-result-tip button {
  padding: 0;
  border: 0;
  color: #0b72f5;
  background: transparent;
  cursor: pointer;
}

.trip-list {
  display: grid;
  gap: calc(9px * var(--ui-scale));
  padding: calc(14px * var(--ui-scale)) calc(20px * var(--ui-scale));
}

.trip-card {
  min-height: calc(154px * var(--ui-scale));
  display: grid;
  grid-template-columns: calc(245px * var(--ui-scale)) minmax(0, 1fr) auto;
  align-items: center;
  gap: calc(27px * var(--ui-scale));
  padding: calc(16px * var(--ui-scale));
  border: 1px solid #dce4ee;
  border-radius: calc(16px * var(--ui-scale));
  background: #fff;
  box-shadow: 0 2px 7px rgba(34, 62, 91, 0.04);
}

.trip-card__cover {
  width: 100%;
  height: calc(120px * var(--ui-scale));
  display: block;
  border-radius: calc(11px * var(--ui-scale));
  object-fit: cover;
  background: #e8f0f8;
}

.trip-card__content {
  min-width: 0;
}

.trip-card__heading {
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
}

.trip-card__heading h3 {
  margin: 0;
  color: #111827;
  font-size: calc(23px * var(--ui-scale));
  font-weight: 700;
  letter-spacing: -0.3px;
}

.status-badge {
  height: calc(30px * var(--ui-scale));
  display: inline-flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale));
  border: 1px solid;
  border-radius: calc(6px * var(--ui-scale));
  font-size: calc(13px * var(--ui-scale));
  white-space: nowrap;
}

.status-badge--upcoming {
  color: #066df1;
  border-color: #bad7ff;
  background: #eef6ff;
}

.status-badge--ended {
  color: #637088;
  border-color: #d4dce7;
  background: #f5f7fa;
}

.trip-card__tags {
  margin: calc(10px * var(--ui-scale)) 0 calc(16px * var(--ui-scale));
  overflow: hidden;
  color: #5e6c84;
  font-size: calc(14px * var(--ui-scale));
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trip-card__tags span {
  margin: 0 calc(4px * var(--ui-scale));
  color: #99a5b7;
}

.trip-card__dates {
  display: flex;
  align-items: center;
  gap: calc(21px * var(--ui-scale));
}

.trip-card__dates > i {
  width: 1px;
  height: calc(32px * var(--ui-scale));
  flex: 0 0 auto;
  background: #dce4ee;
}

.date-block {
  min-width: calc(164px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(13px * var(--ui-scale));
  color: #52627d;
  font-size: calc(13px * var(--ui-scale));
  white-space: nowrap;
}

.date-block > span {
  display: grid;
  gap: calc(3px * var(--ui-scale));
}

.date-block small {
  color: #7b879a;
  font-size: calc(11px * var(--ui-scale));
}

.date-block--updated {
  min-width: calc(205px * var(--ui-scale));
}

.trip-card__actions {
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
  padding: 0 calc(20px * var(--ui-scale));
}

.detail-button {
  min-width: calc(120px * var(--ui-scale));
  height: calc(47px * var(--ui-scale));
  padding: 0 calc(18px * var(--ui-scale));
  border: 1px solid #1878f5;
  border-radius: calc(8px * var(--ui-scale));
  color: #076bf3;
  background: #fff;
  font-size: calc(15px * var(--ui-scale));
  font-weight: 600;
}

.detail-button:hover {
  color: #fff;
  background: #0c73f5;
}

.square-button {
  width: calc(47px * var(--ui-scale));
  height: calc(47px * var(--ui-scale));
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid #d6dfeb;
  border-radius: calc(8px * var(--ui-scale));
  background: #fff;
}

.square-button:hover {
  color: #0873f7;
  border-color: #8cbafb;
}

.square-button--danger {
  color: #ff4054;
}

.square-button--danger:hover {
  color: #fff;
  border-color: #ff5263;
  background: #ff5263;
}

button:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.list-state {
  min-height: calc(300px * var(--ui-scale));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: calc(10px * var(--ui-scale));
  color: #7d899b;
  font-size: calc(14px * var(--ui-scale));
}

.list-state strong {
  color: #34425a;
  font-size: calc(17px * var(--ui-scale));
}

.list-state p {
  margin: 0;
}

.empty-calendar {
  width: calc(64px * var(--ui-scale));
  height: calc(64px * var(--ui-scale));
  display: grid;
  place-items: center;
  color: #438cf5;
  border-radius: 50%;
  background: #eef5ff;
}

.loading-ring {
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  border: 3px solid #dbe9fb;
  border-top-color: #1476f7;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: calc(10px * var(--ui-scale));
  padding: calc(6px * var(--ui-scale)) calc(20px * var(--ui-scale)) calc(16px * var(--ui-scale));
}

.pagination button {
  width: calc(40px * var(--ui-scale));
  height: calc(38px * var(--ui-scale));
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid #dce4ee;
  border-radius: calc(8px * var(--ui-scale));
  background: #fff;
  font-size: calc(14px * var(--ui-scale));
}

.pagination button:hover:not(:disabled),
.pagination button.active {
  color: #fff;
  border-color: #0a70f3;
  background: #0a70f3;
}

.page-size {
  height: calc(38px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(7px * var(--ui-scale));
  margin-left: calc(28px * var(--ui-scale));
  padding: 0 calc(12px * var(--ui-scale));
  color: #526078;
  border: 1px solid #dce4ee;
  border-radius: calc(8px * var(--ui-scale));
  background: #fff;
  font-size: calc(14px * var(--ui-scale));
}

.page-size select {
  padding: 0;
  border: 0;
  outline: 0;
  color: #526078;
  background: transparent;
}

@media (max-width: 1280px) {
  .token-overview {
    min-width: 500px;
  }

  .trip-card {
    grid-template-columns: 190px minmax(0, 1fr) auto;
    gap: 18px;
  }

  .date-block {
    min-width: 130px;
  }

  .date-block--updated {
    display: none;
  }

  .trip-card__dates > i:last-of-type {
    display: none;
  }

  .trip-card__actions {
    gap: 8px;
    padding: 0 5px;
  }
}

@media (max-width: 960px) {
  .trips-page {
    padding: 14px;
  }

  .overview-card {
    align-items: stretch;
    flex-direction: column;
  }

  .token-overview {
    width: 100%;
    min-width: 0;
  }

  .search-box {
    width: 100%;
  }

  .search-row {
    align-items: stretch;
    flex-direction: column;
  }

  .search-row__actions {
    justify-content: flex-end;
  }

  .trip-card {
    grid-template-columns: 180px minmax(0, 1fr);
  }

  .trip-card__actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
    padding: 0;
  }
}

@media (max-width: 700px) {
  .trips-page {
    padding: 8px;
  }

  .token-overview {
    grid-template-columns: repeat(3, 1fr);
  }

  .token-overview__icon {
    display: none;
  }

  .token-metric {
    padding: 0 10px;
  }

  .panel-toolbar {
    align-items: stretch;
    flex-direction: column;
    padding: 12px;
  }

  .trip-tabs,
  .filter-actions {
    width: 100%;
  }

  .trip-tab {
    min-width: 0;
    flex: 1;
    padding: 0 8px;
  }

  .filter-actions {
    justify-content: flex-end;
  }

  .trip-list {
    padding: 10px;
  }

  .trip-card {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .trip-card__cover {
    height: 190px;
  }

  .trip-card__actions {
    grid-column: auto;
  }

  .trip-card__dates {
    flex-wrap: wrap;
  }

  .trip-card__dates > i {
    display: none;
  }

  .date-block--updated {
    display: flex;
  }

  .detail-button {
    flex: 1;
  }

  .page-size {
    margin-left: 5px;
  }
}

@media (max-width: 480px) {
  .overview-card {
    padding: 14px;
  }

  .saved-summary {
    gap: 12px;
    padding-left: 0;
  }

  .summary-icon {
    width: 50px;
    height: 50px;
  }

  .saved-summary__title {
    font-size: 16px;
  }

  .saved-summary p {
    font-size: 12px;
  }

  .token-overview {
    min-height: 70px;
    padding: 8px 4px;
  }

  .token-metric {
    padding: 0 7px;
  }

  .token-metric span {
    font-size: 11px;
  }

  .token-metric strong,
  .token-metric--total strong {
    font-size: 18px;
  }

  .search-row__actions > button {
    min-width: 0;
    flex: 1;
    padding: 0 12px;
  }

  .refresh-button span {
    display: none;
  }

  .trip-card__cover {
    height: 155px;
  }

  .trip-card__heading {
    align-items: flex-start;
    justify-content: space-between;
  }

  .trip-card__heading h3 {
    font-size: 20px;
  }

  .trip-card__tags {
    white-space: normal;
  }

  .date-block {
    width: 100%;
  }

  .pagination {
    flex-wrap: wrap;
  }

  .page-size {
    margin-left: 0;
  }
}
</style>
