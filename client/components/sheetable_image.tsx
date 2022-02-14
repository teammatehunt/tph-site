import React, { useMemo } from 'react';
import cx from 'classnames';

import { HIDDEN_CLASS, NO_COPY_CLASS } from 'components/copy';

/*
 * Generate an image that can be pasted into Google Sheets with the Copy to
 * Clipboard button.
 *
 * This works by inserting a Sheets formula to the static image when copied.
 * Note that images will not show in Sheets in dev because Google cannot load
 * from localhost.
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
  hiddenProps?: React.HTMLProps<HTMLSpanElement>;
}

const SheetableImage: React.FC<SheetableImageProps> = ({
  className = '',
  src,
  copySrc,
  hiddenProps = {},
  ...props
}) => {
  const absSrc = useMemo<string | undefined>(() => {
    const _src = copySrc ?? src;
    return typeof window === 'undefined'
      ? _src
      : _src && new URL(_src, window.location.href).href;
  }, [src, copySrc]);

  return (
    <>
      <img src={src} className={cx(className, NO_COPY_CLASS)} {...props} />
      {absSrc && (
        <span
          className={HIDDEN_CLASS}
          suppressHydrationWarning
          {...hiddenProps}
        >{`=IMAGE("${absSrc}")`}</span>
      )}
    </>
  );
};
export default SheetableImage;
