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
  autoDays: true,
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
let progressTimer: ReturnType<typeof setInterval> | null = null;

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
  if (formState.autoDays) {
    formState.endDate = formatDate(addDays(formState.startDate, formState.travelDays - 1));
  }
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

watch(() => formState.startDate, () => {
  if (formState.autoDays) formState.endDate = formatDate(addDays(formState.startDate, formState.travelDays - 1));
  else syncDaysFromDates();
});
watch(() => formState.endDate, syncDaysFromDates);

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
            <AppIcon name="calendar" :size="18" />
            <input v-model="formState.startDate" type="date" />
            <span>至</span>
            <input v-model="formState.endDate" type="date" :min="formState.startDate" :disabled="formState.autoDays" />
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
          <label class="toggle-label">
            <span>自动天数（含出行日）</span>
            <button
              type="button"
              :class="['switch', { active: formState.autoDays }]"
              role="switch"
              :aria-checked="formState.autoDays"
              @click="formState.autoDays = !formState.autoDays"
            ><span></span></button>
          </label>
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
        <span :class="['loader', { active: isSubmitting }]">
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
  gap: 14px;
  min-width: 0;
}

.plan-card {
  height: 433px;
  padding: 15px 30px 12px;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 14px rgba(35, 65, 95, 0.08);
}

.plan-title {
  height: 42px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.plan-title__icon {
  color: #0578f6;
}

.plan-title h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
  font-weight: 750;
}

.primary-fields {
  display: grid;
  grid-template-columns: 1.12fr 1.18fr 0.88fr 0.88fr;
  gap: 24px;
}

.field,
.option-group {
  min-width: 0;
}

.field label,
.option-group > label,
.group-label-line label {
  display: block;
  margin-bottom: 6px;
  color: #243148;
  font-size: 14px;
  line-height: 1;
  font-weight: 550;
}

.control {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  color: #4b5f7e;
  border: 1px solid #cbd8e7;
  border-radius: 10px;
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
  font-size: 13px;
}

.control input[type="date"]::-webkit-calendar-picker-indicator {
  display: none;
}

.control--date-range {
  gap: 8px;
}

.control--date-range input {
  width: 88px;
}

.control--date-range input:disabled {
  color: #324667;
  opacity: 1;
}

.control--date-range > span {
  color: #50617b;
  font-size: 13px;
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
  width: 24px;
  height: 24px;
  padding: 0;
  color: #586c88;
  border-radius: 6px;
  background: #f3f6fa;
  font-size: 18px;
  line-height: 20px;
}

.step-control span {
  color: #344967;
  font-size: 14px;
}

.toggle-label {
  display: flex !important;
  align-items: center;
  justify-content: space-between;
}

.switch {
  width: 32px;
  height: 18px;
  padding: 2px;
  border: 0;
  border-radius: 10px;
  background: #cbd5e1;
  cursor: pointer;
  transition: background 0.18s ease;
}

.switch span {
  display: block;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform 0.18s ease;
}

.switch.active {
  background: #08b87c;
}

.switch.active span {
  transform: translateX(14px);
}

.days-control {
  justify-content: space-between;
  padding: 0 6px;
}

.days-control button {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  color: #45607d;
  border-radius: 6px;
  background: #f3f6fa;
  font-size: 19px;
}

.days-control strong {
  color: #324667;
  font-size: 14px;
  font-weight: 500;
}

.option-row {
  display: grid;
  gap: 26px;
}

.option-row--first {
  grid-template-columns: 1fr 1.16fr;
  margin-top: 17px;
}

.option-row--second {
  grid-template-columns: 0.83fr 1.17fr;
  margin-top: 17px;
}

.option-row--third {
  grid-template-columns: 0.83fr 1.17fr;
  margin-top: 16px;
}

.segmented {
  display: grid;
  gap: 10px;
}

.segmented--three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.segmented button,
.chips button {
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 10px;
  color: #53617a;
  border: 1px solid #d5dee9;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  white-space: nowrap;
  font-size: 13px;
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
  font-size: 17px;
  line-height: 1;
}

.group-label-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.group-label-line label {
  margin: 0;
}

.group-label-line strong {
  color: #008b64;
  font-size: 14px;
  font-weight: 600;
}

