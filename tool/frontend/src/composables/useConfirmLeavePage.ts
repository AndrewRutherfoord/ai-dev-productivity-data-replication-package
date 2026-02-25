import { computed, onBeforeUnmount, onMounted, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

/**
 * Composable that shows a confirm leave or confirm reload dialog there are unsaved changes on a page.
 *
 * @param confirmLeaveMessage Message to show in the dialog.
 * @param leavable Boolean that indicates whether the page can be left without showing the dialog.
 */
export default function useConfirmLeavePage(confirmLeaveMessage: string, leavable: Ref<boolean>, invert = false) {
  
  const canLeave = computed(() => {
    if (invert) {
      return !leavable.value
    }
    return leavable.value
  })

  /**
   * Before reloading the page, checks if there are unsaved changes and shows a confirm leave dialog.
   */
  function beforeReload(event: { returnValue: string }) {
    // To show confirm leave dialog.
    if (!canLeave.value) {
      event.returnValue = confirmLeaveMessage // Needed for some browsers
      return confirmLeaveMessage
    }
    return null
  }

  onMounted(() => {
    // Add confirm leave event listener.
    window.addEventListener('beforeunload', beforeReload)
  })

  onBeforeUnmount(() => {
    // Remove confirm leave event listener.
    window.removeEventListener('beforeunload', beforeReload)
  })

  /**
   * Before a route change, checks if there are unsaved changes and shows a confirm leave dialog.
   */
  onBeforeRouteLeave(() => {
    if (!canLeave.value && !confirm(confirmLeaveMessage)) {
      return false
    }
    return true
  })
}
