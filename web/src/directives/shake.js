// v-shake 指令：绑定在 .t-input-wrap 容器上，根据错误布尔值触发表单校验抖动。
// 要求结构：.t-input-wrap > (.t-input[承载可见边框] + .t-error-msg[错误信息])。
// 行为：错误置真 → 加 .is-error（显红边框+显示文案）并播放 .is-shaking；
// 经过 --revert-hold 后自动回退；错误置假 → 立即清除。
const shake = {
  mounted(el, binding) {
    if (binding.value) trigger(el, true)
  },
  updated(el, binding) {
    if (binding.value !== binding.oldValue) trigger(el, binding.value)
  },
  unmounted(el) {
    if (el._revertTimer) clearTimeout(el._revertTimer)
  }
}

function trigger(wrap, isError) {
  const input = wrap.querySelector('.t-input')
  const cs = getComputedStyle(document.documentElement)
  const num = (name, fb) => {
    const v = parseFloat(cs.getPropertyValue(name))
    return Number.isFinite(v) ? v : fb
  }

  if (isError) {
    wrap.classList.add('is-error')
    if (input) input.classList.add('is-error')
    if (input) {
      input.classList.remove('is-shaking')
      void input.offsetWidth // 强制 reflow 后重加，保证抖动可重播
      input.classList.add('is-shaking')
      const shakeMs = num('--shake-dur-a', 80) * 2 + num('--shake-dur-b', 60) * 2
      setTimeout(() => input.classList.remove('is-shaking'), shakeMs + 20)
    }
    const hold = num('--revert-hold', 3000)
    if (wrap._revertTimer) clearTimeout(wrap._revertTimer)
    wrap._revertTimer = setTimeout(() => {
      wrap._revertTimer = null
      wrap.classList.remove('is-error')
      if (input) input.classList.remove('is-error')
    }, shakeMs + hold)
  } else {
    if (wrap._revertTimer) clearTimeout(wrap._revertTimer)
    wrap._revertTimer = null
    wrap.classList.remove('is-error')
    if (input) input.classList.remove('is-error')
  }
}

export default shake
