/**
 * Utility functions for text formatting, title cleaning, and dates.
 */

export function cleanDocumentTitle(filename: string): string {
  // Deja el nombre del chat exactamente igual al nombre del archivo, sin modificar mayúsculas ni minúsculas
  return filename;
}

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
