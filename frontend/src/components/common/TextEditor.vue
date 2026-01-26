<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as monaco from 'monaco-editor'
import 'monaco-editor/min/vs/editor/editor.main.css'
import { loadMonacoLocale } from '@/i18n/monaco'

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
const { locale } = useI18n({ useScope: 'global' })

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

const disposeEditor = () => {
  editor?.dispose()
  editor = null
}

const createEditor = async (value: string) => {
  if (!rootRef.value) {
    return
  }
  await loadMonacoLocale(locale.value)
  editor = monaco.editor.create(rootRef.value, {
    value,
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
  lastValue = value
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
}

onMounted(() => {
  void createEditor(props.modelValue || '')
})

onBeforeUnmount(() => {
  disposeEditor()
})

watch(
  () => props.modelValue,
  (value) => {
    lastValue = value
    syncValue(value)
  },
)

watch(
  locale,
  async () => {
    if (!rootRef.value) {
      return
    }
    const currentValue = editor?.getValue() ?? props.modelValue ?? ''
    disposeEditor()
    await createEditor(currentValue)
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
