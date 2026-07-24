<script setup lang="ts">
import { computed, ref } from "vue";

import type { DestinationRecommendationItem } from "../types";
import AppIcon from "./AppIcon.vue";

const props = defineProps<{
  items: DestinationRecommendationItem[];
  loading?: boolean;
  selectedCity?: string;
}>();

const emit = defineEmits<{
  select: [item: DestinationRecommendationItem];
}>();

const page = ref(0);
const pageSize = 4;
const totalPages = computed(() => Math.max(1, Math.ceil(props.items.length / pageSize)));
const visibleItems = computed(() => {
  if (!props.items.length) return [];
  const start = Math.min(page.value, totalPages.value - 1) * pageSize;
  return props.items.slice(start, start + pageSize);
});

function coverUrl(item: DestinationRecommendationItem): string {
  return item.image_path || `/covers/${item.city_key}.png`;
}

function weatherIconName(item: DestinationRecommendationItem): string {
  const text = `${item.forecast_days?.[0]?.day_weather || item.weather_label || ""}`;
  return text.includes("晴") ? "sun" : "weather";
}

function weatherText(item: DestinationRecommendationItem): string {
  return item.forecast_days?.[0]?.day_weather || item.weather_label?.split(/[·|，]/)[0] || "天气舒适";
}

function temperature(item: DestinationRecommendationItem): string {
  const day = item.forecast_days?.[0];
  if (day?.day_temp) return `${day.day_temp}°C`;
  return "22°C";
}

function previous() {
  page.value = (page.value - 1 + totalPages.value) % totalPages.value;
}

function next() {
  page.value = (page.value + 1) % totalPages.value;
}
</script>

<template>
  <section class="hot-section">
    <header class="hot-header">
      <div class="hot-heading">
        <span class="hot-heading__icon"><AppIcon name="fire" :size="23" :stroke-width="2.2" /></span>
        <h2>热门目的地推荐</h2>
        <span>点击卡片可自动填入表单</span>
      </div>
    </header>

    <div v-if="loading" class="hot-state">
      <span class="state-spinner"></span>
      正在根据天气加载热门目的地…
    </div>

    <div v-else-if="visibleItems.length" class="carousel">
      <button v-if="totalPages > 1" type="button" class="arrow arrow--left" aria-label="上一组" @click="previous">
        <AppIcon name="chevron-left" :size="22" />
      </button>

      <div class="hot-grid">
        <button
          v-for="(item, index) in visibleItems"
          :key="item.city_key"
          type="button"
          :class="['hot-card', { 'hot-card--selected': selectedCity === item.city }]"
          @click="emit('select', item)"
        >
          <div class="hot-card__image-wrap">
            <img class="hot-card__image" :src="coverUrl(item)" :alt="`${item.city}风景`" />
            <span v-if="index === 0 && selectedCity !== item.city" class="recommend-badge">推荐</span>
            <span v-if="selectedCity === item.city" class="selected-badge">✓</span>
            <strong>{{ item.city }}</strong>
          </div>
          <div class="hot-card__tagline">
            <AppIcon name="sparkles" :size="15" />
            <span>{{ item.tagline }}</span>
          </div>
          <div class="hot-card__meta">
            <span><AppIcon :name="weatherIconName(item)" :size="18" /> {{ weatherText(item) }}&nbsp; {{ temperature(item) }}</span>
            <span><AppIcon name="calendar" :size="16" /> {{ item.suggested_days || 3 }}–{{ (item.suggested_days || 3) + 1 }} 天</span>
          </div>
        </button>
      </div>

      <button v-if="totalPages > 1" type="button" class="arrow arrow--right" aria-label="下一组" @click="next">
        <AppIcon name="chevron-right" :size="22" />
      </button>
    </div>

    <div v-else class="hot-state">暂无热门推荐，请直接填写下方目的地。</div>

    <div v-if="totalPages > 1 && !loading" class="pagination">
      <button
        v-for="index in totalPages"
        :key="index"
        type="button"
        :class="{ active: page === index - 1 }"
        :aria-label="`第 ${index} 页`"
        @click="page = index - 1"
      ></button>
    </div>
  </section>
</template>

<style scoped>
.hot-section {
  position: relative;
  height: 329px;
  padding: 20px 28px 17px;
  border: 1px solid rgba(226, 232, 240, 0.72);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 4px 14px rgba(35, 65, 95, 0.08);
}

