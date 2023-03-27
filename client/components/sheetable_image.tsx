import React, { useMemo } from 'react';
import cx from 'classnames';

import { HIDDEN_CLASS, NO_COPY_CLASS } from 'components/copy';

/*
 * Generate an image that can be pasted into Google Sheets with the Copy to
 * Clipboard button.
 *
 * NOTE: with the implementation of copyjack this component is mostly unnecessary.
 * The main usage for this is to specify a copySrc that is distinct from the
 * rendered image on the website; for example, if you want to show SVGs but copy
 * PNGs, since SVGs are not supported in Google Sheets.
 *
 * When using, you should make sure that the formula will get its own cell, for
 * example by putting the <SheetableImage/> in a <td/> or <div/>.
 *
 * Note: if you want to style the img, you will need to use the resolve tag
 * (https://github.com/vercel/styled-jsx#the-resolve-tag) and pass in a className.
 */
interface SheetableImageProps
  extends React.ImgHTMLAttributes<HTMLImageElement> {
  copySrc?: string;
  hiddenProps?: React.ImgHTMLAttributes<HTMLImageElement>;
}

const SheetableImage: React.FC<SheetableImageProps> = ({
  className = '',
  src,
  copySrc,
  hiddenProps = {},
  children,
  ...props
}) => {
  return (
    <>
      {children === undefined ? (
        <img
          src={src}
          className={cx(className, { [NO_COPY_CLASS]: !!copySrc })}
          {...props}
        />
      ) : (
        children
      )}
      {copySrc && (
        <img
          src={copySrc}
          className={HIDDEN_CLASS}
          {...props}
          {...hiddenProps}
        />
      )}
    </>
  );
};
export default SheetableImage;