.range-wrap {
  position: relative;
  height: 12px;
  margin: 0 8px;
  border-radius: 8px;
}

.range-wrap input {
  position: absolute;
  inset: -6px 0 auto;
  width: 100%;
  height: 24px;
  margin: 0;
  appearance: none;
  pointer-events: none;
  background: transparent;
}

.range-wrap input::-webkit-slider-thumb {
  width: 18px;
  height: 18px;
  appearance: none;
  pointer-events: auto;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #1188ff;
  box-shadow: 0 1px 5px rgba(0, 73, 166, 0.35);
  cursor: grab;
}

.range-wrap input::-moz-range-thumb {
  width: 13px;
  height: 13px;
  pointer-events: auto;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #1188ff;
  box-shadow: 0 1px 5px rgba(0, 73, 166, 0.35);
}

.range-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  color: #7789a5;
  font-size: 10px;
}

.option-group > label small {
  color: #63738c;
  font-size: 11px;
  font-weight: 400;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px 10px;
}

.chips button {
  height: 30px;
  min-width: 92px;
  gap: 6px;
  padding: 0 12px;
  border-radius: 10px;
  font-size: 12px;
}

.chips button span {
  font-size: 13px;
}

.option-group--diet .chips button {
  min-width: 70px;
}

.notes-control {
  position: relative;
  height: 69px;
  overflow: hidden;
  border: 1px solid #cbd8e7;
  border-radius: 10px;
  background: #fff;
}

.notes-control:focus-within {
  border-color: #2d8cff;
  box-shadow: 0 0 0 3px rgba(45, 140, 255, 0.1);
}

.notes-control textarea {
  width: 100%;
  height: 100%;
  padding: 11px 54px 10px 13px;
  resize: none;
  color: #415473;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: 12px;
  line-height: 1.5;
}

.notes-control > span {
  position: absolute;
  right: 8px;
  bottom: 7px;
  color: #8998af;
  font-size: 10px;
}

.action-card {
  height: 123px;
  display: grid;
  grid-template-columns: 330px minmax(0, 325px);
  align-items: center;
  padding-left: 22px;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 4px 14px rgba(35, 65, 95, 0.08);
}

.start-button {
  height: 98px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-left: -1px;
  color: #fff;
  border: 0;
  border-radius: 44px 0 0 44px;
  background: linear-gradient(110deg, #0bc6b0 0%, #04b8d9 46%, #0878fb 100%);
  box-shadow: 0 6px 16px rgba(0, 153, 209, 0.26);
  cursor: pointer;
  font-size: 23px;
  font-weight: 750;
}

.start-button:hover:not(:disabled) {
  filter: brightness(1.04);
}

.start-button:disabled {
  cursor: wait;
}

.generation-status {
  height: 98px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 25px 0 20px;
  border-top: 1px solid #bed9f6;
  border-right: 1px solid #bed9f6;
  border-bottom: 1px solid #bed9f6;
  border-radius: 0 44px 44px 0;
  background: linear-gradient(100deg, rgba(248, 252, 255, 0.98), #fff);
}

.loader {
  position: relative;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
}

.loader i {
  position: absolute;
  left: 16px;
  top: 2px;
  width: 4px;
  height: 9px;
  border-radius: 3px;
  background: #9aaac0;
  transform-origin: 2px 16px;
}

.loader i:nth-child(2) { transform: rotate(45deg); opacity: .85; }
.loader i:nth-child(3) { transform: rotate(90deg); opacity: .72; }
.loader i:nth-child(4) { transform: rotate(135deg); opacity: .59; }
.loader i:nth-child(5) { transform: rotate(180deg); opacity: .46; }
.loader i:nth-child(6) { transform: rotate(225deg); opacity: .36; }
.loader i:nth-child(7) { transform: rotate(270deg); opacity: .25; }
.loader i:nth-child(8) { transform: rotate(315deg); opacity: .16; }
.loader.active { animation: spin 1s steps(8) infinite; }

.generation-status__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.generation-status__body strong {
  color: #16233b;
  font-size: 15px;
}

.generation-status__body > span {
  color: #60718c;
  font-size: 12px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 15px;
}

.progress-track {
  flex: 1;
  height: 7px;
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
  width: 30px;
  color: #4a6791;
  font-size: 12px;
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
