import React, { FC, HTMLProps, ReactFragment } from 'react';
import cx from 'classnames';
import dynamic from 'next/dynamic';
import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

const ReactTooltip = dynamic(() => import('react-tooltip'), {
  ssr: false,
});

interface Props {
  border?: boolean;
  color?: string;
  center?: boolean;
  warning?: boolean;
  tooltipMessage?: ReactFragment;
  // If provided, use an existing ReactTooltip on the page.
  tooltipId?: string;
  tooltipClassname?: string;
}

/**
 * Shows a little info (i) icon with a tooltip for help text.
 * Generally used for accessibility / explanations that are puzzle content.
 */
const InfoIcon: FC<Props & HTMLProps<HTMLSpanElement>> = ({
  color,
  tooltipMessage,
  tooltipId,
  tooltipClassname,
  border = false,
  center = false,
  warning = false,
  className,
  children,
}) => {
  const Component = warning ? ExclamationTriangleIcon : InformationCircleIcon;
  return (
    <>
      <div
        className={cx('flex rounded-md items-center space-x-2', {
          'justify-center': center,
          'border border-dashed border-black dark:border-white p-2': border,
        })}
      >
        <Component
          className="h-6 w-6 min-w-[1.5rem]"
          data-tip={tooltipId ? tooltipMessage : ''}
          data-for={tooltipId ?? 'info-tooltip'}
        />
        <span className={className}>{children}</span>
      </div>
      {tooltipMessage && !tooltipId && (
        <ReactTooltip
          id="info-tooltip"
          effect="solid"
          getContent={() => (
            <span className={tooltipClassname || 'message'}>
              {tooltipMessage}
            </span>
          )}
        />
      )}

      <style jsx>{`
        div {
          color: ${color ?? '#555'};
        }

        /* Override color in dark mode, unless on a light background. */
        :global(.darkmode) div {
          color: ${color ?? 'var(--white)'};
        }

        .justify-center :global(img) {
          vertical-align: middle;
        }

        .message {
          font-family: 'Roboto', sans-serif;
        }

        @media print {
          :global(.darkmode) div {
            color: black;
          }
        }
      `}</style>
    </>
  );
};

export default InfoIcon;
