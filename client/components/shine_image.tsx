import React, {
  FunctionComponent,
  ImgHTMLAttributes,
  useEffect,
  useRef,
} from 'react';
import $ from 'jquery';

import cx from 'classnames';
import highlightMask from 'assets/public/highlight-mask.png';

interface Props {
  shine?: string;
  offset?: [number, number];
  interactable?: boolean;
}

const MASK_SIZE: number = 1000;

/**
 * Renders an image with a shiny animation on hover.
 */
const ShineImage: FunctionComponent<
  Props & ImgHTMLAttributes<HTMLImageElement>
> = ({ shine, interactable = true, children, ...props }) => {
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

  // Not sure if we need the wrapping div here. Will leave it for now.
  return (
    <div className="w-full">
      <div className="w-full relative">
        <img
          ref={iconEl}
          className={cx('icon', {
            interact: interactable,
          })}
          width="100%"
          {...props}
        />
        {shine && (
          <img
            ref={shineEl}
            className={cx('shine', {
              interact: interactable,
            })}
            width="100%"
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
        img {
          transition: transform 0.2s ease;
        }

        div:hover img.interact {
          transform: scale(1.05);
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
