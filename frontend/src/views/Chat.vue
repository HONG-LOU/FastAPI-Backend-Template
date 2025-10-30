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
        <div class="users" v-if="allUsers?.length">
          <div class="section-title">所有用户</div>
          <div
            v-for="u in filteredUsers"
            :key="u.id"
            class="user"
            @click="startDirectWithUser(u.id)"
          >
            <div class="title">{{ u.name || u.email }}</div>
          </div>
        </div>
        <div class="convs" v-if="groups.length">
          <div
            v-for="c in groups"
            :key="c.id"
            class="conv"
            :class="{ active: c.id===roomId }"
            @click="selectRoom(c.id)"
          >
            <div class="title">{{ c.name || c.peer?.name || c.peer?.email || '群聊' }}</div>
            <div class="preview">{{ c.last_message?.content || ' ' }}</div>
          </div>
        </div>
        <div class="tools">
          <n-input v-model:value="search" placeholder="输入邮箱或用户ID开始聊天" />
          <n-button block style="margin-top:8px" @click="createDirectRoom">创建直聊</n-button>
          <n-input v-model:value="groupName" placeholder="群名称（可选）" style="margin-top:12px" />
          <n-input v-model:value="groupMembers" placeholder="群成员（用逗号分隔邮箱或ID）" style="margin-top:8px" />
          <n-button block style="margin-top:8px" @click="createGroupRoom">创建群聊</n-button>
        </div>
      </aside>
      <main class="main">
        <div class="room-header" v-if="currentRoom">
          <div class="room-title">{{ currentRoom.name || currentRoom.peer?.name || currentRoom.peer?.email || '群聊' }}</div>
          <div class="spacer" />
          <n-button v-if="currentRoom.type==='group'" size="small" @click="onAddMember">添加成员</n-button>
        </div>
        <div class="messages" ref="messagesEl">
          <div v-for="m in messages" :key="m.localId || m.id" class="msg" :class="{ me: m.sender_id===meId }">
            <div class="bubble" :class="{ 'image-only': !m.content && m.attachments?.length && m.attachments.every(a => a.content_type && a.content_type.startsWith('image/')) }">
              <span v-if="m.content">{{ m.content }}</span>
              <template v-if="m.attachments?.length">
                <div class="attachments" :class="{ 'image-only': !m.content && m.attachments?.length && m.attachments.every(a => a.content_type && a.content_type.startsWith('image/')) }">
                  <template v-for="a in m.attachments" :key="a.id">
                    <img
                      v-if="a.content_type && a.content_type.startsWith('image/')"
                      :src="attSrcMap[a.id] || a.url"
                      class="image-att"
                      @error="() => fetchImageBlob(a)"
                      @load="scheduleScrollToBottom"
                    />
                    <div v-else class="file-card">
                      <div class="file-icon">📄</div>
                      <div class="file-info">
                        <div class="file-name" :title="a.filename">{{ a.filename }}</div>
                        <div class="file-meta">{{ formatSize(a.size_bytes) }}</div>
                      </div>
                      <a class="file-action" :href="a.url" :download="a.filename" target="_blank" rel="noopener noreferrer">下载</a>
                    </div>
                  </template>
                </div>
              </template>
              <span v-if="m.status==='pending'" class="dot-loading" />
              <span v-if="m.status==='failed'" class="failed">发送失败</span>
            </div>
          </div>
          <div ref="bottomEl"></div>
        </div>
        <div class="editor" @paste.prevent="onPaste" @dragover.prevent @drop.prevent="onDrop">
          <input ref="fileInputRef" type="file" multiple style="display:none" @change="onPickFiles" />
          <n-input ref="editorRef" v-model:value="text" type="textarea" :autosize="{minRows:2,maxRows:4}" @keyup.enter.exact.prevent="send" />
          <n-button @click="pickFiles" :disabled="!roomId || sending">上传文件</n-button>
          <n-button type="primary" @click="send" :disabled="!roomId || sending" :loading="sending">发送</n-button>
        </div>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useMessage, NButton, NInput } from 'naive-ui'
import { api } from '@/api/client'

