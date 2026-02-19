import { nextTick, onBeforeUnmount, watch, type Ref } from 'vue'

type FocusTrapOptions = {
  enabled: Ref<boolean>
  panelRef: Ref<HTMLElement | null>
  restoreFocus?: boolean
}

const FOCUSABLE_SELECTOR =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])'

export const useFocusTrap = (options: FocusTrapOptions) => {
  let lastFocusedElement: HTMLElement | null = null

  const trapFocus = (event: KeyboardEvent) => {
    if (!options.enabled.value || event.key !== 'Tab' || !options.panelRef.value) {
      return
    }
    const nodes = Array.from(
      options.panelRef.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
    )
    if (!nodes.length) {
      event.preventDefault()
      options.panelRef.value.focus()
      return
    }
    const first = nodes[0]!
    const last = nodes[nodes.length - 1]!
    const active = document.activeElement as HTMLElement | null
    if (event.shiftKey && active === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && active === last) {
      event.preventDefault()
      first.focus()
    }
  }

  const focusFirst = async () => {
    await nextTick()
    const panel = options.panelRef.value
    if (!panel) {
      return
    }
    const first = panel.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
    ;(first || panel).focus()
  }

  watch(
    options.enabled,
    (enabled) => {
      if (enabled) {
        lastFocusedElement = document.activeElement as HTMLElement | null
        document.addEventListener('keydown', trapFocus)
        void focusFirst()
        return
      }
      document.removeEventListener('keydown', trapFocus)
      if (options.restoreFocus !== false) {
        lastFocusedElement?.focus()
      }
      lastFocusedElement = null
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', trapFocus)
  })
}

