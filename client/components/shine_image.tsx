import React, {
  FunctionComponent,
  ImgHTMLAttributes,
  useEffect,
  useRef,
} from 'react';
import $ from 'jquery';

import highlightMask from 'assets/public/highlight-mask.png';

interface Props {
  shine?: string;
  offset?: [number, number];
}

const MASK_SIZE: number = 1000;

/**
 * Renders an image with a shiny animation on hover.
 */
const ShineImage: FunctionComponent<
  Props & ImgHTMLAttributes<HTMLImageElement>
> = ({ shine, height, children, ...props }) => {
  const iconEl = useRef<HTMLImageElement>(null);
  const shineEl = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (shine && typeof window !== 'undefined') {
      function onMouseMove(e) {
        if (!iconEl.current || !shineEl.current) {
          return;
        }
        const iconOffset = $(iconEl.current).offset();
        const relX = e.pageX - iconOffset.left - MASK_SIZE / 2;
        const relY = e.pageY - iconOffset.top - MASK_SIZE / 2;

        shineEl.current.style.webkitMaskPosition = `${relX}px ${relY}px`;
      }
      window.addEventListener('mousemove', onMouseMove);

      return () => window.removeEventListener('mousemove', onMouseMove);
    }
  }, []);

  return (
    <div className="container">
      <div className="wrapper">
        <img ref={iconEl} className="icon" height={height} {...props} />
        {shine && (
          <img
            ref={shineEl}
            className="shine"
            height={height}
            {...props}
            src={shine}
            style={{
              WebkitMaskImage: `url("${highlightMask}")`,
            }}
          />
        )}
      </div>
      {children}

      <style jsx>{`
        .container {
          height: 100%;
        }

        .wrapper {
          position: relative;
        }

        .wrapper {
          height: ${height}px;
        }

        img {
          position: absolute;
          transform: translateX(-50%);
          transition: transform 0.2s ease;
        }

        div:hover img {
          transform: translateX(-50%) scale(1.05);
        }

        .shine {
          -webkit-mask-size: ${MASK_SIZE}px;
          -webkit-mask-repeat: no-repeat;
          -webkit-mask-position: -180px 180px;
        }
      `}</style>
    </div>
  );
};

export default ShineImage;
