import React, { Fragment, FunctionComponent, ReactFragment } from 'react';
import cx from 'classnames';

export type ClueFragment =
  | [ReactFragment]
  | [ReactFragment, string]
  | [ReactFragment, string, boolean];

interface Props {
  clue: ClueFragment[];
  tooltipId: string;
  answer: string;
  length?: string;
  showLength?: boolean;
}

const getEnumeration = (answer: string): string => {
  return answer.replace(/[a-zA-Z]+/g, (match) => match.length.toString());
};

/**
 * Annotates a cryptic clue with descriptions on hover.
 * Note that a ReactTooltip must be included somewhere on the page with tooltipId.
 */
const CrypticAnnotation: FunctionComponent<Props> = ({
  clue,
  tooltipId,
  answer,
  length = undefined,
  showLength = true,
}) => (
  <>
    {clue.map(([fragment, explanation = '', isDef = false], i) => {
      const description = [isDef ? 'Definition' : '', explanation]
        .filter((s) => !!s)
        .join(': ');
      return (
        <Fragment key={`${answer}-${i}`}>
          <span
            className={cx({ underline: isDef })}
            tabIndex={0}
            data-tip={description || null}
            data-for={tooltipId}
            aria-label={description}
          >
            {fragment}
          </span>{' '}
          <style jsx>{`
            span:focus,
            span:hover {
              color: var(--primary);
              cursor: help;
            }
          `}</style>
        </Fragment>
      );
    })}
    {showLength ? `(${length || getEnumeration(answer)})` : null}
  </>
);

export default CrypticAnnotation;
