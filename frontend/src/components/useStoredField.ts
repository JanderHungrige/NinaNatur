import { useCallback, useState } from 'react';

/**
 * A form field over a stored value (doc 93): what it shows, a setter, and
 * whether the gardener changed it.
 *
 * The store can change while the form is open — the laser fills a crown base
 * when the light is computed, a survey a height, a roof, the eaves. A field
 * that kept the value it opened with then differed from the store without
 * anybody touching it, and the save sent the old value back as the
 * gardener's word: a measurement turned into an entry, the thing Wave 21
 * forbade (review of stage 3, 2026-09-28). So an untouched field follows the
 * store, and a touched one keeps what was typed. It follows in the render
 * that sees the new value, not by remounting the form, which would take the
 * focus out of whatever field it was in.
 */
export function useStoredField(stored: string): [string, (value: string) => void, boolean] {
  const [field, setField] = useState({ value: stored, base: stored });
  let current = field;
  if (stored !== field.base) {
    current = { value: field.value === field.base ? stored : field.value, base: stored };
    setField(current);
  }
  const setValue = useCallback((value: string) => setField((f) => ({ ...f, value })), []);
  return [current.value, setValue, current.value !== current.base];
}
