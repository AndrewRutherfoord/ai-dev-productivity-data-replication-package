<template>
    <v-dialog v-model="visibility" width="700px">
        <v-card title="Row Data">
            <v-card-text>
                <code class="text-red">
        <pre>{{ jsonifiedData }}</pre>
      </code>
            </v-card-text>
            <template v-slot:actions>
                <v-btn class="ms-1" variant="outlined" text="Close" @click="toggle"></v-btn>
                <v-btn v-if="isSupported" class="ms-auto" variant="outlined" @click="copy(jsonifiedData)">
                    <v-icon>mdi-content-copy</v-icon>
                    <v-tooltip text="Save to File" activator="parent" location="top" />
                </v-btn>

                <v-btn v-if="isSupported" variant="outlined" @click="saveToFile">
                    <v-icon>mdi-content-save</v-icon>
                    <v-tooltip text="Save to File" activator="parent" location="top" />
                </v-btn>
            </template>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import { useSaveData } from '@/composables/useSaveData';
import { useClipboard } from '@vueuse/core'
import { computed } from 'vue';

const visibility = defineModel('visibility')
const data = defineModel("data")

const jsonifiedData = computed(() => {
    return JSON.stringify(data.value, null, 2)
})

const { text, copy, copied, isSupported } = useClipboard()

const { saveToFile, filename } = useSaveData(jsonifiedData, "row-data.json")

function toggle() {
    visibility.value = !visibility.value;
}

</script>