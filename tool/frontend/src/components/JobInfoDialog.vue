<template>
    <v-dialog v-model="model">
        <v-card prepend-icon="mdi-update" title="Update in progress">
            <v-card-text>
                <h6>Job Configuration:</h6>
                <code class="text-red">
                <pre>{{ prettyJSON(job.data) }}</pre>
            </code>
                <h4>Statuses</h4>
                <ol>
                    <li v-for="status in job.statuses" :key="status.timestamp" class="text-capitalize">
                        {{
                            status.status }}
                        ({{ status.timestamp }})</li>
                </ol>
            </v-card-text>
            <template v-slot:actions>
                <v-btn class="ms-auto" text="Ok" @click="model = false"></v-btn>
            </template>
        </v-card>
    </v-dialog>
</template>
<script setup lang="ts">
import { ref } from 'vue';
import yaml from 'js-yaml';

const model = defineModel()

const props = defineProps({
    job: {
        type: Object as PropType<Job>,
    }
})

function prettyJSON(value: string) {
    //   return JSON.stringify(value, null, 2);
    return yaml.dump(value);
}

</script>

<style scoped></style>