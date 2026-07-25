<script setup lang="ts">
import axios from "axios";
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { message } from "ant-design-vue";

import AppIcon from "../components/AppIcon.vue";
import DestinationCarousel from "../components/DestinationCarousel.vue";
import { fetchHotRecommendations, generateTrip } from "../services/api";
import type { DestinationRecommendationItem, Itinerary, TripRequestPayload } from "../types";

const emit = defineEmits<{
  generated: [itinerary: Itinerary];
}>();

const paceOptions = [
  { label: "悠闲放松", icon: "🌿", value: "轻松" },
  { label: "平衡适中", icon: "⚖", value: "适中" },
  { label: "紧凑充实", icon: "⚡", value: "紧凑" },
];
const hotelOptions = [
  { label: "经济型", icon: "▤" },
  { label: "舒适型", icon: "▥" },
  { label: "豪华型", icon: "♢" },
];
const travelOptions = [
  { label: "自然风景", icon: "♧" },
  { label: "城市漫游", icon: "✾" },
  { label: "亲子友好", icon: "♙" },
  { label: "美食探索", icon: "🌱" },
  { label: "博物馆", icon: "◇" },
  { label: "夜生活", icon: "♟" },
  { label: "轻徒步", icon: "☁" },
  { label: "购物", icon: "♢" },
];
const dietaryOptions = [
  { label: "无辣", icon: "☁" },
  { label: "清淡", icon: "♙" },
  { label: "本地特色", icon: "♟" },
  { label: "海鲜", icon: "♨" },
  { label: "素食", icon: "◇" },
  { label: "低糖", icon: "◇" },
];

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(base: Date | string, amount: number): Date {
  const next = typeof base === "string" ? new Date(`${base}T00:00:00`) : new Date(base);
  next.setDate(next.getDate() + amount);
  return next;
}

const today = new Date();
const formState = reactive({
  destination: "成都",
  startDate: formatDate(addDays(today, 7)),
  endDate: formatDate(addDays(today, 11)),
  travelers: 2,
  travelDays: 5,
  budgetMin: 3000,
  budgetMax: 8000,
  pace: "轻松",
  hotelLevel: "舒适型",
  preferences: ["自然风景", "城市漫游", "美食探索"],
  dietaryPreferences: ["本地特色", "海鲜"],
  notes: "希望体验当地文化，安排一次温泉体验，偏好地铁出行，减少换乘。",
});

const recommendations = ref<DestinationRecommendationItem[]>([]);
const recommendationsLoading = ref(false);
const isSubmitting = ref(false);
const progress = ref(0);
const startDateInput = ref<HTMLInputElement | null>(null);
const endDateInput = ref<HTMLInputElement | null>(null);
let progressTimer: ReturnType<typeof setInterval> | null = null;

function openDatePicker(input: HTMLInputElement | null | undefined) {
  if (!input || input.disabled) return;
  try {
    if (typeof input.showPicker === "function") {
      input.showPicker();
      return;
    }
  } catch {
    // showPicker 在非用户手势或浏览器限制下可能抛错，回退到 focus。
  }
  input.focus();
  input.click();
}

const noteCount = computed(() => formState.notes.length);

function toggleOption(list: string[], value: string) {
  const index = list.indexOf(value);
  if (index >= 0) list.splice(index, 1);
  else list.push(value);
}

function adjustTravelers(amount: number) {
  formState.travelers = Math.max(1, Math.min(20, formState.travelers + amount));
}

function adjustDays(amount: number) {
  formState.travelDays = Math.max(1, Math.min(30, formState.travelDays + amount));
  // 天数步进始终回写结束日期，便于和日期区间保持一致。
  formState.endDate = formatDate(addDays(formState.startDate, formState.travelDays - 1));
}

function onEndDatePicked() {
  if (formState.endDate < formState.startDate) {
    formState.endDate = formState.startDate;
  }
  syncDaysFromDates();
}

