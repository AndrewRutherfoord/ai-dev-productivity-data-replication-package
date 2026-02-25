<template>
    <slot name="header">
        <v-list-item :title="title" :subtitle="subtitle">
            <template v-slot:append>
                <v-tooltip :text="createNewTooltip">
                    <template v-slot:activator="{ props }">
                        <v-btn :icon="createNewIcon" density="compact" variant="text" @click="createFile"
                            v-bind="props"></v-btn>
                    </template>
                </v-tooltip>
            </template>
        </v-list-item>
    </slot>
    <v-divider></v-divider>
    <v-list v-if="!isLoading">
        <FileTreeNode v-for="key in Object.keys(data)" :key="key" :name="key" :data="data[key]" :path="key"
            @link-clicked="onClick" @delete-file="onDeleteFile" :delete-tooltip="deleteTooltip"
            :delete-icon="deleteIcon" :open-tooltip="openTooltip" :open-icon="openIcon">
        </FileTreeNode>
    </v-list>
</template>

<script setup lang="ts">
import FileTreeNode from './FileTreeNode.vue'

defineProps(
    {
        title: String, subtitle: String, data: Object, isLoading: Boolean,
        deleteTooltip: { type: String, default: "Delete" },
        deleteIcon: { type: String, default: "mdi-delete" },
        openTooltip: { type: String, default: "Open" },
        openIcon: { type: String, default: "mdi-open-in-app" },
        createNewIcon: { type: String, default: "mdi-file-document-plus-outline" },
        createNewTooltip: { type: String, default: "Create New" },
    }
)

const emits = defineEmits(['linkClicked', 'deleteFile', 'createFile'])

function onClick(path: string) {
    emits('linkClicked', path)
}

function onDeleteFile(path: string) {
    emits('deleteFile', path)
}

function createFile() {
    emits('createFile')
}

</script>