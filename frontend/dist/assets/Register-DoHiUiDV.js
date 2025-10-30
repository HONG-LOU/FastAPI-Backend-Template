import{x as Q,y as h,z as m,A as z,B as d,C as _,D as X,E as Y,d as M,G as i,H as Z,N as ee,I as oe,J as re,W as se,K as ne,S as te,L as le,M as ae,O as L,P as ie,Q as H,R as p,T as ce,r as E,p as de,c as ue,g as C,w as x,h as f,l as W,U as ge,f as pe,k as fe,e as ve,m as $,a as he}from"./index-D1dR0X0d.js";import{r as me,a as Ce,g as be,u as xe,N as k,B as A,_ as Ie}from"./_plugin-vue_export-helper-BD59ZGkT.js";import{N as ye,a as ze,b as N}from"./FormItem-B257f-0z.js";const we={iconMargin:"11px 8px 0 12px",iconMarginRtl:"11px 12px 0 8px",iconSize:"24px",closeIconSize:"16px",closeSize:"20px",closeMargin:"13px 14px 0 0",closeMarginRtl:"13px 0 0 14px",padding:"13px"};function Se(t){const{lineHeight:o,borderRadius:s,fontWeightStrong:v,baseColor:n,dividerColor:u,actionColor:w,textColor1:c,textColor2:e,closeColorHover:a,closeColorPressed:b,closeIconColor:I,closeIconColorHover:y,closeIconColorPressed:l,infoColor:r,successColor:S,warningColor:R,errorColor:T,fontSize:P}=t;return Object.assign(Object.assign({},we),{fontSize:P,lineHeight:o,titleFontWeight:v,borderRadius:s,border:`1px solid ${u}`,color:w,titleTextColor:c,iconColor:e,contentTextColor:e,closeBorderRadius:s,closeColorHover:a,closeColorPressed:b,closeIconColor:I,closeIconColorHover:y,closeIconColorPressed:l,borderInfo:`1px solid ${h(n,m(r,{alpha:.25}))}`,colorInfo:h(n,m(r,{alpha:.08})),titleTextColorInfo:c,iconColorInfo:r,contentTextColorInfo:e,closeColorHoverInfo:a,closeColorPressedInfo:b,closeIconColorInfo:I,closeIconColorHoverInfo:y,closeIconColorPressedInfo:l,borderSuccess:`1px solid ${h(n,m(S,{alpha:.25}))}`,colorSuccess:h(n,m(S,{alpha:.08})),titleTextColorSuccess:c,iconColorSuccess:S,contentTextColorSuccess:e,closeColorHoverSuccess:a,closeColorPressedSuccess:b,closeIconColorSuccess:I,closeIconColorHoverSuccess:y,closeIconColorPressedSuccess:l,borderWarning:`1px solid ${h(n,m(R,{alpha:.33}))}`,colorWarning:h(n,m(R,{alpha:.08})),titleTextColorWarning:c,iconColorWarning:R,contentTextColorWarning:e,closeColorHoverWarning:a,closeColorPressedWarning:b,closeIconColorWarning:I,closeIconColorHoverWarning:y,closeIconColorPressedWarning:l,borderError:`1px solid ${h(n,m(T,{alpha:.25}))}`,colorError:h(n,m(T,{alpha:.08})),titleTextColorError:c,iconColorError:T,contentTextColorError:e,closeColorHoverError:a,closeColorPressedError:b,closeIconColorError:I,closeIconColorHoverError:y,closeIconColorPressedError:l})}const Re={common:Q,self:Se},Te=z("alert",`
 line-height: var(--n-line-height);
 border-radius: var(--n-border-radius);
 position: relative;
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-color);
 text-align: start;
 word-break: break-word;
`,[d("border",`
 border-radius: inherit;
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 transition: border-color .3s var(--n-bezier);
 border: var(--n-border);
 pointer-events: none;
 `),_("closable",[z("alert-body",[d("title",`
 padding-right: 24px;
 `)])]),d("icon",{color:"var(--n-icon-color)"}),z("alert-body",{padding:"var(--n-padding)"},[d("title",{color:"var(--n-title-text-color)"}),d("content",{color:"var(--n-content-text-color)"})]),X({originalTransition:"transform .3s var(--n-bezier)",enterToProps:{transform:"scale(1)"},leaveToProps:{transform:"scale(0.9)"}}),d("icon",`
 position: absolute;
 left: 0;
 top: 0;
 align-items: center;
 justify-content: center;
 display: flex;
 width: var(--n-icon-size);
 height: var(--n-icon-size);
 font-size: var(--n-icon-size);
 margin: var(--n-icon-margin);
 `),d("close",`
 transition:
 color .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 position: absolute;
 right: 0;
 top: 0;
 margin: var(--n-close-margin);
 `),_("show-icon",[z("alert-body",{paddingLeft:"calc(var(--n-icon-margin-left) + var(--n-icon-size) + var(--n-icon-margin-right))"})]),_("right-adjust",[z("alert-body",{paddingRight:"calc(var(--n-close-size) + var(--n-padding) + 2px)"})]),z("alert-body",`
 border-radius: var(--n-border-radius);
 transition: border-color .3s var(--n-bezier);
 `,[d("title",`
 transition: color .3s var(--n-bezier);
 font-size: 16px;
 line-height: 19px;
 font-weight: var(--n-title-font-weight);
 `,[Y("& +",[d("content",{marginTop:"9px"})])]),d("content",{transition:"color .3s var(--n-bezier)",fontSize:"var(--n-font-size)"})]),d("icon",{transition:"color .3s var(--n-bezier)"})]),Pe=Object.assign(Object.assign({},L.props),{title:String,showIcon:{type:Boolean,default:!0},type:{type:String,default:"default"},bordered:{type:Boolean,default:!0},closable:Boolean,onClose:Function,onAfterLeave:Function,onAfterHide:Function}),_e=M({name:"Alert",inheritAttrs:!1,props:Pe,slots:Object,setup(t){const{mergedClsPrefixRef:o,mergedBorderedRef:s,inlineThemeDisabled:v,mergedRtlRef:n}=ae(t),u=L("Alert","-alert",Te,Re,t,o),w=ie("Alert",n,o),c=H(()=>{const{common:{cubicBezierEaseInOut:l},self:r}=u.value,{fontSize:S,borderRadius:R,titleFontWeight:T,lineHeight:P,iconSize:j,iconMargin:B,iconMarginRtl:F,closeIconSize:O,closeBorderRadius:V,closeSize:q,closeMargin:U,closeMarginRtl:D,padding:K}=r,{type:g}=t,{left:G,right:J}=be(B);return{"--n-bezier":l,"--n-color":r[p("color",g)],"--n-close-icon-size":O,"--n-close-border-radius":V,"--n-close-color-hover":r[p("closeColorHover",g)],"--n-close-color-pressed":r[p("closeColorPressed",g)],"--n-close-icon-color":r[p("closeIconColor",g)],"--n-close-icon-color-hover":r[p("closeIconColorHover",g)],"--n-close-icon-color-pressed":r[p("closeIconColorPressed",g)],"--n-icon-color":r[p("iconColor",g)],"--n-border":r[p("border",g)],"--n-title-text-color":r[p("titleTextColor",g)],"--n-content-text-color":r[p("contentTextColor",g)],"--n-line-height":P,"--n-border-radius":R,"--n-font-size":S,"--n-title-font-weight":T,"--n-icon-size":j,"--n-icon-margin":B,"--n-icon-margin-rtl":F,"--n-close-size":q,"--n-close-margin":U,"--n-close-margin-rtl":D,"--n-padding":K,"--n-icon-margin-left":G,"--n-icon-margin-right":J}}),e=v?ce("alert",H(()=>t.type[0]),c,t):void 0,a=E(!0),b=()=>{const{onAfterLeave:l,onAfterHide:r}=t;l&&l(),r&&r()};return{rtlEnabled:w,mergedClsPrefix:o,mergedBordered:s,visible:a,handleCloseClick:()=>{var l;Promise.resolve((l=t.onClose)===null||l===void 0?void 0:l.call(t)).then(r=>{r!==!1&&(a.value=!1)})},handleAfterLeave:()=>{b()},mergedTheme:u,cssVars:v?void 0:c,themeClass:e?.themeClass,onRender:e?.onRender}},render(){var t;return(t=this.onRender)===null||t===void 0||t.call(this),i(le,{onAfterLeave:this.handleAfterLeave},{default:()=>{const{mergedClsPrefix:o,$slots:s}=this,v={class:[`${o}-alert`,this.themeClass,this.closable&&`${o}-alert--closable`,this.showIcon&&`${o}-alert--show-icon`,!this.title&&this.closable&&`${o}-alert--right-adjust`,this.rtlEnabled&&`${o}-alert--rtl`],style:this.cssVars,role:"alert"};return this.visible?i("div",Object.assign({},Z(this.$attrs,v)),this.closable&&i(ee,{clsPrefix:o,class:`${o}-alert__close`,onClick:this.handleCloseClick}),this.bordered&&i("div",{class:`${o}-alert__border`}),this.showIcon&&i("div",{class:`${o}-alert__icon`,"aria-hidden":"true"},me(s.icon,()=>[i(oe,{clsPrefix:o},{default:()=>{switch(this.type){case"success":return i(te,null);case"info":return i(ne,null);case"warning":return i(se,null);case"error":return i(re,null);default:return null}}})])),i("div",{class:[`${o}-alert-body`,this.mergedBordered&&`${o}-alert-body--bordered`]},Ce(s.header,n=>{const u=n||this.title;return u?i("div",{class:`${o}-alert-body__title`},u):null}),s.default&&i("div",{class:`${o}-alert-body__content`},s))):null}})}}),$e={class:"wrap"},Ee={class:"actions"},Be=M({__name:"Register",setup(t){const o=xe(),s=de({email:"",password:""}),v={email:{required:!0,message:"请输入邮箱",trigger:["input","blur"]},password:{required:!0,message:"请输入密码",trigger:["input","blur"]}},n=E(!1),u=E(!1);async function w(){n.value=!0;try{await he.post("/api/auth/register",{email:s.email,password:s.password}),u.value=!0,o.success("验证邮件已发送，请检查邮箱")}catch(c){o.error(c?.response?.data?.message||"注册失败")}finally{n.value=!1}}return(c,e)=>(W(),ue("div",$e,[C(f(ye),{class:"card",title:"注册"},{default:x(()=>[C(f(ze),{model:s,rules:v,onSubmit:fe(w,["prevent"])},{default:x(()=>[C(f(N),{label:"邮箱",path:"email"},{default:x(()=>[C(f(k),{value:s.email,"onUpdate:value":e[0]||(e[0]=a=>s.email=a),placeholder:"you@example.com"},null,8,["value"])]),_:1}),C(f(N),{label:"密码",path:"password"},{default:x(()=>[C(f(k),{value:s.password,"onUpdate:value":e[1]||(e[1]=a=>s.password=a),type:"password","show-password-on":"mousedown"},null,8,["value"])]),_:1}),ve("div",Ee,[C(f(A),{type:"primary","attr-type":"submit",loading:n.value},{default:x(()=>[...e[3]||(e[3]=[$("注册",-1)])]),_:1},8,["loading"]),C(f(A),{quaternary:"",onClick:e[2]||(e[2]=a=>c.$router.push({name:"login"}))},{default:x(()=>[...e[4]||(e[4]=[$("返回登录",-1)])]),_:1})])]),_:1},8,["model"]),u.value?(W(),ge(f(_e),{key:0,type:"success",title:"验证邮件已发送",style:{"margin-top":"12px"}},{default:x(()=>[...e[5]||(e[5]=[$(" 请前往邮箱点击验证链接完成注册。 ",-1)])]),_:1})):pe("",!0)]),_:1})]))}}),Ae=Ie(Be,[["__scopeId","data-v-2fa7208e"]]);export{Ae as default};