function onStartDatePicked() {
  if (formState.endDate < formState.startDate) {
    formState.endDate = formState.startDate;
  }
  syncDaysFromDates();
}

function normalizeBudget(changed: "min" | "max") {
  if (changed === "min" && formState.budgetMin > formState.budgetMax - 500) {
    formState.budgetMin = formState.budgetMax - 500;
  }
  if (changed === "max" && formState.budgetMax < formState.budgetMin + 500) {
    formState.budgetMax = formState.budgetMin + 500;
  }
}

function budgetPercent(value: number) {
  return ((value - 1000) / 14000) * 100;
}

const budgetTrackStyle = computed(() => ({
  background: `linear-gradient(to right, #e2e8f0 0%, #e2e8f0 ${budgetPercent(formState.budgetMin)}%, #0eb885 ${budgetPercent(formState.budgetMin)}%, #0eb885 ${budgetPercent(formState.budgetMax)}%, #e2e8f0 ${budgetPercent(formState.budgetMax)}%, #e2e8f0 100%)`,
}));

function syncDaysFromDates() {
  const start = new Date(`${formState.startDate}T00:00:00`).getTime();
  const end = new Date(`${formState.endDate}T00:00:00`).getTime();
  if (!Number.isNaN(start) && !Number.isNaN(end) && end >= start) {
    formState.travelDays = Math.floor((end - start) / 86400000) + 1;
  }
}

function applyRecommendation(item: DestinationRecommendationItem) {
  formState.destination = item.city;
  formState.travelDays = Math.max(item.suggested_days || 3, 1);
  formState.endDate = formatDate(addDays(formState.startDate, formState.travelDays - 1));
  if (item.default_budget) {
    formState.budgetMin = Math.max(1000, Math.floor(item.default_budget * 0.75 / 500) * 500);
    formState.budgetMax = Math.min(15000, Math.ceil(item.default_budget * 1.5 / 500) * 500);
  }
  if (item.default_pace) formState.pace = item.default_pace;
  const supported = item.default_preferences?.filter((value) => travelOptions.some((opt) => opt.label === value));
  if (supported?.length) formState.preferences = supported;
  message.success(`已为你填入${item.city}的推荐配置`);
}

async function loadRecommendations() {
  recommendationsLoading.value = true;
  try {
    const response = await fetchHotRecommendations();
    recommendations.value = response.items || [];
    if (recommendations.value.length && !recommendations.value.some((item) => item.city === formState.destination)) {
      formState.destination = recommendations.value[0].city;
    }
  } catch (error) {
    console.error(error);
    recommendations.value = [];
  } finally {
    recommendationsLoading.value = false;
  }
}

function startProgress() {
  progress.value = 8;
  if (progressTimer) clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    if (progress.value < 90) {
      const step = progress.value < 45 ? 5 : progress.value < 75 ? 2 : 1;
      progress.value = Math.min(90, progress.value + step);
    }
  }, 650);
}

function stopProgress() {
  if (progressTimer) clearInterval(progressTimer);
  progressTimer = null;
}

async function handleSubmit() {
  if (!formState.destination.trim()) {
    message.warning("请先填写目的地");
    return;
  }

  const payload: TripRequestPayload = {
    destination: formState.destination.trim(),
    start_date: formState.startDate,
    end_date: formState.endDate,
    travelers: formState.travelers,
    budget: formState.budgetMax,
    preferences: formState.preferences,
    pace: formState.pace,
    dietary_preferences: formState.dietaryPreferences,
    hotel_level: formState.hotelLevel,
    special_notes: formState.notes || null,
  };

  isSubmitting.value = true;
  startProgress();
  try {
    const itinerary = await generateTrip(payload);
    progress.value = 100;
    message.success("行程生成成功，已切换到结果页");
    window.setTimeout(() => emit("generated", itinerary), 260);
  } catch (error) {
    console.error(error);
    if (axios.isAxiosError(error)) {
      if (error.code === "ECONNABORTED") message.error("行程生成超时，请稍后再试");
      else if (error.response) message.error(`行程生成失败：后端返回 ${error.response.status}`);
      else message.error("行程生成失败，请检查前后端连接");
    } else {
      message.error("行程生成失败，请检查服务状态");
    }
  } finally {
    stopProgress();
    isSubmitting.value = false;
  }
}

