/**
 * Callbacks that stay the same functions, and still call the latest ones.
 *
 * The plan's scene is memoised so that a pan redraws the backdrop and nothing
 * else (the owner's check, 2026-09-21, #11). A handler passed down as a new
 * function on every render would defeat that without anybody noticing. Each
 * handler here is wrapped once, per name, and reads the newest version through
 * a ref. An absent handler stays absent, because the scene attaches nothing
 * for one, and "no handler" is a promise that must survive the wrapping.
 */
import { useMemo, useRef } from 'react';

type Handler = (...args: never[]) => unknown;

export function useStableHandlers<T extends { [name: string]: Handler | undefined }>(
  handlers: T,
): T {
  const latest = useRef(handlers);
  latest.current = handlers;
  const wrapped = useRef(new Map<string, Handler>());
  const present = Object.keys(handlers)
    .filter((name) => handlers[name] !== undefined)
    .sort()
    .join(',');
  return useMemo(() => {
    const out: { [name: string]: Handler | undefined } = {};
    for (const name of Object.keys(latest.current)) {
      if (latest.current[name] === undefined) {
        out[name] = undefined;
        continue;
      }
      let handler = wrapped.current.get(name);
      if (handler === undefined) {
        handler = (...args: never[]) => latest.current[name]?.(...args);
        wrapped.current.set(name, handler);
      }
      out[name] = handler;
    }
    return out as T;
    // Only which handlers exist decides the object; their versions come
    // through the ref.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [present]);
}
