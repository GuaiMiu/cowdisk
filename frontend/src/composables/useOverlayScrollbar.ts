import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export const useOverlayScrollbar = () => {
  const scrollRef = ref<HTMLElement | null>(null)
  const scrollTop = ref(0)
  const clientHeight = ref(0)
  const scrollHeight = ref(0)
  const isHover = ref(false)
  const isScrolling = ref(false)
  const isDragging = ref(false)
  const dragOffset = ref(0)
  let scrollTimer: number | null = null
  let observer: ResizeObserver | null = null

  const updateMetrics = () => {
    if (!scrollRef.value) {
      scrollTop.value = 0
      clientHeight.value = 0
      scrollHeight.value = 0
      return
    }
    scrollTop.value = scrollRef.value.scrollTop
    clientHeight.value = scrollRef.value.clientHeight
    scrollHeight.value = scrollRef.value.scrollHeight
  }

  const onScroll = () => {
    updateMetrics()
    isScrolling.value = true
    if (scrollTimer) {
      window.clearTimeout(scrollTimer)
    }
    scrollTimer = window.setTimeout(() => {
      isScrolling.value = false
    }, 700)
  }

  const onMouseEnter = () => {
    isHover.value = true
  }

  const onMouseLeave = () => {
    isHover.value = false
  }

  const isScrollable = computed(() => scrollHeight.value > clientHeight.value + 1)

  const thumbHeight = computed(() => {
    if (!isScrollable.value) {
      return 0
    }
    const ratio = clientHeight.value / scrollHeight.value
    return Math.max(Math.floor(clientHeight.value * ratio), 24)
  })

  const thumbTop = computed(() => {
    if (!isScrollable.value) {
      return 0
    }
    const maxScroll = scrollHeight.value - clientHeight.value
    const maxTop = clientHeight.value - thumbHeight.value
    if (maxScroll <= 0) {
      return 0
    }
    return Math.round((scrollTop.value / maxScroll) * maxTop)
  })

  const visible = computed(() => isScrollable.value && (isHover.value || isScrolling.value))

  const onThumbMouseDown = (event: MouseEvent) => {
    if (!scrollRef.value || !isScrollable.value) {
      return
    }
    isDragging.value = true
    const rect = scrollRef.value.getBoundingClientRect()
    const thumbOffset = event.clientY - rect.top - thumbTop.value
    dragOffset.value = Math.max(0, Math.min(thumbOffset, thumbHeight.value))
    event.preventDefault()
  }

  const onDragMove = (event: MouseEvent) => {
    if (!scrollRef.value || !isDragging.value) {
      return
    }
    const rect = scrollRef.value.getBoundingClientRect()
    const maxTop = clientHeight.value - thumbHeight.value
    const nextTop = Math.max(0, Math.min(event.clientY - rect.top - dragOffset.value, maxTop))
    const maxScroll = scrollHeight.value - clientHeight.value
    const nextScrollTop = maxTop > 0 ? (nextTop / maxTop) * maxScroll : 0
    scrollRef.value.scrollTop = nextScrollTop
    updateMetrics()
  }

  const onDragEnd = () => {
    if (!isDragging.value) {
      return
    }
    isDragging.value = false
  }

  onMounted(() => {
    updateMetrics()
    observer = new ResizeObserver(updateMetrics)
    if (scrollRef.value) {
      observer.observe(scrollRef.value)
    }
    window.addEventListener('resize', updateMetrics)
    window.addEventListener('mousemove', onDragMove)
    window.addEventListener('mouseup', onDragEnd)
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
    window.removeEventListener('resize', updateMetrics)
    window.removeEventListener('mousemove', onDragMove)
    window.removeEventListener('mouseup', onDragEnd)
    if (scrollTimer) {
      window.clearTimeout(scrollTimer)
    }
  })

  return {
    scrollRef,
    onScroll,
    onMouseEnter,
    onMouseLeave,
    thumbHeight,
    thumbTop,
    visible,
    isScrollable,
    updateMetrics,
    onThumbMouseDown,
  }
}
