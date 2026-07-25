<script setup lang="ts">
import { ref, watch } from "vue";

import AppIcon from "./components/AppIcon.vue";
import FloatingChatAssistant from "./components/FloatingChatAssistant.vue";
import type { Itinerary } from "./types";
import {
  loadCurrentView,
  loadLatestItinerary,
  saveCurrentView,
  saveLatestItinerary,
  type AppView,
} from "./utils/clientCache";
import History from "./views/History.vue";
import Home from "./views/Home.vue";
import Result from "./views/Result.vue";

const restoredItinerary = loadLatestItinerary();
const restoredView = loadCurrentView();

function resolveInitialView(): AppView {
  if (restoredView === "result" && restoredItinerary) return "result";
  if (restoredView === "history" || restoredView === "home") return restoredView;
  // 有缓存行程但上次不在结果页时，仍回到规划页；结果页按需挂载
  return "home";
}

const latestItinerary = ref<Itinerary | null>(restoredItinerary);
const currentView = ref<AppView>(resolveInitialView());
// 结果/行程页一旦挂载就保活（v-show），避免切换时销毁重建
const resultMounted = ref(currentView.value === "result");
const historyMounted = ref(currentView.value === "history");

function showResult(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  saveLatestItinerary(itinerary);
  resultMounted.value = true;
  currentView.value = "result";
}

function handleGenerated(itinerary: Itinerary) {
  showResult(itinerary);
}

function openTrip(itinerary: Itinerary) {
  showResult(itinerary);
}

function updateCurrentItinerary(itinerary: Itinerary) {
  showResult(itinerary);
}

watch(currentView, (view) => {
  if (view === "result") resultMounted.value = true;
  if (view === "history") historyMounted.value = true;
  saveCurrentView(view);
});
</script>

<template>
  <div class="app-shell">
    <header class="nav-bar">
      <div class="brand">
        <span class="brand__logo"><AppIcon name="plane" :size="24" :stroke-width="2.3" /></span>
        <span class="brand__title">智能旅行助手</span>
      </div>

      <nav class="nav-tabs" aria-label="主导航">
        <button
          :class="['nav-tab', { 'nav-tab--active': currentView === 'home' }]"
          @click="currentView = 'home'"
        >
          规划
        </button>
        <button
          :class="['nav-tab', { 'nav-tab--active': currentView === 'result' }]"
          @click="currentView = 'result'"
        >
          结果
        </button>
        <button
          :class="['nav-tab', { 'nav-tab--active': currentView === 'history' }]"
          @click="currentView = 'history'"
        >
          我的行程
        </button>
      </nav>

      <div class="account-area">
        <button class="icon-button" type="button" aria-label="切换深色模式">
          <AppIcon name="moon" :size="22" />
        </button>
        <button class="account" type="button">
          <span class="account__avatar" aria-hidden="true"></span>
          <span>我的账户</span>
          <AppIcon name="chevron-down" :size="15" />
        </button>
      </div>
    </header>

    <div :class="['app-body', { 'app-body--wide': currentView !== 'home' }]">
      <main class="page-content">
        <Home v-if="currentView === 'home'" @generated="handleGenerated" />
        <!-- 保活：隐藏时不销毁，避免结果↔行程切换时重复请求与闪加载 -->
        <History
          v-if="historyMounted"
          v-show="currentView === 'history'"
          :active="currentView === 'history'"
          @open-trip="openTrip"
        />
        <!-- 保活：隐藏时不销毁，避免地图实例与天气状态丢失 -->
        <Result
          v-if="resultMounted"
          v-show="currentView === 'result'"
          :active="currentView === 'result'"
          :itinerary="latestItinerary"
          @back-home="currentView = 'home'"
          @updated="updateCurrentItinerary"
        />
      </main>

      <!-- AI 助手仅挂载在规划页，结果/我的行程不展示 -->
      <aside v-if="currentView === 'home'" class="assistant-column">
        <FloatingChatAssistant :itinerary="latestItinerary" />
      </aside>
    </div>
  </div>
</template>

<style scoped>
:global(:root) {
  color-scheme: light;
  font-synthesis: none;
  --ui-scale: 1;
}

@media (min-width: 1900px) and (min-height: 900px) {
  :global(:root) {
    --ui-scale: 1.2;
  }
}

@media (min-width: 2200px) and (min-height: 1100px) {
  :global(:root) {
    --ui-scale: 1.35;
  }
}

@media (min-width: 2450px) and (min-height: 1200px) {
  :global(:root) {
    --ui-scale: 1.5;
  }
}

:global(body) {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  font-family: Inter, "SF Pro Text", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
  background: #f3f7fb;
  color: #172033;
  -webkit-font-smoothing: antialiased;
}

:global(button),
:global(input),
:global(textarea),
:global(select) {
  font: inherit;
}

:global(*) {
  box-sizing: border-box;
}

