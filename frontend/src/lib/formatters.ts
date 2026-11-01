/**
 * Utility functions for text formatting, title cleaning, and dates.
 */

// Purpose: cleanDocumentTitle.
// Inputs: filename: string.
// Output: Value specified by the signature or operation effect.
export function cleanDocumentTitle(filename: string): string {
  // Keeps the chat name exactly equal to the file name without changing letter case.
  return filename;
}
// Purpose: formatProcessedDate.

// Inputs: dateStr?: string.
// Output: Value specified by the signature or operation effect.
/**
 * formatProcessedDate function..
 *
 * @param dateStr? - string.
 * @returns string..
 */
export function formatProcessedDate(dateStr?: string): string {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}
