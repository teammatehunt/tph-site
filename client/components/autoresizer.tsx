import React, { useEffect, useRef, useState } from 'react';
import cx from 'classnames';

import useScreenSize from 'utils/useScreenSize';

interface Props {
  className?: string;
  maxWidth?: number;
  fitScreen?: boolean;
  aspectRatio?: number;
  maxHeightFraction?: number;
  center?: boolean;
}

const AutoResizer: React.FC<Props> = ({
  className,
  maxWidth = 10000, // Set to some absurd value by default
  fitScreen = true,
  aspectRatio = 1,
  center = false,
  maxHeightFraction = 1,
  children,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const { width: w, height: h } = useScreenSize();
  const [width, setWidth] = useState(w);
  const [height, setHeight] = useState(h);
  const scale = Math.min(1, Math.max(width / w, height / h));

  useEffect(() => {
    const onResize = () => {
      if (ref.current) {
        const refWidth = ref.current.offsetWidth;
        const refHeight = ref.current.offsetHeight;
        let newWidth = Math.min(maxWidth, refWidth);
        let newHeight = Math.min((maxWidth * refHeight) / refWidth, refHeight);
        if (fitScreen) {
          newWidth = Math.min(h * aspectRatio * maxHeightFraction, newWidth);
          newHeight = Math.min(h * maxHeightFraction, newHeight);
        }
        setWidth(newWidth);
        setHeight(newHeight);
      }
    };
    let resizeObs: ResizeObserver | null = null;
    if (window.ResizeObserver && ref.current) {
      resizeObs = new ResizeObserver(onResize);
      resizeObs.observe(ref.current);
    }
    // Always run onResize after a bit of delay after full load.
    setTimeout(onResize, 100);
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      if (resizeObs && ref.current) {
        resizeObs.unobserve(ref.current);
      }
    };
  }, []);

  return (
    <div className="w-full relative" ref={ref}>
      <div
        className={cx('canvas w-full relative', className, {
          'flex justify-center': center,
        })}
      >
        {typeof children === 'function'
          ? children(width, height, ref)
          : children}
      </div>

      <style jsx>{`
        .canvas {
          top: 0;
          left: 0;
          transform: scale(${scale});
          transform-origin: center;
        }
      `}</style>
    </div>
  );
};

export default AutoResizer;
