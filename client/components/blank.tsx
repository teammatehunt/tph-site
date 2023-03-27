import React, { FC, Fragment, HTMLProps, useState } from 'react';

import { HIDDEN_CLASS, NO_COPY_CLASS, Monospace } from 'components/copy';

interface Props {
  count?: number;
  showCount?: boolean;
  children?: React.ReactNode;
}

/** Renders a number of accessibility-friendly blank lines. */
const Blank: FC<Props> = ({ count = 4, showCount = false, children }) => {
  return (
    <span role="figure" aria-label={showCount ? `${count} blanks` : 'blank'}>
      <span className={showCount ? 'blanks' : HIDDEN_CLASS}>
        {Array.from(Array(count)).map((_, i) => (
          <Fragment key={i}>
            _{i === Math.floor(count / 2) ? children : undefined}
          </Fragment>
        ))}
      </span>
      {
        /* When we don't care about showing count, use underline */
        !showCount && (
          <u className={NO_COPY_CLASS}>
            {Array.from(Array(count)).map((_, i) => (
              <Fragment key={i}>
                &nbsp;{i === Math.floor(count / 2) ? children : undefined}
              </Fragment>
            ))}
          </u>
        )
      }
    </span>
  );
};

export default Blank;
