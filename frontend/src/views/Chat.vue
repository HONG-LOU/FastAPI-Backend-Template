<template>
  <div class="page">
    <header class="topbar">
      <div class="brand">Chat</div>
      <div class="spacer" />
      <div class="me" v-if="meEmail">{{ meEmail }}</div>
      <n-button tertiary @click="onLogout">退出</n-button>
    </header>
    <section class="content">
      <aside class="sidebar">
        <n-input v-model:value="search" placeholder="输入用户ID开始聊天" />
        <n-button block style="margin-top:8px" @click="createDirectRoom">创建直聊</n-button>
      </aside>
      <main class="main">
        <div class="messages" ref="messagesEl">
          <div v-for="m in messages" :key="m.localId || m.id" class="msg" :class="{ me: m.sender_id===meId }">
            <div class="bubble">
              <span>{{ m.content }}</span>
              <span v-if="m.status==='pending'" class="dot-loading" />
              <span v-if="m.status==='failed'" class="failed">发送失败</span>
            </div>
          </div>
        </div>
        <div class="editor">
          <n-input v-model:value="text" type="textarea" :autosize="{minRows:2,maxRows:4}" @keyup.enter.exact.prevent="send" :disabled="sending" />
          <n-button type="primary" @click="send" :disabled="!roomId || sending" :loading="sending">发送</n-button>
        </div>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useMessage, NButton, NInput } from 'naive-ui'
import { api } from '@/api/client'

type Msg = { id?: number; localId?: string; status?: 'pending' | 'failed'; room_id: number; sender_id: number; content: string; created_at: string }

const message = useMessage()
const auth = useAuthStore()
const meId = ref<number | null>(null)
const meEmail = ref<string>('')
const roomId = ref<number | null>(null)
const messages = ref<Msg[]>([])
const messageIds = new Set<number>()
const text = ref('')
const search = ref('')
let ws: WebSocket | null = null
const sending = ref(false)
const messagesEl = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/api/auth/me')
    meId.value = data.id
    meEmail.value = data.email
  } catch (e) {
    // ignore
  }
})

onBeforeUnmount(() => {
  if (ws) ws.close()
})

async function createDirectRoom() {
  const uid = Number(search.value)
  if (!uid) {
    message.warning('请输入有效的用户ID')
    return
  }
  try {
    const { data } = await api.post('/api/chat/rooms/direct', { user_id: uid })
    roomId.value = data.id
    await loadMessages()
    connectWs()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '创建失败')
  }
}

async function loadMessages() {
  if (!roomId.value) return
  const { data } = await api.get(`/api/chat/rooms/${roomId.value}/messages`, { params: { limit: 50 } })
  data.sort((a: Msg, b: Msg) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  messages.value = data
  await nextTick()
  scrollToBottom()
}

function connectWs() {
  if (!roomId.value || !auth.tokens?.access_token) return
  if (ws) ws.close()
  const wsUrl = (import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000') + `/api/chat/ws?room_id=${roomId.value}&token=${auth.tokens.access_token}`
  ws = new WebSocket(wsUrl)
  ws.onmessage = (ev) => {
    try {
      const payload = JSON.parse(ev.data)
      if (payload.type === 'message') {
        addMessage(payload)
        removePendingDuplicate(payload)
      }
    } catch {}
  }
}

async function send() {
  if (!text.value.trim() || !roomId.value || sending.value) return
  try {
    sending.value = true
    const localId = `tmp_${Date.now()}_${Math.random().toString(36).slice(2)}`
    const temp: Msg = {
      localId,
      status: 'pending',
      room_id: roomId.value,
      sender_id: meId.value!,
      content: text.value,
      created_at: new Date().toISOString()
    }
    messages.value.push(temp)
    const contentBackup = text.value
    text.value = ''
    const { data } = await api.post('/api/chat/messages', { room_id: roomId.value, content: contentBackup })
    const idx = messages.value.findIndex(m => m.localId === localId)
    if (idx >= 0) {
      messages.value[idx] = data
      if (data?.id) messageIds.add(data.id)
    } else {
      addMessage(data)
    }
  } catch (e: any) {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.status === 'pending' && m.sender_id === meId.value && m.room_id === roomId.value) {
        m.status = 'failed'
        break
      }
    }
    message.error(e?.response?.data?.message || '发送失败')
  }
  finally {
    sending.value = false
  }
}

function onLogout() {
  auth.logout()
  location.href = '/login'
}

function addMessage(m: Msg) {
  if (m.id && messageIds.has(m.id)) return
  if (m.id) messageIds.add(m.id)
  messages.value.push(m)
  nextTick(scrollToBottom)
}

function removePendingDuplicate(m: Msg) {
  if (!m?.id || !meId.value) return
  const idx = messages.value.findIndex(x => x.status === 'pending' && x.sender_id === meId.value && x.room_id === m.room_id && x.content === m.content)
  if (idx >= 0) messages.value.splice(idx, 1)
}

function scrollToBottom() {
  const el = messagesEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}
</script>

<style scoped>
.page { height: 100%; display: flex; flex-direction: column; }
.topbar { height: 56px; display: flex; align-items: center; padding: 0 16px; border-bottom: 1px solid #eee; gap: 12px; }
.brand { font-weight: 600; }
.spacer { flex: 1; }
.me { color: #6b7280; font-size: 14px; }
.content { flex: 1; display: flex; min-height: 0; }
.sidebar { width: 280px; border-right: 1px solid #eee; padding: 12px; display: flex; flex-direction: column; }
.main { flex: 1; display: flex; flex-direction: column; }
.messages { flex: 1; padding: 12px; overflow: auto; display: flex; flex-direction: column; gap: 8px; }
.msg { display: flex; }
.msg.me { justify-content: flex-end; }
.bubble { background: #f3f4f6; padding: 8px 12px; border-radius: 10px; max-width: 70%; }
.msg.me .bubble { background: #4f46e5; color: #fff; }
.editor { border-top: 1px solid #eee; padding: 8px; display: flex; gap: 8px; }
.dot-loading {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-left: 6px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.5);
  border-top-color: rgba(255,255,255,1);
  animation: spin 0.8s linear infinite;
}
.failed { margin-left: 6px; font-size: 12px; opacity: 0.9; }
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>