type Att = { id: number; url: string; filename: string; content_type: string; size_bytes: number }
type Msg = { id?: number; localId?: string; status?: 'pending' | 'failed'; room_id: number; sender_id: number; content: string | null; created_at: string; attachments?: Att[] }

const message = useMessage()
const auth = useAuthStore()
const meId = ref<number | null>(null)
const meEmail = ref<string>('')
const roomId = ref<number | null>(null)
const messages = ref<Msg[]>([])
const conversations = ref<any[]>([])
const allUsers = ref<any[]>([])
const messageIds = new Set<number>()
const text = ref('')
const search = ref('')
const groupName = ref('')
const groupMembers = ref('')
let ws: WebSocket | null = null
let wsReconnectTimer: number | null = null
const currentRoom = computed(() => conversations.value.find((c: any) => c.id === roomId.value))
const filteredUsers = computed(() => {
  const kw = (search.value || '').trim().toLowerCase()
  const base = allUsers.value.filter((u: any) => u.id !== meId.value)
  if (!kw) return base
  return base.filter((u: any) =>
    (u.name && u.name.toLowerCase().includes(kw)) || (u.email && u.email.toLowerCase().includes(kw))
  )
})
const groups = computed(() => conversations.value.filter((c: any) => c.type === 'group'))
const sending = ref(false)
const messagesEl = ref<HTMLElement | null>(null)
const bottomEl = ref<HTMLElement | null>(null)
const editorRef = ref<InstanceType<typeof NInput> | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const audioCtx = ref<AudioContext | null>(null)
const attSrcMap = ref<Record<number, string>>({})

function ensureAudioContext() {
  try {
    if (!audioCtx.value) {
      const AC = (window as any).AudioContext || (window as any).webkitAudioContext
      if (!AC) return
      audioCtx.value = new AC()
    }
    if (audioCtx.value && audioCtx.value.state === 'suspended') {
      audioCtx.value.resume().catch(() => {})
    }
  } catch {}
}

function playBeep() {
  try {
    ensureAudioContext()
    const ctx = audioCtx.value
    if (!ctx) return
    const oscillator = ctx.createOscillator()
    const gain = ctx.createGain()
    oscillator.type = 'sine'
    oscillator.frequency.value = 880
    // 加大音量并延长一点时长，避免爆音仍保留快速淡入淡出
    const now = ctx.currentTime
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.3, now + 0.015)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.55)
    oscillator.connect(gain)
    gain.connect(ctx.destination)
    oscillator.start(now)
    oscillator.stop(now + 0.6)
  } catch {}
}

function requestNotificationPermission() {
  if (typeof Notification === 'undefined') return
  if (Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {})
  }
}

function showDesktopNotification(m: Msg) {
  if (typeof Notification === 'undefined') return
  if (document.visibilityState === 'visible') return
  if (Notification.permission !== 'granted') return
  try {
    const n = new Notification('新消息', { body: m.content || undefined })
    n.onclick = () => { window.focus(); n.close() }
  } catch {}
}

onMounted(async () => {
  try {
    const { data } = await api.get('/api/auth/me')
    meId.value = data.id
    meEmail.value = data.email
  } catch (e) {
    // ignore
  }
  // 预先请求通知权限，并在首次交互后恢复音频上下文
  requestNotificationPermission()
  window.addEventListener('click', ensureAudioContext, { once: true })
  window.addEventListener('keydown', ensureAudioContext, { once: true })
  await Promise.all([loadConversations(), loadAllUsers()])
  const cached = Number(localStorage.getItem('selected_room_id') || 0)
  if (cached && conversations.value.some(c => c.id === cached)) {
    await selectRoom(cached)
  } else if (conversations.value.length) {
    await selectRoom(conversations.value[0].id)
  }
})

onBeforeUnmount(() => {
  if (ws) ws.close()
})