watch(() => formState.startDate, onStartDatePicked);
watch(() => formState.endDate, () => {
  if (formState.endDate < formState.startDate) {
    formState.endDate = formState.startDate;
  }
  syncDaysFromDates();
});

onMounted(loadRecommendations);
onBeforeUnmount(stopProgress);
</script>

<template>
  <section class="home-page">
    <DestinationCarousel
      :items="recommendations"
      :loading="recommendationsLoading"
      :selected-city="formState.destination"
      @select="applyRecommendation"
    />

    <section class="plan-card">
      <header class="plan-title">
        <span class="plan-title__icon"><AppIcon name="route" :size="25" :stroke-width="2.2" /></span>
        <h2>行程规划</h2>
      </header>

      <div class="primary-fields">
        <div class="field field--destination">
          <label>目的地</label>
          <div class="control">
            <AppIcon name="pin" :size="18" />
            <input v-model="formState.destination" type="text" placeholder="输入目的地" />
            <AppIcon name="pin" :size="14" />
          </div>
        </div>

        <div class="field field--dates">
          <label>起止日期</label>
          <div class="control control--date-range">
            <button
              type="button"
              class="date-icon-btn"
              aria-label="选择开始日期"
              @click="openDatePicker(startDateInput)"
            >
              <AppIcon name="calendar" :size="18" />
            </button>
            <input
              ref="startDateInput"
              v-model="formState.startDate"
              type="date"
              :min="formatDate(today)"
              @click="openDatePicker(startDateInput)"
              @keydown.enter.prevent="openDatePicker(startDateInput)"
              @change="onStartDatePicked"
            />
            <span>至</span>
            <input
              ref="endDateInput"
              v-model="formState.endDate"
              type="date"
              :min="formState.startDate"
              @click="openDatePicker(endDateInput)"
              @keydown.enter.prevent="openDatePicker(endDateInput)"
              @change="onEndDatePicked"
            />
          </div>
        </div>

        <div class="field field--travelers">
          <label>人数</label>
          <div class="control step-control">
            <AppIcon name="user" :size="18" />
            <button type="button" aria-label="减少人数" @click="adjustTravelers(-1)">−</button>
            <span>{{ formState.travelers }} 位</span>
            <button type="button" aria-label="增加人数" @click="adjustTravelers(1)">＋</button>
          </div>
        </div>

        <div class="field field--days">
          <label>天数（含出行日）</label>
          <div class="control days-control">
            <button type="button" aria-label="减少天数" @click="adjustDays(-1)">−</button>
            <strong>{{ formState.travelDays }} 天</strong>
            <button type="button" aria-label="增加天数" @click="adjustDays(1)">＋</button>
          </div>
        </div>
      </div>

      <div class="option-row option-row--first">
        <div class="option-group option-group--pace">
          <label>节奏偏好</label>
          <div class="segmented segmented--three">
            <button
              v-for="option in paceOptions"
              :key="option.value"
              type="button"
              :class="{ active: formState.pace === option.value }"
              @click="formState.pace = option.value"
            ><span>{{ option.icon }}</span>{{ option.label }}</button>
          </div>
        </div>
        <div class="option-group option-group--hotel">
          <label>住宿偏好</label>
          <div class="segmented segmented--three">
            <button
              v-for="option in hotelOptions"
              :key="option.label"
              type="button"
              :class="{ active: formState.hotelLevel === option.label }"
              @click="formState.hotelLevel = option.label"
            ><span>{{ option.icon }}</span>{{ option.label }}</button>
          </div>
        </div>
      </div>

      <div class="option-row option-row--second">
        <div class="option-group option-group--budget">
          <div class="group-label-line">
            <label>预算（人均）</label>
            <strong>¥{{ formState.budgetMin.toLocaleString() }}&nbsp; - &nbsp;¥{{ formState.budgetMax.toLocaleString() }}</strong>
          </div>
          <div class="range-wrap" :style="budgetTrackStyle">
            <input v-model.number="formState.budgetMin" type="range" min="1000" max="15000" step="500" aria-label="最低预算" @input="normalizeBudget('min')" />
            <input v-model.number="formState.budgetMax" type="range" min="1000" max="15000" step="500" aria-label="最高预算" @input="normalizeBudget('max')" />
          </div>
          <div class="range-ticks"><span>¥1,000</span><span>¥3,000</span><span>¥8,000</span><span>¥15,000+</span></div>
        </div>
        <div class="option-group option-group--travel">
          <label>旅行偏好 <small>（可多选）</small></label>
          <div class="chips">
            <button
              v-for="option in travelOptions"
              :key="option.label"
              type="button"
              :class="{ active: formState.preferences.includes(option.label) }"
              @click="toggleOption(formState.preferences, option.label)"
            ><span>{{ option.icon }}</span>{{ option.label }}</button>
          </div>
        </div>
      </div>

      <div class="option-row option-row--third">
        <div class="option-group option-group--diet">
          <label>饮食偏好 <small>（可多选）</small></label>
          <div class="chips">
            <button
              v-for="option in dietaryOptions"
              :key="option.label"
              type="button"
              :class="{ active: formState.dietaryPreferences.includes(option.label) }"
              @click="toggleOption(formState.dietaryPreferences, option.label)"
            ><span>{{ option.icon }}</span>{{ option.label }}</button>
          </div>
        </div>
        <div class="option-group option-group--notes">
          <label>额外备注</label>
          <div class="notes-control">
            <textarea v-model="formState.notes" maxlength="200" placeholder="告诉我其他需求…"></textarea>
            <span>{{ noteCount }}/200</span>
          </div>
        </div>
      </div>
    </section>

    <section class="action-card">
      <button type="button" class="start-button" :disabled="isSubmitting" @click="handleSubmit">
        <AppIcon name="sparkles" :size="30" :stroke-width="2.1" />
        <span>{{ isSubmitting ? "正在规划" : "开始规划" }}</span>
      </button>
      <div class="generation-status">
        <span v-if="isSubmitting" class="loader active">
          <i v-for="n in 8" :key="n"></i>
        </span>
        <div class="generation-status__body">
          <strong>{{ isSubmitting ? "生成中…" : "准备就绪" }}</strong>
          <span>{{ isSubmitting ? "AI 正在为您生成个性化行程" : "填写偏好后，点击开始规划" }}</span>
          <div class="progress-row">
            <div class="progress-track"><i :style="{ width: `${isSubmitting ? progress : 0}%` }"></i></div>
            <span>{{ isSubmitting ? `${progress}%` : "" }}</span>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<style scoped>