.app-shell {
  min-height: 100vh;
  height: 100vh;
  padding: calc(8px * var(--ui-scale));
  display: flex;
  flex-direction: column;
  gap: calc(12px * var(--ui-scale));
  background:
    radial-gradient(circle at 48% -10%, rgba(255, 255, 255, 0.96), transparent 35%),
    #f3f7fb;
}

.nav-bar {
  position: relative;
  z-index: 20;
  height: calc(64px * var(--ui-scale));
  flex: 0 0 calc(64px * var(--ui-scale));
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 calc(20px * var(--ui-scale));
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: calc(18px * var(--ui-scale));
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 5px 16px rgba(30, 58, 95, 0.14);
}

.brand,
.account-area,
.account {
  display: flex;
  align-items: center;
}

.brand {
  gap: calc(13px * var(--ui-scale));
  min-width: calc(255px * var(--ui-scale));
}

.brand__logo {
  width: calc(38px * var(--ui-scale));
  height: calc(38px * var(--ui-scale));
  display: grid;
  place-items: center;
  color: #fff;
  border-radius: 50%;
  background: linear-gradient(145deg, #1488ff 0%, #0064ed 100%);
  box-shadow: 0 5px 12px rgba(0, 112, 244, 0.25);
}

.brand__title {
  font-size: calc(22px * var(--ui-scale));
  line-height: 1;
  color: #0f1728;
  font-weight: 750;
  letter-spacing: -0.4px;
  white-space: nowrap;
}

.nav-tabs {
  position: absolute;
  left: 50%;
  top: 0;
  height: 100%;
  transform: translateX(-50%);
  display: flex;
  align-items: stretch;
  gap: calc(34px * var(--ui-scale));
}

.nav-tab {
  position: relative;
  min-width: calc(76px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale));
  border: 0;
  background: transparent;
  color: #17233d;
  font-size: calc(19px * var(--ui-scale));
  font-weight: 600;
  cursor: pointer;
}

.nav-tab::after {
  content: "";
  position: absolute;
  left: calc(10px * var(--ui-scale));
  right: calc(10px * var(--ui-scale));
  bottom: calc(3px * var(--ui-scale));
  height: calc(4px * var(--ui-scale));
  border-radius: 4px;
  background: transparent;
}

.nav-tab:hover,
.nav-tab--active {
  color: #006bfa;
}

.nav-tab--active::after {
  background: #0879ff;
  box-shadow: 0 2px 5px rgba(8, 121, 255, 0.28);
}

.account-area {
  gap: calc(20px * var(--ui-scale));
}

.icon-button,
.account {
  border: 0;
  color: #253450;
  background: transparent;
  cursor: pointer;
}

.icon-button {
  width: calc(36px * var(--ui-scale));
  height: calc(36px * var(--ui-scale));
  display: grid;
  place-items: center;
  padding: 0;
}

.account {
  gap: calc(11px * var(--ui-scale));
  padding: 0;
  font-size: calc(15px * var(--ui-scale));
}

.account__avatar {
  width: calc(34px * var(--ui-scale));
  height: calc(34px * var(--ui-scale));
  flex: 0 0 auto;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.8);
  background:
    linear-gradient(to bottom, rgba(83, 185, 247, 0.84) 0 45%, transparent 45%),
    radial-gradient(ellipse at 60% 72%, #315c18 0 21%, transparent 22%),
    radial-gradient(ellipse at 28% 76%, #6d8d2b 0 27%, transparent 28%),
    #c6d8a0;
  box-shadow: 0 2px 8px rgba(30, 64, 100, 0.18);
}

.app-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) calc(402px * var(--ui-scale));
  gap: calc(12px * var(--ui-scale));
}

.app-body--wide {
  grid-template-columns: minmax(0, 1fr);
}

.page-content,
.assistant-column {
  min-width: 0;
  min-height: 0;
}

.page-content {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #d7e1ec transparent;
}

.assistant-column {
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.82);
  border-radius: calc(18px * var(--ui-scale));
  background: #fff;
  box-shadow: 0 4px 14px rgba(35, 65, 95, 0.11);
}

@media (max-width: 1080px) {
  .app-body {
    grid-template-columns: minmax(0, 1fr) 330px;
  }

  .nav-tabs {
    gap: 8px;
  }

  .brand {
    min-width: 210px;
  }

  .brand__title {
    font-size: 18px;
  }
}

@media (max-width: 840px) {
  .app-shell {
    height: auto;
    min-height: 100vh;
  }

  .app-body {
    grid-template-columns: 1fr;
  }

  .assistant-column {
    height: 620px;
  }

  .account span:not(.account__avatar) {
    display: none;
  }

  .brand__title {
    display: none;
  }

  .brand {
    min-width: auto;
  }
}

@media (max-width: 560px) {
  .app-shell {
    padding: 5px;
    gap: 8px;
  }

  .nav-bar {
    padding: 0 10px;
  }

  .nav-tabs {
    gap: 0;
  }

  .nav-tab {
    min-width: 58px;
    font-size: 15px;
  }

  .account-area {
    gap: 2px;
  }

  .account__avatar {
    width: 30px;
    height: 30px;
  }
}
</style>