.hot-header {
  height: 43px;
  display: flex;
  align-items: flex-start;
}

.hot-heading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hot-heading__icon {
  color: #ff414a;
}

.hot-heading h2 {
  margin: 0;
  color: #111827;
  font-size: 19px;
  line-height: 1;
  font-weight: 750;
}

.hot-heading > span:last-child {
  margin-left: 2px;
  color: #7b89a3;
  font-size: 13px;
}

.carousel {
  position: relative;
}

.hot-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.hot-card {
  min-width: 0;
  height: 247px;
  padding: 0;
  overflow: hidden;
  text-align: left;
  color: #18243a;
  border: 1px solid #dfe7ef;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 5px rgba(30, 58, 87, 0.1);
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.hot-card:hover {
  transform: translateY(-2px);
  border-color: #8ebfff;
  box-shadow: 0 7px 16px rgba(21, 86, 156, 0.15);
}

.hot-card--selected {
  border: 2px solid #087aff;
  box-shadow: 0 0 0 3px rgba(8, 122, 255, 0.14), 0 5px 12px rgba(24, 93, 170, 0.13);
}

.hot-card__image-wrap {
  position: relative;
  height: 174px;
  overflow: hidden;
  background: #dbe7f1;
}

.hot-card--selected .hot-card__image-wrap {
  height: 173px;
}

.hot-card__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hot-card__image-wrap::after {
  content: "";
  position: absolute;
  inset: 40% 0 0;
  background: linear-gradient(to bottom, transparent, rgba(5, 14, 26, 0.7));
  pointer-events: none;
}

.hot-card__image-wrap strong {
  position: absolute;
  z-index: 1;
  left: 16px;
  bottom: 8px;
  color: #fff;
  font-size: 24px;
  line-height: 1.2;
  font-weight: 800;
  text-shadow: 0 2px 5px rgba(0, 0, 0, 0.45);
}

.recommend-badge,
.selected-badge {
  position: absolute;
  z-index: 2;
  top: 10px;
  right: 10px;
  display: grid;
  place-items: center;
}

.recommend-badge {
  height: 26px;
  padding: 0 11px;
  border-radius: 13px;
  color: #55708f;
  background: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  font-weight: 600;
}

.selected-badge {
  width: 29px;
  height: 29px;
  border-radius: 50%;
  color: #fff;
  background: #0675f5;
  font-size: 17px;
  font-weight: 800;
  box-shadow: 0 2px 5px rgba(0, 76, 173, 0.3);
}

.hot-card__tagline,
.hot-card__meta,
.hot-card__meta span {
  display: flex;
  align-items: center;
}

.hot-card__tagline {
  height: 34px;
  gap: 8px;
  padding: 0 13px;
  border-bottom: 1px solid #edf1f5;
  color: #4c5d78;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
}

.hot-card__tagline span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.hot-card__meta {
  height: 38px;
  justify-content: space-between;
  gap: 6px;
  padding: 0 12px;
  color: #53647f;
  font-size: 12px;
}

.hot-card__meta span {
  gap: 6px;
  white-space: nowrap;
}

.hot-card__meta span:first-child .app-icon {
  color: #ff8a00;
}

.arrow {
  position: absolute;
  z-index: 5;
  top: 91px;
  width: 41px;
  height: 41px;
  padding: 0;
  display: grid;
  place-items: center;
  color: #425673;
  border: 1px solid #dce3eb;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 3px 9px rgba(30, 50, 75, 0.14);
  cursor: pointer;
}

.arrow--left {
  left: -38px;
}

.arrow--right {
  right: -38px;
}

.pagination {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.pagination button {
  width: 6px;
  height: 6px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: #c8d5e5;
  cursor: pointer;
}

.pagination button.active {
  background: #1981f7;
}

.hot-state {
  height: 230px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #7b89a3;
  font-size: 14px;
}

.state-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #d9e8fb;
  border-top-color: #087aff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1080px) {
  .hot-section {
    height: auto;
  }

  .hot-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .pagination {
    display: none;
  }
}

@media (max-width: 600px) {
  .hot-section {
    padding: 18px 16px;
  }

  .hot-heading > span:last-child {
    display: none;
  }

  .hot-grid {
    grid-template-columns: 1fr;
  }

  .arrow {
    display: none;
  }
}
</style>
