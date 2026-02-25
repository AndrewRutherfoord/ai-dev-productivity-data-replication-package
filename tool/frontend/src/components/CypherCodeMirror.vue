<template>
    <div ref="editorDiv"></div>
</template>

<script setup lang="ts">
import { createCypherEditor } from '@neo4j-cypher/codemirror';
import { editor } from 'monaco-editor';
import { ref, onMounted, defineModel, watch } from 'vue'

const editorDiv = ref();
const editorInstance = ref();

const model = defineModel();

onMounted(() => {
    const { editor } = createCypherEditor(editorDiv.value, {})
    editorInstance.value = editor
    editor.onValueChanged((value: string) => {
        model.value = value
    })
})

function setValue(value: string) {
    editorInstance.value.setValue(value)
    model.value = value
}

function getQuery() {
    return model.value
}

defineExpose({
    setValue,
    getQuery
});

</script>

<style scoped></style>