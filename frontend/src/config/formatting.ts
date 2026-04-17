/**
 * Shared number and currency formatting utilities.
 * Eliminates duplicate Cr/L/K formatting logic across 4+ components.
 */

const CRORE = 10000000;
const LAKH = 100000;
const THOUSAND = 1000;

/**
 * Format a number using Indian notation (Cr, L, K).
 * Used consistently across ChatScreen, DataChart, MessageBubble, DataSourcesPanel.
 */
export function formatIndianNumber(value: number, decimals: number = 1): string {
  if (Math.abs(value) >= CRORE) {
    return `${(value / CRORE).toFixed(decimals)} Cr`;
  }
  if (Math.abs(value) >= LAKH) {
    return `${(value / LAKH).toFixed(decimals)} L`;
  }
  if (Math.abs(value) >= THOUSAND) {
    return `${(value / THOUSAND).toFixed(decimals)} K`;
  }
  return value.toLocaleString('en-IN');
}

/**
 * Format a number with optional currency symbol.
 * @param value - The numeric value
 * @param currency - Currency symbol (e.g., '₹'). Pass empty string for no currency.
 * @param decimals - Number of decimal places
 */
export function formatCurrency(value: number, currency: string = '₹', decimals: number = 1): string {
  const formatted = formatIndianNumber(value, decimals);
  return currency ? `${currency}${formatted}` : formatted;
}

/**
 * Format a large record count (e.g., "12.5K records").
 */
export function formatRecordCount(count: number): string {
  if (count >= THOUSAND) {
    return `${(count / THOUSAND).toFixed(1)}K`;
  }
  return count.toLocaleString();
}

/**
 * Format file size in human-readable format.
 */
export function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${bytes} B`;
}
