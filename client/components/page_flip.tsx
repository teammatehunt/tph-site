import React, { useEffect, useRef } from 'react';
import $ from 'jquery';
import 'turn.js';

import { KeyCode, useEventListener } from 'utils/keyboard';

const PADDING = 20;

/**
 * Component that animates flipping pages of a book.
 * Warning: because Turn.js has client-side only code, this component must be
 * loaded dynamically without server-side render:
 * https://nextjs.org/docs/advanced-features/dynamic-import#with-no-ssr
 */
const PageFlip = ({
  options: { width, height, display, ...options },
  children,
}) => {
  const bookRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const windowWidth = $(window).width();
    const windowHeight = $(window).height();

    $(bookRef.current).turn({
      width: Math.min(windowWidth - PADDING * 2, width),
      height: Math.min(windowHeight - PADDING * 2, height),
      // Show single page on small screens.
      display: windowWidth < 500 ? 'single' : display,
      ...options,
    });

    function cleanup() {
      $(bookRef.current).turn('destroy').remove();
    }
  }, [bookRef.current]);

  useEventListener('keyup', (key) => {
    if (!bookRef.current) {
      return;
    }
    switch (key) {
      case KeyCode.LEFT:
        $(bookRef.current).turn('previous');
        break;
      case KeyCode.RIGHT:
        $(bookRef.current).turn('next');
        break;
    }
  });

  return <div ref={bookRef}>{children}</div>;
};

export default PageFlip;
