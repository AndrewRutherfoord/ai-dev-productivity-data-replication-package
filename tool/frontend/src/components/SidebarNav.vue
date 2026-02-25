<template>
  <v-navigation-drawer expand-on-hover rail>
    <!-- <v-list>
            <v-list-item prepend-avatar="https://randomuser.me/api/portraits/women/85.jpg"
                subtitle="sandra_a88@gmailcom" title="Sandra Adams"></v-list-item>
        </v-list> -->

    <v-list density="compact" nav>
      <template v-for="section in routes">
        <v-list-item
          v-for="route in section"
          :key="route.routeName"
          :prepend-icon="route.icon"
          :title="route.label"
          :to="{ name: route.routeName }"
        ></v-list-item>
        <v-divider></v-divider>
      </template>
    </v-list>
    <template v-slot:append>
      <v-list density="compact" nav>
        <!-- <v-list-item title="Notifications" prepend-icon="mdi-message" :to="{ name: 'notifications' }">
                    <template v-slot:prepend>
                        <v-badge color="error" content="6"><v-icon>mdi-message</v-icon></v-badge>
                    </template>
</v-list-item> -->
        <v-list-item
          title="Neo4j Settings"
          prepend-icon="mdi-database-cog"
          @click="emit('open-neo4j-settings')"
        ></v-list-item>
        <v-list-item
          title="Toggle Theme"
          prepend-icon="mdi-theme-light-dark"
          @click="toggleTheme"
        ></v-list-item>
      </v-list>
    </template>
  </v-navigation-drawer>
</template>

<script lang="ts" setup>
import { useTheme } from 'vuetify'

const emit = defineEmits<{
  'open-neo4j-settings': []
}>()

const routes = [
  [
    {
      label: 'Home',
      icon: 'mdi-home',
      routeName: 'home'
    }
  ],
  [
    {
      label: 'Conf. Editor',
      icon: 'mdi-code-braces',
      routeName: 'editor'
    },
    {
      label: 'Jobs',
      icon: 'mdi-clipboard-list-outline',
      routeName: 'jobs-list'
    }
  ],
  [
    {
      label: 'Manage DB',
      icon: 'mdi-database',
      routeName: 'manage-database'
    },
    {
      label: 'Query Neo4j',
      icon: 'mdi-database-search',
      routeName: 'query'
    }
  ]
]

const theme = useTheme()

function toggleTheme() {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}

function showNotifications() {
  console.log('show notifications')
}
</script>

