import { v4 as uuidv4 } from 'uuid';
import { useLocalStorage } from 'utils/storage';

/**
 * Returns an object with getters/setters for a unique identifier (uuid).
 * This uuid is preserved in localStorage and can be used as a personal identifier.
 */
export const useBrowserUuid = () =>
  typeof window === 'undefined'
    ? undefined
    : useLocalStorage('uuid', uuidv4, true).get();
