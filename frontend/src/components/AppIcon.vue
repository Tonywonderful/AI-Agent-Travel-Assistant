<script setup lang="ts">
defineProps<{
  name: string;
  size?: number;
  strokeWidth?: number;
}>();
</script>

<template>
  <svg
    class="app-icon"
    :width="size || 20"
    :height="size || 20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth || 1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'plane'">
      <path d="M22 2 9.5 14.5" />
      <path d="m22 2-7.5 20-4.2-7.8L2 10l20-8Z" />
    </template>
    <template v-else-if="name === 'moon'">
      <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" />
    </template>
    <template v-else-if="name === 'chevron-down'">
      <path d="m6 9 6 6 6-6" />
    </template>
    <template v-else-if="name === 'chevron-up'">
      <path d="m18 15-6-6-6 6" />
    </template>
    <template v-else-if="name === 'chevron-left'">
      <path d="m15 18-6-6 6-6" />
    </template>
    <template v-else-if="name === 'chevron-right'">
      <path d="m9 18 6-6-6-6" />
    </template>
    <template v-else-if="name === 'fire'">
      <path d="M12 22c4.4 0 7-3.3 7-7.2 0-3.5-2-6.2-4.5-8.8-.4 2-1.3 3.1-2.5 4.1.1-3.2-1.5-6-4-8.1.1 3.8-3 6.1-3 10.4C5 17.8 8.1 22 12 22Z" />
      <path d="M9.5 17.5c0 2 1.1 3.4 2.6 4.3 1.6-.8 2.7-2.3 2.7-4.2 0-1.8-1-3.2-2.2-4.6-.3 1.2-.8 2-1.6 2.7-.1-1.5-.7-2.8-1.6-3.8.1 2.1.1 3.4.1 5.6Z" />
    </template>
    <template v-else-if="name === 'route'">
      <circle cx="6" cy="19" r="2" />
      <circle cx="18" cy="5" r="2" />
      <path d="M8 19h2.5a3 3 0 0 0 0-6h-1a3 3 0 0 1 0-6H16" />
    </template>
    <template v-else-if="name === 'pin'">
      <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
      <circle cx="12" cy="10" r="2.5" />
    </template>
    <template v-else-if="name === 'calendar'">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </template>
    <template v-else-if="name === 'refresh'">
      <path d="M20 6v5h-5" />
      <path d="M4 18v-5h5" />
      <path d="M6.1 9A7 7 0 0 1 18 6l2 5M4 13l2 5a7 7 0 0 0 11.9-3" />
    </template>
    <template v-else-if="name === 'pie-chart'">
      <path d="M11 3a9 9 0 1 0 9 9h-9V3Z" />
      <path d="M14 3.6A8.5 8.5 0 0 1 20.4 10H14V3.6Z" />
    </template>
    <template v-else-if="name === 'filter'">
      <path d="M4 5h16l-6.5 7.5V19l-3 1v-7.5L4 5Z" />
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </template>
    <template v-else-if="name === 'check-circle'">
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12 2.5 2.5L16 9" />
    </template>
    <template v-else-if="name === 'edit'">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z" />
    </template>
    <template v-else-if="name === 'user'">
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
    </template>
    <template v-else-if="name === 'weather'">
      <path d="M17.5 19H7a5 5 0 1 1 1.3-9.8A6.5 6.5 0 0 1 20 13a4 4 0 0 1-2.5 6Z" />
    </template>
    <template v-else-if="name === 'sun'">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41" />
    </template>
    <template v-else-if="name === 'bot'">
      <rect x="4" y="7" width="16" height="13" rx="5" />
      <path d="M12 3v4M9 13h.01M15 13h.01M8 17h8" />
    </template>
    <template v-else-if="name === 'users'">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </template>
    <template v-else-if="name === 'wallet'">
      <rect x="2" y="5" width="20" height="15" rx="3" />
      <path d="M16 12h6M2 9h20" />
    </template>
    <template v-else-if="name === 'map'">
      <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z" />
      <path d="M9 3v15M15 6v15" />
    </template>
    <template v-else-if="name === 'trash'">
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 11v5M14 11v5" />
    </template>
    <template v-else-if="name === 'send'">
      <path d="m22 2-7 20-4-9-9-4 20-7Z" />
      <path d="M22 2 11 13" />
    </template>
    <template v-else-if="name === 'sparkles'">
      <path d="m12 3 1.2 3.1L16 7.5l-2.8 1.4L12 12l-1.2-3.1L8 7.5l2.8-1.4L12 3ZM5 13l.9 2.1L8 16l-2.1.9L5 19l-.9-2.1L2 16l2.1-.9L5 13ZM19 12l.9 2.1L22 15l-2.1.9L19 18l-.9-2.1L16 15l2.1-.9L19 12Z" />
    </template>
  </svg>
</template>

<style scoped>
.app-icon {
  display: block;
  flex: 0 0 auto;
}
</style>