.home-page {
  display: grid;
  gap: calc(14px * var(--ui-scale));
  min-width: 0;
}

.plan-card {
  height: calc(433px * var(--ui-scale));
  padding: calc(15px * var(--ui-scale)) calc(30px * var(--ui-scale)) calc(12px * var(--ui-scale));
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: calc(18px * var(--ui-scale));
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 14px rgba(35, 65, 95, 0.08);
}

.plan-title {
  height: calc(42px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
}

.plan-title__icon {
  color: #0578f6;
  transform: scale(var(--ui-scale));
}

.plan-title h2 {
  margin: 0;
  color: #111827;
  font-size: calc(20px * var(--ui-scale));
  font-weight: 750;
}

.primary-fields {
  display: grid;
  grid-template-columns: 1.12fr 1.18fr 0.88fr 0.88fr;
  gap: calc(24px * var(--ui-scale));
}

.field,
.option-group {
  min-width: 0;
}

.field label,
.option-group > label,
.group-label-line label {
  display: block;
  margin-bottom: calc(6px * var(--ui-scale));
  color: #243148;
  font-size: calc(14px * var(--ui-scale));
  line-height: 1;
  font-weight: 550;
}

.control {
  height: calc(40px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale));
  color: #4b5f7e;
  border: 1px solid #cbd8e7;
  border-radius: calc(10px * var(--ui-scale));
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.control:focus-within {
  border-color: #2d8cff;
  box-shadow: 0 0 0 3px rgba(45, 140, 255, 0.1);
}

.control input {
  min-width: 0;
  flex: 1;
  height: 100%;
  padding: 0;
  color: #324667;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: calc(13px * var(--ui-scale));
}

.control--date-range {
  gap: calc(8px * var(--ui-scale));
  cursor: pointer;
}

.date-icon-btn {
  display: grid;
  place-items: center;
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
  cursor: pointer;
}

.control--date-range input[type="date"] {
  position: relative;
  width: calc(104px * var(--ui-scale));
  min-width: calc(104px * var(--ui-scale));
  flex: 0 0 auto;
  color: #324667;
  cursor: pointer;
}

/* 保留原生日历入口，但做成透明热区覆盖输入框，保证可点出下拉日历 */
.control--date-range input[type="date"]::-webkit-calendar-picker-indicator {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  cursor: pointer;
  opacity: 0;
}

.control--date-range > span {
  color: #50617b;
  font-size: calc(13px * var(--ui-scale));
}

.step-control {
  justify-content: space-between;
}

.step-control button,
.days-control button {
  border: 0;
  cursor: pointer;
}

.step-control button {
  width: calc(24px * var(--ui-scale));
  height: calc(24px * var(--ui-scale));
  padding: 0;
  color: #586c88;
  border-radius: calc(6px * var(--ui-scale));
  background: #f3f6fa;
  font-size: calc(18px * var(--ui-scale));
  line-height: calc(20px * var(--ui-scale));
}

.step-control span {
  color: #344967;
  font-size: calc(14px * var(--ui-scale));
}

.days-control {
  justify-content: space-between;
  padding: 0 calc(6px * var(--ui-scale));
}

.days-control button {
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  display: grid;
  place-items: center;
  color: #45607d;
  border-radius: calc(6px * var(--ui-scale));
  background: #f3f6fa;
  font-size: calc(19px * var(--ui-scale));
}

.days-control strong {
  color: #324667;
  font-size: calc(14px * var(--ui-scale));
  font-weight: 500;
}

.option-row {
  display: grid;
  gap: calc(26px * var(--ui-scale));
}

.option-row--first {
  grid-template-columns: 1fr 1.16fr;
  margin-top: calc(17px * var(--ui-scale));
}

.option-row--second {
  grid-template-columns: 0.83fr 1.17fr;
  margin-top: calc(17px * var(--ui-scale));
}

.option-row--third {
  grid-template-columns: 0.83fr 1.17fr;
  margin-top: calc(16px * var(--ui-scale));
}

.segmented {
  display: grid;
  gap: calc(10px * var(--ui-scale));
}

.segmented--three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.segmented button,
.chips button {
  height: calc(40px * var(--ui-scale));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: calc(9px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale));
  color: #53617a;
  border: 1px solid #d5dee9;
  border-radius: calc(10px * var(--ui-scale));
  background: #fff;
  cursor: pointer;
  white-space: nowrap;
  font-size: calc(13px * var(--ui-scale));
  transition: all 0.15s ease;
}

