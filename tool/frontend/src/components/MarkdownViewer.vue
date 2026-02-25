<template>
    <v-container>
        <div class="markdown" v-html="renderedMarkdown"></div>
    </v-container>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import markdownit from 'markdown-it'
import readme from '../../../README.md?raw'
import markdownItHighlightjs from 'markdown-it-highlightjs';
import 'highlight.js/styles/default.css'; // Import a highlight.js theme (you can choose another theme if you like)

const renderedMarkdown = ref<string>('');

onMounted(async () => {
    const md = markdownit({
        html: true,
        linkify: true,
        typographer: true,
        breaks: true
    }).use(markdownItHighlightjs)
    const rendered = await md.render(readme);
    renderedMarkdown.value = rendered;
})

</script>

<style>
/* All styles are prefaced with "div.markdown" to avoid changing the styles on the rest of the application.
 * Couldn't use a scoped style because it doesn't work with v-html.
*/

div.markdown ul {
    list-style-type: disc;
    padding-left: 1.5em;
}

div.markdown ul ul {
    list-style-type: circle;
}

div.markdown ul ul ul {
    list-style-type: square;
}

div.markdown code {
    background-color: #f3f3f3 !important;
    padding: 0.1em 0.3em !important;
    color: #333;
    /* color: red !important; */
}

div.markdown h1,
div.markdown h2,
div.markdown h3,
div.markdown h4,
div.markdown h5,
div.markdown h6,
div.markdown p,
div.markdown code,
div.markdown pre {
    margin-top: 1em;
    margin-bottom: 0.5em;
}
</style>