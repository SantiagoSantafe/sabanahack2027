/** Pressed-key set for manual driving; ignores keys typed into form fields. */
export const pressed = new Set<string>();

function isTyping(e: KeyboardEvent): boolean {
  const t = e.target as HTMLElement | null;
  return !!t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
}

const DRIVE_KEYS = ['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'];

let installed = false;
export function installKeyboard() {
  if (installed) return;
  installed = true;
  window.addEventListener('keydown', (e) => {
    if (isTyping(e)) return;
    const k = e.key.toLowerCase();
    pressed.add(k);
    if (DRIVE_KEYS.includes(k)) e.preventDefault();
  });
  window.addEventListener('keyup', (e) => pressed.delete(e.key.toLowerCase()));
  window.addEventListener('blur', () => pressed.clear());
  // Switching tabs or minimizing: keys released while hidden never fire keyup. Dead-man: clear them.
  document.addEventListener('visibilitychange', () => pressed.clear());
}

export function axis(): { fwd: number; turn: number; fast: boolean } {
  const f = (pressed.has('w') || pressed.has('arrowup') ? 1 : 0) - (pressed.has('s') || pressed.has('arrowdown') ? 1 : 0);
  const t = (pressed.has('a') || pressed.has('arrowleft') ? 1 : 0) - (pressed.has('d') || pressed.has('arrowright') ? 1 : 0);
  return { fwd: f, turn: t, fast: pressed.has('shift') };
}