.segmented button:hover,
.chips button:hover {
  border-color: #75d6b3;
}

.segmented button.active,
.chips button.active {
  color: #059666;
  border-color: #05b77b;
  background: #f7fffc;
  font-weight: 650;
}

.segmented button span,
.chips button span {
  color: inherit;
  font-size: calc(17px * var(--ui-scale));
  line-height: 1;
}

.group-label-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: calc(8px * var(--ui-scale));
}

.group-label-line label {
  margin: 0;
}

.group-label-line strong {
  color: #008b64;
  font-size: calc(14px * var(--ui-scale));
  font-weight: 600;
}

.range-wrap {
  position: relative;
  height: calc(12px * var(--ui-scale));
  margin: 0 calc(8px * var(--ui-scale));
  border-radius: 8px;
}

.range-wrap input {
  position: absolute;
  inset: calc(-6px * var(--ui-scale)) 0 auto;
  width: 100%;
  height: calc(24px * var(--ui-scale));
  margin: 0;
  appearance: none;
  pointer-events: none;
  background: transparent;
}

.range-wrap input::-webkit-slider-thumb {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  appearance: none;
  pointer-events: auto;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #1188ff;
  box-shadow: 0 1px 5px rgba(0, 73, 166, 0.35);
  cursor: grab;
}

