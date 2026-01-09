/**
 * Google Apps Script for Real-time Sheet Updates
 * ===============================================
 * 
 * This script sends a webhook notification to your Kiwi backend
 * whenever the Google Sheet is edited.
 * 
 * SETUP INSTRUCTIONS:
 * 1. Open your Google Sheet
 * 2. Go to Extensions > Apps Script
 * 3. Delete any existing code and paste this entire file
 * 4. Update BACKEND_URL below with your backend URL
 * 5. Click "Save" (Ctrl+S)
 * 6. Click "Run" > "setupTrigger" (first time only)
 * 7. Authorize the script when prompted
 * 
 * For local development:
 *   - Use ngrok: ngrok http 8000
 *   - Set BACKEND_URL to your ngrok URL (e.g., "https://abc123.ngrok.io")
 * 
 * For production:
 *   - Set BACKEND_URL to your deployed backend URL
 */

// ⚠️ UPDATE THIS URL to your backend
const BACKEND_URL = "http://localhost:8000";  // Change this!

/**
 * Triggered when the sheet content changes.
 * Sends a POST request to the backend webhook endpoint.
 */
function onChange(e) {
  try {
    const spreadsheet = SpreadsheetApp.getActive();
    const sheet = spreadsheet.getActiveSheet();

    const payload = {
      spreadsheetId: spreadsheet.getId(),
      sheetName: sheet.getName(),
      updatedAt: new Date().toISOString()
    };

    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true  // Don't throw on HTTP errors
    };

    const response = UrlFetchApp.fetch(BACKEND_URL + "/api/sheet-update", options);

    // Log for debugging (View > Execution log in Apps Script editor)
    console.log("Webhook response:", response.getResponseCode(), response.getContentText());

  } catch (error) {
    console.error("Webhook error:", error);
    // Don't throw - we don't want to block spreadsheet edits
  }
}

/**
 * Sets up the onChange trigger.
 * Run this function ONCE manually to install the trigger.
 */
function setupTrigger() {
  // Remove any existing triggers first
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));

  // Create new onChange trigger
  ScriptApp.newTrigger("onChange")
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onChange()
    .create();

  console.log("✅ Trigger installed! Sheet changes will now notify the backend.");
}

/**
 * Test function to verify the webhook is working.
 * Run this manually to test connectivity.
 */
function testWebhook() {
  onChange({ source: SpreadsheetApp.getActive() });
  console.log("Test webhook sent! Check your backend logs.");
}
