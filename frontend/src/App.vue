<script setup lang="ts">
import { ref } from "vue";

import AppIcon from "./components/AppIcon.vue";
import FloatingChatAssistant from "./components/FloatingChatAssistant.vue";
import type { Itinerary } from "./types";
import History from "./views/History.vue";
import Home from "./views/Home.vue";
import Result from "./views/Result.vue";

const currentView = ref<"home" | "result" | "history">("home");
const latestItinerary = ref<Itinerary | null>(null);

function handleGenerated(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}

function openTrip(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}

function updateCurrentItinerary(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}
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
          历史
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

    <div class="app-body">
      <main class="page-content">
        <Home v-if="currentView === 'home'" @generated="handleGenerated" />
        <Result
          v-else-if="currentView === 'result'"
          :itinerary="latestItinerary"
          @back-home="currentView = 'home'"
          @updated="updateCurrentItinerary"
        />
        <History
          v-else
          :active="currentView === 'history'"
          @open-trip="openTrip"
        />
      </main>

      <aside class="assistant-column">
        <FloatingChatAssistant
          :current-view="currentView"
          :itinerary="latestItinerary"
        />
      </aside>
    </div>
  </div>
</template>

<style scoped>
:global(:root) {
  color-scheme: light;
  font-synthesis: none;
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
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background:
    radial-gradient(circle at 48% -10%, rgba(255, 255, 255, 0.96), transparent 35%),
    #f3f7fb;
}

.nav-bar {
  position: relative;
  z-index: 20;
  height: 64px;
  flex: 0 0 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 18px;
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
  gap: 13px;
  min-width: 255px;
}

.brand__logo {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  color: #fff;
  border-radius: 50%;
  background: linear-gradient(145deg, #1488ff 0%, #0064ed 100%);
  box-shadow: 0 5px 12px rgba(0, 112, 244, 0.25);
}

.brand__title {
  font-size: 22px;
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
  gap: 34px;
}

.nav-tab {
  position: relative;
  min-width: 76px;
  padding: 0 10px;
  border: 0;
  background: transparent;
  color: #17233d;
  font-size: 19px;
  font-weight: 600;
  cursor: pointer;
}

.nav-tab::after {
  content: "";
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 3px;
  height: 4px;
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
  gap: 20px;
}

.icon-button,
.account {
  border: 0;
  color: #253450;
  background: transparent;
  cursor: pointer;
}

.icon-button {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  padding: 0;
}

.account {
  gap: 11px;
  padding: 0;
  font-size: 15px;
}

.account__avatar {
  width: 34px;
  height: 34px;
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
  grid-template-columns: minmax(0, 1fr) clamp(350px, 26.15vw, 402px);
  gap: 12px;
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
  border-radius: 18px;
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
