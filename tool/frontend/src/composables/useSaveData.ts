import { ref, type Ref } from 'vue'

/**
 * Saves data to a file using a link element.
 * 
 * @param data String data to be saved to a file. Passed as a Ref to allow for reactivity. Only saved when saveToFile() is called.
 * @param initialFilename Initial value for the filename ref. Defaults to 'data.json'. Can be changed by calling filename.value = '<filename>.json'
 */
export function useSaveData(data: Ref<string>, initialFilename: string = 'data.json') {
  const filename = ref<string>(initialFilename)

  /**
   * Saves the data to a file. 
   * Source: https://www.tutorialspoint.com/how-to-create-and-save-text-file-in-javascript
   */
  const saveToFile = () => {

    // Create a blob from the data
    const blob = new Blob([data.value], { type: 'application/json' })

    // Create a link element
    const link = document.createElement('a')

    // Set the download attribute with a filename
    link.download = filename.value

    // Create an object URL and set it as the href attribute
    link.href = window.URL.createObjectURL(blob)

    // Append the link to the body
    document.body.appendChild(link)

    // Programmatically click the link to trigger the download
    link.click()

    // Remove the link from the document
    document.body.removeChild(link)
  }

  return { saveToFile, filename }
}
