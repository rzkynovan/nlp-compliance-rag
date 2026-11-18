import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** false saat SSR dan hidrasi, true setelahnya — untuk nilai yang hanya ada di browser. */
export function useMounted(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
