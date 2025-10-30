import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useMessage, NButton, NInput } from 'naive-ui';
import { api } from '@/api/client';
const message = useMessage();
const auth = useAuthStore();
const meId = ref(null);
const meEmail = ref('');
const roomId = ref(null);
const messages = ref([]);
const text = ref('');
const search = ref('');
let ws = null;
onMounted(async () => {
    try {
        const { data } = await api.get('/api/auth/me');
        meId.value = data.id;
        meEmail.value = data.email;
    }
    catch (e) {
        // ignore
    }
});
onBeforeUnmount(() => {
    if (ws)
        ws.close();
});
async function createDirectRoom() {
    const uid = Number(search.value);
    if (!uid) {
        message.warning('请输入有效的用户ID');
        return;
    }
    try {
        const { data } = await api.post('/api/chat/rooms/direct', { user_id: uid });
        roomId.value = data.id;
        await loadMessages();
        connectWs();
    }
    catch (e) {
        message.error(e?.response?.data?.message || '创建失败');
    }
}
async function loadMessages() {
    if (!roomId.value)
        return;
    const { data } = await api.get(`/api/chat/rooms/${roomId.value}/messages`, { params: { limit: 50 } });
    messages.value = data;
}
function connectWs() {
    if (!roomId.value || !auth.tokens?.access_token)
        return;
    if (ws)
        ws.close();
    const wsUrl = (import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000') + `/api/chat/ws?room_id=${roomId.value}&token=${auth.tokens.access_token}`;
    ws = new WebSocket(wsUrl);
    ws.onmessage = (ev) => {
        try {
            const payload = JSON.parse(ev.data);
            if (payload.type === 'message') {
                messages.value.push(payload);
            }
        }
        catch { }
    };
}
async function send() {
    if (!text.value.trim() || !roomId.value)
        return;
    try {
        const { data } = await api.post('/api/chat/messages', { room_id: roomId.value, content: text.value });
        messages.value.push(data);
        text.value = '';
    }
    catch (e) {
        message.error(e?.response?.data?.message || '发送失败');
    }
}
function onLogout() {
    auth.logout();
    location.href = '/login';
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['msg']} */ ;
/** @type {__VLS_StyleScopedClasses['me']} */ ;
/** @type {__VLS_StyleScopedClasses['msg']} */ ;
/** @type {__VLS_StyleScopedClasses['me']} */ ;
/** @type {__VLS_StyleScopedClasses['bubble']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "page" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.header, __VLS_intrinsicElements.header)({
    ...{ class: "topbar" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "brand" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
    ...{ class: "spacer" },
});
if (__VLS_ctx.meEmail) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "me" },
    });
    (__VLS_ctx.meEmail);
}
const __VLS_0 = {}.NButton;
/** @type {[typeof __VLS_components.NButton, typeof __VLS_components.nButton, typeof __VLS_components.NButton, typeof __VLS_components.nButton, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    tertiary: true,
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    tertiary: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
let __VLS_6;
const __VLS_7 = {
    onClick: (__VLS_ctx.onLogout)
};
__VLS_3.slots.default;
var __VLS_3;
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "content" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
    ...{ class: "sidebar" },
});
const __VLS_8 = {}.NInput;
/** @type {[typeof __VLS_components.NInput, typeof __VLS_components.nInput, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    value: (__VLS_ctx.search),
    placeholder: "输入用户ID开始聊天",
}));
const __VLS_10 = __VLS_9({
    value: (__VLS_ctx.search),
    placeholder: "输入用户ID开始聊天",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
const __VLS_12 = {}.NButton;
/** @type {[typeof __VLS_components.NButton, typeof __VLS_components.nButton, typeof __VLS_components.NButton, typeof __VLS_components.nButton, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    ...{ 'onClick': {} },
    block: true,
    ...{ style: {} },
}));
const __VLS_14 = __VLS_13({
    ...{ 'onClick': {} },
    block: true,
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
let __VLS_16;
let __VLS_17;
let __VLS_18;
const __VLS_19 = {
    onClick: (__VLS_ctx.createDirectRoom)
};
__VLS_15.slots.default;
var __VLS_15;
__VLS_asFunctionalElement(__VLS_intrinsicElements.main, __VLS_intrinsicElements.main)({
    ...{ class: "main" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "messages" },
});
for (const [m] of __VLS_getVForSourceType((__VLS_ctx.messages))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        key: (m.id),
        ...{ class: "msg" },
        ...{ class: ({ me: m.sender_id === __VLS_ctx.meId }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "bubble" },
    });
    (m.content);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "editor" },
});
const __VLS_20 = {}.NInput;
/** @type {[typeof __VLS_components.NInput, typeof __VLS_components.nInput, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    ...{ 'onKeyup': {} },
    value: (__VLS_ctx.text),
    type: "textarea",
    autosize: ({ minRows: 2, maxRows: 4 }),
}));
const __VLS_22 = __VLS_21({
    ...{ 'onKeyup': {} },
    value: (__VLS_ctx.text),
    type: "textarea",
    autosize: ({ minRows: 2, maxRows: 4 }),
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
let __VLS_24;
let __VLS_25;
let __VLS_26;
const __VLS_27 = {
    onKeyup: (__VLS_ctx.send)
};
var __VLS_23;
const __VLS_28 = {}.NButton;
/** @type {[typeof __VLS_components.NButton, typeof __VLS_components.nButton, typeof __VLS_components.NButton, typeof __VLS_components.nButton, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    ...{ 'onClick': {} },
    type: "primary",
    disabled: (!__VLS_ctx.roomId),
}));
const __VLS_30 = __VLS_29({
    ...{ 'onClick': {} },
    type: "primary",
    disabled: (!__VLS_ctx.roomId),
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
let __VLS_32;
let __VLS_33;
let __VLS_34;
const __VLS_35 = {
    onClick: (__VLS_ctx.send)
};
__VLS_31.slots.default;
var __VLS_31;
/** @type {__VLS_StyleScopedClasses['page']} */ ;
/** @type {__VLS_StyleScopedClasses['topbar']} */ ;
/** @type {__VLS_StyleScopedClasses['brand']} */ ;
/** @type {__VLS_StyleScopedClasses['spacer']} */ ;
/** @type {__VLS_StyleScopedClasses['me']} */ ;
/** @type {__VLS_StyleScopedClasses['content']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar']} */ ;
/** @type {__VLS_StyleScopedClasses['main']} */ ;
/** @type {__VLS_StyleScopedClasses['messages']} */ ;
/** @type {__VLS_StyleScopedClasses['msg']} */ ;
/** @type {__VLS_StyleScopedClasses['bubble']} */ ;
/** @type {__VLS_StyleScopedClasses['editor']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            NButton: NButton,
            NInput: NInput,
            meId: meId,
            meEmail: meEmail,
            roomId: roomId,
            messages: messages,
            text: text,
            search: search,
            createDirectRoom: createDirectRoom,
            send: send,
            onLogout: onLogout,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
