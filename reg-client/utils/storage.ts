import { useRef } from 'react';

/**
 * Returns an object with getters/setters for localStorage.
 */
export const useLocalStorage = <T>(
  key: string,
  defaultValue?: T | (() => T),
  saveDefault?: boolean
): { get: () => T; set: (value: T) => void } => {
  const valueRef = useRef<T | undefined>();

  key = process.env.storagePrefix + key;

  return {
    get() {
      const getDefaultValue = () => {
        let value = defaultValue;
        if (typeof defaultValue === 'function') {
          value = (defaultValue as () => T)();
        }
        if (saveDefault) {
          if (typeof window !== 'undefined') {
            window.localStorage.setItem(key, JSON.stringify(value));
          }
        }
        return value as T;
      };
      if (!valueRef.current) {
        if (typeof window !== 'undefined') {
          const storedValue = window.localStorage.getItem(key);
          valueRef.current =
            storedValue !== null ? JSON.parse(storedValue) : getDefaultValue();
        } else {
          valueRef.current = getDefaultValue();
        }
      }
      return valueRef.current!;
    },
    set(value: T) {
      if (valueRef.current === value) {
        return;
      }
      valueRef.current = value;
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(value));
      }
    },
  };
};
