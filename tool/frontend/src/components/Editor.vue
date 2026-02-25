<template>
  <vue-monaco-editor class="h-100" v-model:value="code" :theme="getEditorTheme()" :language="language"
    :options="MONACO_EDITOR_OPTIONS" @mount="handleMount" />
</template>

<script lang="ts" setup>
import { useMagicKeys, whenever } from '@vueuse/core';
import type { languages } from 'monaco-editor';
import { ref, shallowRef, onMounted, onUnmounted } from 'vue'
import { useTheme } from 'vuetify'

const theme = useTheme()

const props = defineProps(
  {
    language: {
      type: String,
      default: "yaml"
    }
  }
)

const emits = defineEmits(["input", "save"])

const { ctrl_s } = useMagicKeys({
  passive: false,
  onEventFired(e) {
    if (e.ctrlKey && e.key === 's' && e.type === 'keydown')
      e.preventDefault()
  },
})

const keys = useMagicKeys()
const altShiftF = keys['Alt+Shift+F']

whenever(ctrl_s, () => emits('save'))
whenever(altShiftF, () => formatCode())

const MONACO_EDITOR_OPTIONS = {
  automaticLayout: true,
  formatOnType: true,
  formatOnPaste: true
}

const code = defineModel({ type: String, default: '// some code...' })

const editorRef = shallowRef()
const handleMount = (editor) => (editorRef.value = editor)

// your action
function formatCode() {
  console.log("Format")
  editorRef.value?.getAction('editor.action.formatDocument').run()
}

function getEditorTheme() {
  if (theme.global.current.value.dark) {
    return 'vs-dark'
  } else {
    return 'vs-light'
  }
}

</script>
