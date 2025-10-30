<template>
  <div class="wrap">
    <n-card class="card" title="登录">
      <n-form :model="form" :rules="rules" @submit.prevent="onSubmit">
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="form.email" placeholder="you@example.com" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input v-model:value="form.password" type="password" show-password-on="mousedown" />
        </n-form-item>
        <div class="actions">
          <n-button type="primary" attr-type="submit" :loading="loading">登录</n-button>
          <n-button quaternary @click="$router.push({ name: 'register' })">去注册</n-button>
        </div>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api, setTokensFromUrlOnce } from '@/api/client'
import { useMessage, NCard, NForm, NFormItem, NInput, NButton } from 'naive-ui'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const auth = useAuthStore()

const form = reactive({ email: '', password: '' })
const rules = {
  email: { required: true, message: '请输入邮箱', trigger: ['input', 'blur'] },
  password: { required: true, message: '请输入密码', trigger: ['input', 'blur'] }
}
const loading = ref(false)

onMounted(() => {
  setTokensFromUrlOnce()
  if (auth.isAuthenticated) {
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  }
})

async function onSubmit() {
  loading.value = true
  try {
    const { data } = await api.post('/api/auth/login', {
      email: form.email,
      password: form.password
    })
    auth.setTokens(data)
    message.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.wrap { min-height: 100%; display: flex; align-items: center; justify-content: center; background: #f7f7fb; padding: 24px; }
.card { width: 380px; }
.actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>