async function createDirectRoom() {
  const raw = (search.value || '').trim()
  if (!raw) {
    message.warning('请输入邮箱或用户ID')
    return
  }
  let payload: any
  if (raw.includes('@')) payload = { email: raw }
  else {
    const uid = Number(raw)
    if (!uid) {
      message.warning('请输入有效的邮箱或用户ID')
      return
    }
    payload = { user_id: uid }
  }
  try {
    const { data } = await api.post('/api/chat/rooms/direct', payload)
    roomId.value = data.id
    await loadMessages()
    connectWs()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '创建失败')
  }
}

async function startDirectWithUser(uid: number) {
  if (!uid || uid === meId.value) return
  try {
    const { data } = await api.post('/api/chat/rooms/direct', { user_id: uid })
    roomId.value = data.id
    await loadMessages()
    connectWs()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '创建失败')
  }
}

async function createGroupRoom() {
  const membersRaw = (groupMembers.value || '').trim()
  if (!membersRaw) {
    message.warning('请输入群成员（逗号分隔邮箱或ID）')
    return
  }
  const parts = membersRaw.split(/[,，\s]+/).map(s => s.trim()).filter(Boolean)
  const emails: string[] = []
  const user_ids: number[] = []
  for (const p of parts) {
    if (p.includes('@')) emails.push(p)
    else {
      const n = Number(p)
      if (n) user_ids.push(n)
    }
  }
  if (!emails.length && !user_ids.length) {
    message.warning('请输入有效的邮箱或用户ID')
    return
  }
  const payload: any = { name: groupName.value || undefined }
  if (emails.length) payload.emails = emails
  if (user_ids.length) payload.user_ids = user_ids
  try {
    const { data } = await api.post('/api/chat/rooms/group', payload)
    roomId.value = data.id
    await loadMessages()
    connectWs()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '创建失败')
  }
}

function parseSingleUser(input: string): { emails?: string[]; user_ids?: number[] } | null {
  const raw = (input || '').trim()
  if (!raw) return null
  if (raw.includes('@')) return { emails: [raw] }
  const n = Number(raw)
  if (n) return { user_ids: [n] }
  return null
}

async function onAddMember() {
  if (!roomId.value || currentRoom?.value?.type !== 'group') {
    message.warning('仅群聊可添加成员')
    return
  }
  const raw = window.prompt('输入成员邮箱或ID：')
  if (raw == null) return
  const payload = parseSingleUser(raw)
  if (!payload) {
    message.warning('请输入有效的邮箱或用户ID')
    return
  }
  try {
    await api.post(`/api/chat/rooms/${roomId.value}/participants`, payload)
    message.success('已添加')
  } catch (e: any) {
    const msg = e?.response?.data?.message || '添加失败'
    message.error(msg.includes('no valid participants') ? '用户不存在' : msg)
  }
}

