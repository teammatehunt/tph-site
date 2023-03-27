import { useEffect, useRef } from 'react';

export enum KeyCode {
  TAB = 9,
  ALT = 18,
  ENTER = 13,
  ESC = 27,
  SPACE = 32,
  LEFT = 37,
  UP = 38,
  RIGHT = 39,
  DOWN = 40,
  W = 87,
  A = 65,
  S = 83,
  D = 68,
}

type EventName = 'keypress' | 'keydown' | 'keyup';

/** Sets up an event listener that listens for keypresses. */
export const useEventListener = (
  eventName: EventName,
  handler: (key: KeyCode) => void,
  element = window,
  deps: React.DependencyList = []
) => {
  // Create a ref that stores handler
  const savedHandler = useRef(handler);

  useEffect(() => void (savedHandler.current = handler), [handler]);

  useEffect(() => {
    const isSupported = element && element.addEventListener;
    if (!isSupported) {
      return;
    }

    // Create event listener that calls handler function stored in ref
    const eventListener = (event) => savedHandler.current(event.which);
    element.addEventListener(eventName, eventListener, { passive: true });

    return function cleanup() {
      element.removeEventListener(eventName, eventListener);
    };
  }, [eventName, element, ...deps]);
};
