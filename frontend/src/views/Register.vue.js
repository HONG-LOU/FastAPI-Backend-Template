import { reactive, ref } from 'vue';
import { useMessage, NCard, NForm, NFormItem, NInput, NButton, NAlert } from 'naive-ui';
import { api } from '@/api/client';
const message = useMessage();
const form = reactive({ email: '', password: '' });
const rules = {
    email: { required: true, message: '请输入邮箱', trigger: ['input', 'blur'] },
    password: { required: true, message: '请输入密码', trigger: ['input', 'blur'] }
};
const loading = ref(false);
const sent = ref(false);
async function onSubmit() {
    loading.value = true;
    try {
        await api.post('/api/auth/register', {
            email: form.email,
            password: form.password
        });
        sent.value = true;
        message.success('验证邮件已发送，请检查邮箱');
    }
    catch (e) {
        message.error(e?.response?.data?.message || '注册失败');
    }
    finally {
        loading.value = false;
    }
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "wrap" },
});
const __VLS_0 = {}.NCard;
/** @type {[typeof __VLS_components.NCard, typeof __VLS_components.nCard, typeof __VLS_components.NCard, typeof __VLS_components.nCard, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "card" },
    title: "注册",
}));
const __VLS_2 = __VLS_1({
    ...{ class: "card" },
    title: "注册",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
const __VLS_4 = {}.NForm;
/** @type {[typeof __VLS_components.NForm, typeof __VLS_components.nForm, typeof __VLS_components.NForm, typeof __VLS_components.nForm, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    ...{ 'onSubmit': {} },
    model: (__VLS_ctx.form),
    rules: (__VLS_ctx.rules),
}));
const __VLS_6 = __VLS_5({
    ...{ 'onSubmit': {} },
    model: (__VLS_ctx.form),
    rules: (__VLS_ctx.rules),
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
let __VLS_8;
let __VLS_9;
let __VLS_10;
const __VLS_11 = {
    onSubmit: (__VLS_ctx.onSubmit)
};
__VLS_7.slots.default;
const __VLS_12 = {}.NFormItem;
/** @type {[typeof __VLS_components.NFormItem, typeof __VLS_components.nFormItem, typeof __VLS_components.NFormItem, typeof __VLS_components.nFormItem, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    label: "邮箱",
    path: "email",
}));
const __VLS_14 = __VLS_13({
    label: "邮箱",
    path: "email",
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_15.slots.default;
const __VLS_16 = {}.NInput;
/** @type {[typeof __VLS_components.NInput, typeof __VLS_components.nInput, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    value: (__VLS_ctx.form.email),
    placeholder: "you@example.com",
}));
const __VLS_18 = __VLS_17({
    value: (__VLS_ctx.form.email),
    placeholder: "you@example.com",
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
var __VLS_15;
const __VLS_20 = {}.NFormItem;
/** @type {[typeof __VLS_components.NFormItem, typeof __VLS_components.nFormItem, typeof __VLS_components.NFormItem, typeof __VLS_components.nFormItem, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    label: "密码",
    path: "password",
}));
const __VLS_22 = __VLS_21({
    label: "密码",
    path: "password",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_23.slots.default;
const __VLS_24 = {}.NInput;
/** @type {[typeof __VLS_components.NInput, typeof __VLS_components.nInput, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    value: (__VLS_ctx.form.password),
    type: "password",
    showPasswordOn: "mousedown",
}));
const __VLS_26 = __VLS_25({
    value: (__VLS_ctx.form.password),
    type: "password",
    showPasswordOn: "mousedown",
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
var __VLS_23;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "actions" },
});
const __VLS_28 = {}.NButton;
/** @type {[typeof __VLS_components.NButton, typeof __VLS_components.nButton, typeof __VLS_components.NButton, typeof __VLS_components.nButton, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    type: "primary",
    attrType: "submit",
    loading: (__VLS_ctx.loading),
}));
const __VLS_30 = __VLS_29({
    type: "primary",
    attrType: "submit",
    loading: (__VLS_ctx.loading),
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
__VLS_31.slots.default;
var __VLS_31;
const __VLS_32 = {}.NButton;
/** @type {[typeof __VLS_components.NButton, typeof __VLS_components.nButton, typeof __VLS_components.NButton, typeof __VLS_components.nButton, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    ...{ 'onClick': {} },
    quaternary: true,
}));
const __VLS_34 = __VLS_33({
    ...{ 'onClick': {} },
    quaternary: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
let __VLS_36;
let __VLS_37;
let __VLS_38;
const __VLS_39 = {
    onClick: (...[$event]) => {
        __VLS_ctx.$router.push({ name: 'login' });
    }
};
__VLS_35.slots.default;
var __VLS_35;
var __VLS_7;
if (__VLS_ctx.sent) {
    const __VLS_40 = {}.NAlert;
    /** @type {[typeof __VLS_components.NAlert, typeof __VLS_components.nAlert, typeof __VLS_components.NAlert, typeof __VLS_components.nAlert, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        type: "success",
        title: "验证邮件已发送",
        ...{ style: {} },
    }));
    const __VLS_42 = __VLS_41({
        type: "success",
        title: "验证邮件已发送",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_43.slots.default;
    var __VLS_43;
}
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['actions']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            NCard: NCard,
            NForm: NForm,
            NFormItem: NFormItem,
            NInput: NInput,
            NButton: NButton,
            NAlert: NAlert,
            form: form,
            rules: rules,
            loading: loading,
            sent: sent,
            onSubmit: onSubmit,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