async function loadMessages() {
  if (!roomId.value) return
  const { data } = await api.get(`/api/chat/rooms/${roomId.value}/messages`, { params: { limit: 50 } })
  data.sort((a: Msg, b: Msg) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  messages.value = data
  await nextTick()
  scheduleScrollToBottom()
}

async function loadConversations() {
  const { data } = await api.get('/api/chat/rooms')
  conversations.value = data
}

async function loadAllUsers() {
  try {
    const { data } = await api.get('/api/profile/users', { params: { limit: 500 } })
    allUsers.value = data
  } catch {}
}

async function selectRoom(id: number) {
  if (roomId.value === id) return
  roomId.value = id
  localStorage.setItem('selected_room_id', String(id))
  await loadMessages()
  connectWs()
}

// 当 access_token 变化时，为当前房间重连 WebSocket 以使用最新凭据
watch(() => auth.tokens?.access_token, (val, oldVal) => {
  if (val && val !== oldVal && roomId.value) {
    connectWs()
  }
})

function connectWs() {
  if (!roomId.value || !auth.tokens?.access_token) return
  if (ws) ws.close()
  const wsBase = (import.meta.env as any).VITE_WS_BASE_URL ?? `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`
  const wsUrl = `${wsBase}/api/chat/ws?room_id=${roomId.value}&token=${auth.tokens.access_token}`
  ws = new WebSocket(wsUrl)
  ws.onmessage = (ev) => {
    try {
      const payload = JSON.parse(ev.data)
      if (payload.type === 'message') {
        addMessage(payload)
        removePendingDuplicate(payload)
        if (payload.sender_id !== meId.value) {
          // 仅在页面不在前台或未聚焦时播放提示音
          if (document.visibilityState !== 'visible' || !document.hasFocus()) {
            playBeep()
          }
          showDesktopNotification(payload)
        }
      }
    } catch {}
  }
  ws.onopen = () => {
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer)
      wsReconnectTimer = null
    }
  }
  ws.onerror = () => {
    try { ws?.close() } catch {}
  }
  ws.onclose = () => {
    if (wsReconnectTimer) return
    wsReconnectTimer = window.setTimeout(() => {
      wsReconnectTimer = null
      connectWs()
    }, 1000)
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
    scheduleScrollToBottom()
    const contentBackup = text.value
    text.value = ''
    const { data } = await api.post('/api/chat/messages', { room_id: roomId.value, content: contentBackup, attachment_ids: [] })
    const idx = messages.value.findIndex(m => m.localId === localId)
    if (idx >= 0) {
      messages.value[idx] = data
      if (data?.id) messageIds.add(data.id)
      scheduleScrollToBottom()
    } else {
      addMessage(data)
    }
    const ci = conversations.value.findIndex(c => c.id === roomId.value)
    if (ci >= 0) conversations.value[ci] = { ...conversations.value[ci], last_message: data }
  } catch (e: any) {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.status === 'pending' && m.sender_id === meId.value && m.room_id === roomId.value) {
        m.status = 'failed'
        scheduleScrollToBottom()
        break
      }
    }
    message.error(e?.response?.data?.message || '发送失败')
  }
  finally {
    sending.value = false
    await nextTick()
    scheduleScrollToBottom()
    editorRef.value?.focus()
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
  scheduleScrollToBottom()
}

function removePendingDuplicate(m: Msg) {
  if (!m?.id || !meId.value) return
  const sameAtt = (a?: Att[], b?: Att[]) => {
    const aa = (a || []).map(x => `${x.filename}:${x.size_bytes}`).sort().join('|')
    const bb = (b || []).map(x => `${x.filename}:${x.size_bytes}`).sort().join('|')
    return aa === bb
  }
  const idx = messages.value.findIndex(x => x.status === 'pending' && x.sender_id === meId.value && x.room_id === m.room_id && x.content === m.content && sameAtt(x.attachments, m.attachments))
  if (idx >= 0) messages.value.splice(idx, 1)
}

function scrollToBottom() {
  // 优先使用底部锚点，布局尚未稳定时更可靠
  const anchor = bottomEl.value
  if (anchor && anchor.scrollIntoView) {
    try { anchor.scrollIntoView({ behavior: 'auto', block: 'end' }) } catch {}
  } else {
    const el = messagesEl.value
    if (el) el.scrollTop = el.scrollHeight
  }
}

function scheduleScrollToBottom() {
  // 使用双 rAF 等待布局与绘制完成后再滚动，提升稳定性
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      scrollToBottom()
    })
  })
}

