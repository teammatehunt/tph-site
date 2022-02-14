import React from 'react';
import cx from 'classnames';

interface Props {
  ratio?: number;
  as?: React.ElementType;
  extraPadding?: number;
  className?: string;
  children?: React.ReactNode;
}

/** Cross-browser compatible wrapper to ensure a specific aspect-ratio in CSS. */
export default function AspectRatio<T>({
  ratio,
  as,
  extraPadding = 0,
  className,
  children,
  ...props
}: Props & T): JSX.Element {
  const Component = as ?? 'div';
  return (
    <div className={cx('container', className)}>
      <Component className="wrapper" {...props}>
        {children}
      </Component>

      <style jsx>{`
        .container {
          position: relative;
        }

        .container {
          padding-top: ${ratio ?? 56.25}%;
        }

        .container {
          padding-bottom: ${extraPadding}px;
        }

        .wrapper {
          position: absolute;
          left: 0;
          top: 0;
          right: 0;
          bottom: 0;
        }
      `}</style>
    </div>
  );
}
