import { useContext, useMemo } from 'react';
import { v4 as uuidv4 } from 'uuid';

import HuntInfoContext from 'components/context';
import { useLocalStorage } from 'utils/storage';

/**
 * Returns an object with getters/setters for a unique identifier (uuid)per browser.
 * This uuid is preserved in localStorage and can be used as a personal identifier.
 * Use if you need the same behavior across the same browser (inc. different tabs)
 */
export const useBrowserUuid = (): string =>
  typeof window === 'undefined'
    ? ''
    : useLocalStorage('uuid', uuidv4, true).get();

/**
 * Returns an object with getters/setters for a unique identifier (uuid) per session.
 * This uuid is always prefixed by the browser uuid.
 * Use if you need different behavior across different tabs.
 */
export const useSessionUuid = (): string => {
  if (typeof window === 'undefined') {
    return '';
  }

  const uuid = useBrowserUuid();
  const session = useLocalStorage('session', 0, false);

  // Look up the sesion in context (set in _app.tsx)
  const { uuid: sessionUuid } = useContext(HuntInfoContext);

  return useMemo(() => {
    // If already found in HuntInfoContext, reuse it.
    if (sessionUuid) {
      return sessionUuid;
    }

    // Otherwise, increment the current session and save it
    // Assume that if we ever hit 1m the first session can be reused
    const newSession = (session.get() + 1) % 1000000;
    session.set(newSession);
    return `${uuid}_${newSession}`;
  }, []);
};
