import React, { FunctionComponent, ReactFragment } from 'react';
import dynamic from 'next/dynamic';
import { AlertTriangle, Info } from 'react-feather';

import { Normal } from 'components/copy';

const ReactTooltip = dynamic(() => import('react-tooltip'), {
  ssr: false,
});

interface Props {
  color?: string;
  center?: boolean;
  warning?: boolean;
  tooltipMessage?: ReactFragment;
}

/**
 * Shows a little info (i) icon with a tooltip for help text.
 * Generally used for accessibility / explanations that are puzzle content.
 */
const InfoIcon: FunctionComponent<Props> = ({
  color,
  tooltipMessage,
  center = false,
  warning = false,
  children,
}) => {
  const Component = warning ? AlertTriangle : Info;
  return (
    <>
      <div className={center ? 'flex-center-vert' : undefined}>
        <span className="icon">
          <Component data-tip="" data-for="info-tooltip" />
        </span>
        <span>{children}</span>
      </div>
      {tooltipMessage && (
        <ReactTooltip
          id="info-tooltip"
          effect="solid"
          getContent={() => <span className="message">{tooltipMessage}</span>}
        />
      )}
      <Normal />

      <style jsx>{`
        div {
          align-items: center;
          color: ${color ?? '#555'};
          display: flex;
        }

        /* Override color in dark mode, unless on a light background. */
        :global(.darkmode section:not(.background)) div {
          color: var(--primary);
        }

        .icon {
          margin: 8px 12px 0 0;
        }

        .flex-center-vert .icon {
          margin-top: 0;
        }

        .flex-center-vert :global(img) {
          vertical-align: middle;
        }

        .message {
          font-family: 'Roboto', sans-serif;
        }
      `}</style>
    </>
  );
};

export default InfoIcon;
