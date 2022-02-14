import React, { FunctionComponent, ImgHTMLAttributes } from 'react';

interface Props {
  offsetX?: number;
  offsetY?: number;
  brightness?: number;
  alwaysShadow?: boolean;
}

/**
 * Renders an image with a drop-shadow on hover, adapted from
 * http://thenewcode.com/600/Creating-a-True-CrossBrowser-Drop-Shadow-Effect-With-CSS3-&-SVG
 * Note: requires image with transparent background!
 */
const ShadowImage: FunctionComponent<
  Props & ImgHTMLAttributes<HTMLImageElement>
> = ({
  offsetX = 8,
  offsetY = 8,
  brightness = 1,
  alwaysShadow = false,
  children,
  ...props
}) => (
  <div className={alwaysShadow ? 'shadow' : undefined}>
    <img {...props} />
    {children}

    {/* SVG for Firefox */}
    <svg height="0" width="0" xmlns="http://www.w3.org/2000/svg">
      <filter id="drop-shadow">
        <feGaussianBlur in="SourceAlpha" stdDeviation="2.2" />
        <feOffset dx={offsetX} dy={offsetY} result="offsetblur" />
        <feFlood floodColor="rgba(0,0,0,0.25)" />
        <feComposite in2="offsetblur" operator="in" />
        <feMerge>
          <feMergeNode />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </svg>

    <style jsx>{`
      div {
        height: 100%;
        position: relative;
      }

      div:hover,
      div.shadow {
        filter: "progid:DXImageTransform.Microsoft.Dropshadow(OffX=${offsetX}, OffY=${offsetY}, Color='#444')";
        filter: url(#drop-shadow);
        filter: drop-shadow(${offsetX} ${offsetY} 8px rgba(0, 0, 0, 0.25));
      }

      img {
        filter: ${brightness === 1
          ? 'none'
          : `brightness(${brightness}) contrast(0.8)`};
      }
    `}</style>
  </div>
);

export default ShadowImage;
