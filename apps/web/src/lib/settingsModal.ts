/**
 * Settings Modal Utility
 *
 * Allows any component to open the settings modal by dispatching a custom event.
 * The SpotlightSearch component listens for this event and opens the modal.
 */

/**
 * Open the settings modal from anywhere in the app.
 * This dispatches a custom event that SpotlightSearch listens for.
 */
export function openSettingsModal(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('openSettingsModal'));
  }
}
