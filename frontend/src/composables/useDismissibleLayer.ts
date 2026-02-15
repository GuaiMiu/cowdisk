import { onBeforeUnmount, onMounted, watch, type Ref } from 'vue'

type DismissibleLayerOptions = {
  enabled: Ref<boolean>
  rootRef: Ref<HTMLElement | null>
  onEscape?: () => void
  onPointerDownOutside?: () => void
}

const activeLayerStack: symbol[] = []

const isEventInside = (event: Event, root: HTMLElement) => {
  const path = typeof event.composedPath === 'function' ? event.composedPath() : []
  if (path.length > 0) {
    return path.includes(root)
  }
  const target = event.target as Node | null
  return !!(target && root.contains(target))
}

export const useDismissibleLayer = (options: DismissibleLayerOptions) => {
  const layerId = Symbol('dismissible-layer')

  const removeLayer = () => {
    const index = activeLayerStack.lastIndexOf(layerId)
    if (index >= 0) {
      activeLayerStack.splice(index, 1)
    }
  }

  const activateLayer = () => {
    removeLayer()
    activeLayerStack.push(layerId)
  }

  const isTopLayer = () => activeLayerStack[activeLayerStack.length - 1] === layerId

  const onDocumentPointerDown = (event: PointerEvent) => {
    if (!options.enabled.value || !options.rootRef.value) {
      return
    }
    if (!isTopLayer()) {
      return
    }
    if (!isEventInside(event, options.rootRef.value)) {
      options.onPointerDownOutside?.()
    }
  }

  const onDocumentKeyDown = (event: KeyboardEvent) => {
    if (!options.enabled.value) {
      return
    }
    if (!isTopLayer()) {
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      options.onEscape?.()
    }
  }

  onMounted(() => {
    document.addEventListener('pointerdown', onDocumentPointerDown)
    document.addEventListener('keydown', onDocumentKeyDown)
  })

  watch(
    options.enabled,
    (enabled) => {
      if (enabled) {
        activateLayer()
      } else {
        removeLayer()
      }
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    removeLayer()
    document.removeEventListener('pointerdown', onDocumentPointerDown)
    document.removeEventListener('keydown', onDocumentKeyDown)
  })
}