.range-wrap input::-moz-range-thumb {
  width: calc(13px * var(--ui-scale));
  height: calc(13px * var(--ui-scale));
  pointer-events: auto;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #1188ff;
  box-shadow: 0 1px 5px rgba(0, 73, 166, 0.35);
}

.range-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: calc(5px * var(--ui-scale));
  color: #7789a5;
  font-size: calc(10px * var(--ui-scale));
}

.option-group > label small {
  color: #63738c;
  font-size: calc(11px * var(--ui-scale));
  font-weight: 400;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: calc(7px * var(--ui-scale)) calc(10px * var(--ui-scale));
}

.chips button {
  height: calc(30px * var(--ui-scale));
  min-width: calc(92px * var(--ui-scale));
  gap: calc(6px * var(--ui-scale));
  padding: 0 calc(12px * var(--ui-scale));
  border-radius: calc(10px * var(--ui-scale));
  font-size: calc(12px * var(--ui-scale));
}

.chips button span {
  font-size: calc(13px * var(--ui-scale));
}

.option-group--diet .chips button {
  min-width: calc(70px * var(--ui-scale));
}

.notes-control {
  position: relative;
  height: calc(69px * var(--ui-scale));
  overflow: hidden;
  border: 1px solid #cbd8e7;
  border-radius: calc(10px * var(--ui-scale));
  background: #fff;
}

.notes-control:focus-within {
  border-color: #2d8cff;
  box-shadow: 0 0 0 3px rgba(45, 140, 255, 0.1);
}

.notes-control textarea {
  width: 100%;
  height: 100%;
  padding: calc(11px * var(--ui-scale)) calc(54px * var(--ui-scale)) calc(10px * var(--ui-scale)) calc(13px * var(--ui-scale));
  resize: none;
  color: #415473;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: calc(12px * var(--ui-scale));
  line-height: 1.5;
}

.notes-control > span {
  position: absolute;
  right: calc(8px * var(--ui-scale));
  bottom: calc(7px * var(--ui-scale));
  color: #8998af;
  font-size: calc(10px * var(--ui-scale));
}

.action-card {
  height: calc(123px * var(--ui-scale));
  display: grid;
  grid-template-columns: calc(330px * var(--ui-scale)) minmax(0, 1fr);
  align-items: center;
  padding: 0 calc(22px * var(--ui-scale));
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: calc(18px * var(--ui-scale));
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 4px 14px rgba(35, 65, 95, 0.08);
}

