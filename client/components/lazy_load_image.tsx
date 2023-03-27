import React, { FC, useEffect, useMemo, useState } from 'react';
import {
  LazyLoadImage,
  LazyLoadImageProps,
} from 'react-lazy-load-image-component';
import 'react-lazy-load-image-component/src/effects/blur.css';

import { HIDDEN_CLASS, makeHrefAbsolute } from 'components/copy';

const Placeholder: FC<React.HTMLProps<HTMLDivElement>> = ({
  className,
  height = 200,
  ...props
}) => (
  <div className="placeholder">
    <style jsx>{`
      .placeholder {
        width: 100%;
        height: ${height}px;
      }
    `}</style>
  </div>
);

interface Props extends LazyLoadImageProps {
  placeholderHeight?: number;
  copySrc?: boolean | string;
}

const Image: FC<LazyLoadImageProps> = ({
  src,
  height,
  placeholder = undefined,
  placeholderHeight = undefined,
  visibleByDefault = false,
  copySrc = true,
  effect = 'blur',
  style,
  ...props
}) => {
  const [loaded, setLoaded] = useState(visibleByDefault);
  const [hasPrinted, setHasPrinted] = useState(false);
  const imagePlaceholder = placeholder ?? (
    <Placeholder height={placeholderHeight ?? height} />
  );

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const beforePrint = () => {
      setHasPrinted(true);
    };
    if (window.matchMedia) {
      window.matchMedia('print').addListener((mql) => {
        if (mql.matches) {
          beforePrint();
        }
      });
    }
    window.addEventListener('beforeprint', beforePrint);
    return () => window.removeEventListener('beforeprint', beforePrint);
  }, []);

  // regular height attribute gets clobbered by `height: auto;` in globals
  let _style = useMemo(() => {
    if (height === undefined) return style;
    if (style === undefined) return { height };
    return { ...style, height };
  }, [style, height]);

  return (
    <>
      <LazyLoadImage
        src={src}
        placeholder={imagePlaceholder}
        afterLoad={() => void setLoaded(true)}
        effect={effect}
        visibleByDefault={
          visibleByDefault || hasPrinted /* force images to load if printing */
        }
        style={_style}
        {...props}
      />
      {!loaded && (
        <p className="hidden print:block">
          Warning: if you see this message, please wait for this image to load
          before printing again.
        </p>
      )}
      {
        /* If lazy image hasn't been loaded yet, render invisible text for copy-to-clipboard.
         * This is not needed post-load because of copyjack. */
        typeof window !== 'undefined' && !loaded && copySrc && (
          <span className={HIDDEN_CLASS}>
            =image("{makeHrefAbsolute(copySrc === true ? src : copySrc)}")
          </span>
        )
      }
    </>
  );
};

export default Image;
