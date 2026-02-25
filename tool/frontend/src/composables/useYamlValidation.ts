import { computed, ref, type Ref } from 'vue'
import yaml from 'js-yaml'
import Ajv from 'ajv'
import addFormats from 'ajv-formats'

/**
 * YAML validation composable. Checks if the current configuration is valid against a schema given.
 *
 * @param schema Schema to validate against.
 * @param content Content to validate.
 */
export function useYamlValidation(schema: string, content: Ref<string>) {
  // If configuration was valid on most recent execution of `validate()`.
  const valid = ref<boolean>(true)

  // String error message to display if the configuration is invalid.
  const error = ref<string | null>(null)

  /**
   * Performs validation of the current configuration against the given schema.
   * @returns If the configuration is valid.
   */
  function validate() {
    let configuration
    try {
      configuration = yaml.load(content.value)
    } catch (e) {
      console.error(e)
      error.value = 'Could not parse configuration.'
      valid.value = false
      return false
    }

    const ajv = new Ajv({ strictTypes: false })
    // Add formats extension to be able to check date formats
    addFormats(ajv)

    try {
      // Check if input matches schema
      const isValid = ajv.validate(JSON.parse(schema), configuration)

      if (isValid) {
        valid.value = true
        return true
      } else {
        const errorItem = ajv.errors?.pop()

        if (errorItem?.params?.format === 'date') {
          // For date fields, inform the user of the format that is expected.
          error.value = 'Date format must match YYYY-MM-DD.'
        } else {
          error.value = errorItem?.message ? errorItem.message : ':/'
        }
        valid.value = false
        return false
      }
    } catch (e) {
      console.error(e)

      error.value = 'Could not parse configuration.'
      valid.value = false
      return false
    }
  }
  return {
    valid,
    error,
    validate
  }
}
