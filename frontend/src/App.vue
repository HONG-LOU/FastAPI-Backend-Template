<template>
  <n-message-provider>
    <router-view />
  </n-message-provider>
</template>

<script setup lang="ts">
import { NMessageProvider } from 'naive-ui'
</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
}
</style>


