<script setup lang="ts" generic="TRow extends Record<string, unknown>">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useSlots, watch } from 'vue'
import Empty from './Empty.vue'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'

type Column = {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
}

const props = withDefaults(
  defineProps<{
    columns: Column[]
    rows: TRow[]
    rowKey?: keyof TRow | string
    minRows?: number
    scrollable?: boolean
    fill?: boolean
    rowHeight?: number
  }>(),
  {
    rows: () => [],
    rowKey: 'id',
    minRows: 0,
    scrollable: false,
    fill: false,
    rowHeight: 48,
  },
)

const bodyRef = ref<HTMLDivElement | null>(null)
const rowCapacity = ref(0)
const {
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
} = useOverlayScrollbar()

const updateCapacity = () => {
  if (!props.scrollable || !props.fill) {
    rowCapacity.value = 0
    return
  }
  if (!scrollRef.value) {
    rowCapacity.value = 0
    return
  }
  rowCapacity.value = Math.floor(scrollRef.value.clientHeight / props.rowHeight)
  updateMetrics()
}

const contentRows = computed(() => props.rows.length)

const placeholderCount = computed(() => {
  if (!props.scrollable || !props.fill) {
    return Math.max(props.minRows - props.rows.length, 0)
  }
  return Math.max(rowCapacity.value - contentRows.value, 0)
})

const gridTemplate = computed(() =>
  props.columns.map((col) => col.width || 'minmax(120px, 1fr)').join(' '),
)

const tableStyle = computed(() => ({
  ...(props.scrollable ? { '--table-row-height': `${props.rowHeight}px` } : undefined),
  '--table-columns': gridTemplate.value,
}))

defineSlots<{
  [K in `cell-${string}`]?: (props: { row: TRow }) => unknown
} & {
  [K in `head-${string}`]?: (props: { column: Column }) => unknown
}>()

const slots = useSlots()
const hasHeadSlot = (key: string) => Boolean(slots[`head-${key}` as `head-${string}`])
const headSlotName = (key: string) => `head-${key}` as `head-${string}`

let observer: ResizeObserver | null = null

onMounted(() => {
  updateCapacity()
  if (props.scrollable && props.fill) {
    observer = new ResizeObserver(updateCapacity)
    if (bodyRef.value) {
      observer.observe(bodyRef.value)
    }
  }
})

watch(
  () => props.rows.length,
  () => {
    void nextTick(() => {
      updateCapacity()
      updateMetrics()
    })
  },
)

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div class="table" :class="scrollable ? 'table--scroll' : ''" :style="tableStyle">
    <div class="table__header">
      <div
        v-for="col in columns"
        :key="col.key"
        class="table__cell table__cell--head"
        :style="{ textAlign: col.align || 'left' }"
      >
        <slot v-if="hasHeadSlot(col.key)" :name="headSlotName(col.key)" :column="col">
          {{ col.label }}
        </slot>
        <template v-else>{{ col.label }}</template>
      </div>
    </div>
    <div
      v-if="rows.length || minRows > 0"
      ref="bodyRef"
      class="table__body"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
    >
      <div ref="scrollRef" class="table__scroll overlay-scroll" @scroll="onScroll">
        <div v-for="row in rows" :key="String(row[rowKey])" class="table__row">
          <div
            v-for="col in columns"
            :key="col.key"
            class="table__cell"
            :style="{ textAlign: col.align || 'left' }"
          >
            <slot :name="`cell-${col.key}`" :row="row">
              {{ row[col.key] }}
            </slot>
          </div>
        </div>
        <div v-if="placeholderCount > 0">
          <div
            v-for="index in placeholderCount"
            :key="`placeholder-${index}`"
            class="table__row table__row--placeholder"
          >
            <div
              v-for="col in columns"
              :key="col.key"
              class="table__cell"
              :style="{ textAlign: col.align || 'left' }"
            >
              &nbsp;
            </div>
          </div>
        </div>
      </div>
      <div v-if="isScrollable" class="overlay-scrollbar" :class="{ 'is-visible': visible }">
        <div
          class="overlay-scrollbar__thumb"
          :style="{ height: `${thumbHeight}px`, transform: `translateY(${thumbTop}px)` }"
          @mousedown="onThumbMouseDown"
        ></div>
      </div>
    </div>
    <Empty v-else title="暂无数据" description="目前没有可展示的记录" />
  </div>
</template>

<style scoped>
.table {
  display: grid;
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface);
}

.table--scroll {
  height: 100%;
  overflow: hidden;
  grid-template-rows: auto 1fr;
  gap: 0;
}

.table__header {
  display: grid;
  grid-template-columns: var(--table-columns, repeat(auto-fit, minmax(120px, 1fr)));
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface-2);
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

.table__body {
  position: relative;
  min-height: 0;
  height: 100%;
}

.table__scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: 0;
  grid-auto-rows: var(--table-row-height, 48px);
  align-content: start;
}

.table__row {
  display: grid;
  grid-template-columns: var(--table-columns, repeat(auto-fit, minmax(120px, 1fr)));
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  min-height: 48px;
}

.table--scroll .table__row {
  height: var(--table-row-height, 48px);
  min-height: 0;
}

.table__cell {
  font-size: 14px;
}

.table__cell--head {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
}

.table__row--placeholder {
  opacity: 0;
  pointer-events: none;
}
</style>