.start-button {
  height: calc(98px * var(--ui-scale));
  display: flex;
  align-items: center;
  justify-content: center;
  gap: calc(12px * var(--ui-scale));
  margin-left: calc(-1px * var(--ui-scale));
  color: #fff;
  border: 0;
  border-radius: calc(44px * var(--ui-scale)) 0 0 calc(44px * var(--ui-scale));
  background: linear-gradient(110deg, #0bc6b0 0%, #04b8d9 46%, #0878fb 100%);
  box-shadow: 0 6px 16px rgba(0, 153, 209, 0.26);
  cursor: pointer;
  font-size: calc(23px * var(--ui-scale));
  font-weight: 750;
}

.start-button:hover:not(:disabled) {
  filter: brightness(1.04);
}

.start-button:disabled {
  cursor: wait;
}

.generation-status {
  height: calc(98px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(18px * var(--ui-scale));
  padding: 0 calc(25px * var(--ui-scale)) 0 calc(20px * var(--ui-scale));
  border-top: 1px solid #bed9f6;
  border-right: 1px solid #bed9f6;
  border-bottom: 1px solid #bed9f6;
  border-radius: 0 calc(44px * var(--ui-scale)) calc(44px * var(--ui-scale)) 0;
  background: linear-gradient(100deg, rgba(248, 252, 255, 0.98), #fff);
}

.loader {
  position: relative;
  width: calc(36px * var(--ui-scale));
  height: calc(36px * var(--ui-scale));
  flex: 0 0 auto;
  animation: spin 1s steps(8) infinite;
}

.loader i {
  position: absolute;
  left: calc(16px * var(--ui-scale));
  top: calc(2px * var(--ui-scale));
  width: calc(4px * var(--ui-scale));
  height: calc(9px * var(--ui-scale));
  border-radius: 3px;
  background: #9aaac0;
  transform-origin: calc(2px * var(--ui-scale)) calc(16px * var(--ui-scale));
}

.loader i:nth-child(2) { transform: rotate(45deg); opacity: .85; }
.loader i:nth-child(3) { transform: rotate(90deg); opacity: .72; }
.loader i:nth-child(4) { transform: rotate(135deg); opacity: .59; }
.loader i:nth-child(5) { transform: rotate(180deg); opacity: .46; }
.loader i:nth-child(6) { transform: rotate(225deg); opacity: .36; }
.loader i:nth-child(7) { transform: rotate(270deg); opacity: .25; }
.loader i:nth-child(8) { transform: rotate(315deg); opacity: .16; }

.generation-status__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: calc(6px * var(--ui-scale));
}

.generation-status__body strong {
  color: #16233b;
  font-size: calc(15px * var(--ui-scale));
}

.generation-status__body > span {
  color: #60718c;
  font-size: calc(12px * var(--ui-scale));
}

.progress-row {
  display: flex;
  align-items: center;
  gap: calc(11px * var(--ui-scale));
  min-height: calc(15px * var(--ui-scale));
}

.progress-track {
  flex: 1;
  height: calc(7px * var(--ui-scale));
  overflow: hidden;
  border-radius: 5px;
  background: #e3edf9;
}

.progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2c8cf8, #1d75ef);
  transition: width 0.35s ease;
}

.progress-row > span {
  width: calc(30px * var(--ui-scale));
  color: #4a6791;
  font-size: calc(12px * var(--ui-scale));
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1080px) {
  .plan-card {
    height: auto;
    overflow: visible;
  }

  .primary-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .option-row,
  .option-row--first,
  .option-row--second,
  .option-row--third {
    grid-template-columns: 1fr;
  }

  .option-group {
    margin-bottom: 4px;
  }
}

@media (max-width: 620px) {
  .plan-card {
    padding: 15px;
  }

  .primary-fields {
    grid-template-columns: 1fr;
  }

  .segmented--three {
    grid-template-columns: 1fr;
  }

  .action-card {
    height: auto;
    grid-template-columns: 1fr;
    gap: 10px;
    padding: 12px;
  }

  .start-button,
  .generation-status {
    width: 100%;
    height: 76px;
    margin: 0;
    border: 0;
    border-radius: 18px;
  }
}
</style>