async function fetchImageBlob(a: Att) {
  if (attSrcMap.value[a.id]) return
  try {
    const resp = await api.get(a.url, { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    attSrcMap.value = { ...attSrcMap.value, [a.id]: url }
  } catch {}
}

function formatSize(n: number) {
  if (!n && n !== 0) return ''
  const kb = 1024, mb = 1024 * 1024, gb = 1024 * 1024 * 1024
  if (n >= gb) return (n / gb).toFixed(2) + ' GB'
  if (n >= mb) return (n / mb).toFixed(2) + ' MB'
  if (n >= kb) return (n / kb).toFixed(2) + ' KB'
  return n + ' B'
}

function pickFiles() {
  fileInputRef.value?.click()
}

async function onPickFiles(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input?.files || !roomId.value) return
  const files = Array.from(input.files)
  input.value = ''
  await uploadAndSend(files)
}

async function onPaste(e: ClipboardEvent) {
  const files = Array.from(e.clipboardData?.files || [])
  if (!files.length || !roomId.value) return
  await uploadAndSend(files)
}

async function onDrop(e: DragEvent) {
  const files = Array.from(e.dataTransfer?.files || [])
  if (!files.length || !roomId.value) return
  await uploadAndSend(files)
}

async function uploadAndSend(files: File[]) {
  try {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    const { data } = await api.post('/api/chat/attachments', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    if (!Array.isArray(data) || !data.length) return
    let usedCaption = false
    for (const att of data) {
      const localId = `tmp_${Date.now()}_${Math.random().toString(36).slice(2)}`
      const temp: Msg = {
        localId,
        status: 'pending',
        room_id: roomId.value!,
        sender_id: meId.value!,
        content: usedCaption ? null : (text.value || null),
        created_at: new Date().toISOString(),
        attachments: [{ id: att.id, url: att.url, filename: att.filename, content_type: att.content_type, size_bytes: att.size_bytes }]
      }
      messages.value.push(temp)
      scheduleScrollToBottom()
      const payload = { room_id: roomId.value, content: temp.content, attachment_ids: [att.id] }
      if (!usedCaption && temp.content) { text.value = '' }
      usedCaption = true
      try {
        const { data: msgData } = await api.post('/api/chat/messages', payload)
        const idx = messages.value.findIndex(m => m.localId === localId)
        if (idx >= 0) {
          messages.value[idx] = msgData
          if (msgData?.id) messageIds.add(msgData.id)
          scheduleScrollToBottom()
        }
      } catch (e: any) {
        const idx = messages.value.findIndex(m => m.localId === localId)
        if (idx >= 0) messages.value[idx].status = 'failed'
      }
    }
  } catch {}
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
.convs { flex: 0 0 auto; max-height: 40%; overflow: auto; display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }
.users { flex: 1; overflow: auto; display: flex; flex-direction: column; gap: 4px; }
.section-title { font-size: 12px; color: #6b7280; margin-bottom: 6px; }
.user { padding: 6px 8px; border-radius: 8px; cursor: pointer; }
.user:hover { background: #f9fafb; }
.conv { padding: 8px; border-radius: 8px; cursor: pointer; }
.conv.active { background: #eef2ff; }
.conv .title { font-weight: 600; font-size: 14px; }
.conv .preview { color: #6b7280; font-size: 12px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tools { border-top: 1px solid #eee; padding-top: 8px; margin-top: 8px; }
.main { flex: 1; display: flex; flex-direction: column; }
.room-header { height: 44px; display: flex; align-items: center; padding: 0 12px; border-bottom: 1px solid #eee; }
.room-title { font-weight: 600; }
.messages { flex: 1; padding: 12px; overflow: auto; display: flex; flex-direction: column; gap: 8px; }
.msg { display: flex; }
.msg.me { justify-content: flex-end; }
.bubble { background: #f3f4f6; padding: 8px 12px; border-radius: 10px; max-width: 70%; white-space: pre-wrap; }
.msg.me .bubble { background: #4f46e5; color: #fff; }
.bubble.image-only { background: transparent; padding: 0; border: 1px solid #e5e7eb; border-radius: 10px; display: inline-block; max-width: unset; overflow: hidden; }
.msg.me .bubble.image-only { background: transparent; color: inherit; border-color: rgba(0,0,0,0.15); }
.editor { border-top: 1px solid #eee; padding: 8px; display: flex; gap: 8px; }
.attachments { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-top: 6px; max-width: 360px; }
.attachments.image-only { display: inline-grid; grid-template-columns: 1fr; gap: 0; margin-top: 0; max-width: unset; }
.image-att { max-width: 100%; max-height: 240px; width: auto; height: auto; object-fit: contain; border-radius: 8px; display: block; }
.file-card { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 8px; min-width: 220px; max-width: 320px; padding: 8px 10px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
.msg.me .file-card { background: rgba(255,255,255,0.95); }
.file-icon { font-size: 18px; }
.file-info { min-width: 0; }
.file-name { font-weight: 600; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
.file-meta { color: #6b7280; font-size: 12px; margin-top: 2px; }
.file-action { color: #4f46e5; font-weight: 600; text-decoration: none; }
.file-action:hover { text-decoration: underline; }
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


