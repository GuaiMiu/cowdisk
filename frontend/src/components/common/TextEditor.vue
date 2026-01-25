<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import 'monaco-editor/min/vs/editor/editor.main.css'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: string
    readOnly?: boolean
    theme?: 'vs' | 'vs-dark'
    wordWrap?: boolean
    minimap?: boolean
    lineNumbers?: boolean
    indentGuides?: boolean
    fontSize?: number
  }>(),
  {
    language: 'plaintext',
    readOnly: false,
    theme: 'vs',
    wordWrap: true,
    minimap: false,
    lineNumbers: true,
    indentGuides: true,
    fontSize: 13,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()

const rootRef = ref<HTMLDivElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let lastValue = ''

const syncValue = (value: string) => {
  if (!editor) {
    return
  }
  const current = editor.getValue()
  if (current === value) {
    return
  }
  editor.setValue(value)
}

onMounted(() => {
  if (!rootRef.value) {
    return
  }
  editor = monaco.editor.create(rootRef.value, {
    value: props.modelValue || '',
    language: props.language,
    readOnly: props.readOnly,
    theme: props.theme,
    minimap: { enabled: props.minimap },
    wordWrap: props.wordWrap ? 'on' : 'off',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    fontSize: props.fontSize,
    lineNumbers: props.lineNumbers ? 'on' : 'off',
    guides: { indentation: props.indentGuides },
  })
  lastValue = props.modelValue || ''
  editor.onDidChangeModelContent(() => {
    if (!editor) {
      return
    }
    const value = editor.getValue()
    if (value === lastValue) {
      return
    }
    lastValue = value
    emit('update:modelValue', value)
  })
})

onBeforeUnmount(() => {
  editor?.dispose()
  editor = null
})

watch(
  () => props.modelValue,
  (value) => {
    lastValue = value
    syncValue(value)
  },
)

watch(
  () => props.language,
  (lang) => {
    if (!editor || !lang) {
      return
    }
    const model = editor.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model, lang)
    }
  },
)

watch(
  () => props.readOnly,
  (value) => {
    editor?.updateOptions({ readOnly: value })
  },
)

watch(
  () => props.theme,
  (value) => {
    if (value) {
      monaco.editor.setTheme(value)
    }
  },
)

watch(
  () => [props.wordWrap, props.minimap, props.lineNumbers, props.indentGuides, props.fontSize],
  ([wordWrap, minimap, lineNumbers, indentGuides, fontSize]) => {
    const size = typeof fontSize === 'number' ? fontSize : 13
    editor?.updateOptions({
      wordWrap: wordWrap ? 'on' : 'off',
      minimap: { enabled: !!minimap },
      lineNumbers: lineNumbers ? 'on' : 'off',
      guides: { indentation: !!indentGuides },
      fontSize: size,
    })
  },
)
</script>

<template>
  <div class="text-editor" ref="rootRef"></div>
</template>

<style scoped>
.text-editor {
  width: 100%;
  height: 100%;
  border-radius: 0;
  border: none;
  overflow: hidden;
  background: var(--color-surface);
}
</style>
