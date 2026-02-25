<template>
    <v-list-item v-if="data === null">
        <pre class="text-red">{{ name }}</pre>
        <template v-slot:append>
            <slot name="file-row-append">

                <v-tooltip :text="openTooltip">
                    <template v-slot:activator="{ props }">
                        <v-btn :icon="openIcon" density="compact" variant="plain" @click="onClick(`${path}`)"
                            v-bind="props">
                        </v-btn>
                    </template>
                </v-tooltip>
                <v-tooltip :text="deleteTooltip">
                    <template v-slot:activator="{ props }">
                        <v-btn :icon="deleteIcon" density="compact" variant="plain" @click="onDeleteFile(`${path}`)"
                            v-bind="props">
                        </v-btn>
                    </template>
                </v-tooltip>
            </slot>
        </template>
    </v-list-item>
    <v-list-group v-else>
        <template v-slot:activator="{ props }">
            <v-list-item v-bind="props" :title="name"></v-list-item>
        </template>
        <FileTreeNode v-for="k in Object.keys(data)" :key="k" :name="k" :data="data[k]" @link-clicked="onClick"
            :path="`${path}/${k}`" @delete-file="onDeleteFile">
        </FileTreeNode>
    </v-list-group>
</template>

<script setup lang="ts">

defineProps({
    name: { type: String, required: true },
    data: { type: Object },
    path: { type: String, required: true },
    deleteTooltip: { type: String, default: "Delete" },
    deleteIcon: { type: String, default: "mdi-delete" },
    openTooltip: { type: String, default: "Open" },
    openIcon: { type: String, default: "mdi-open-in-app" },
});

const emits = defineEmits(['linkClicked', "deleteFile"])

const slots = defineSlots()

function onClick(path: string) {
    emits('linkClicked', path)
}

function onDeleteFile(path: string) {
    emits('deleteFile', path)
}

</script>