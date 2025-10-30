<template>
  <div class="wrap">
    <n-card class="card" title="注册">
      <n-form :model="form" :rules="rules" @submit.prevent="onSubmit">
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="form.email" placeholder="you@example.com" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input v-model:value="form.password" type="password" show-password-on="mousedown" />
        </n-form-item>
        <div class="actions">
          <n-button type="primary" attr-type="submit" :loading="loading">注册</n-button>
          <n-button quaternary @click="$router.push({ name: 'login' })">返回登录</n-button>
        </div>
      </n-form>
      <n-alert v-if="sent" type="success" title="验证邮件已发送" style="margin-top: 12px;">
        请前往邮箱点击验证链接完成注册。
      </n-alert>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useMessage, NCard, NForm, NFormItem, NInput, NButton, NAlert } from 'naive-ui'
import { api } from '@/api/client'

const message = useMessage()
const form = reactive({ email: '', password: '' })
const rules = {
  email: { required: true, message: '请输入邮箱', trigger: ['input', 'blur'] },
  password: { required: true, message: '请输入密码', trigger: ['input', 'blur'] }
}
const loading = ref(false)
const sent = ref(false)

async function onSubmit() {
  loading.value = true
  try {
    await api.post('/api/auth/register', {
      email: form.email,
      password: form.password
    })
    sent.value = true
    message.success('验证邮件已发送，请检查邮箱')
  } catch (e: any) {
    message.error(e?.response?.data?.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.wrap { min-height: 100%; display: flex; align-items: center; justify-content: center; background: #f7f7fb; padding: 24px; }
.card { width: 420px; }
.actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>


