<template>
    <v-card>
        <v-card-title>Database Node Types</v-card-title>
        <v-table>
            <thead>
                <tr>
                    <th class="text-left">
                        Node Label
                    </th>
                    <th class="text-left">
                        Count
                    </th>
                </tr>
            </thead>
            <tbody v-if="result != null && result.length > 0">
                <tr v-for="item in result" :key="item.label">
                    <td>{{ item.label }}</td>
                    <td>{{ item.count }}</td>
                </tr>
            </tbody>
            <tbody v-else>
                <tr>
                    <td colspan="2">No nodes in database...</td>
                </tr>
            </tbody>
        </v-table>
    </v-card>
</template>

<script setup lang="ts">
import { useNeo4j } from '@/composables/useNeo4j';
import { onMounted } from 'vue';

const { runQuery, error, loading, result, headers } = useNeo4j();

onMounted(() => {
    getData();
});

async function getData() {
    await runQuery('MATCH (n) RETURN distinct labels(n) as label, count(*) as count')
}

defineExpose({
    getData
})
</script>