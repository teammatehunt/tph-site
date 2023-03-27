import React from 'react';
import Head from 'next/head';
import cx from 'classnames';

interface Props {
  title: string;
  pageTitle?: string;
  suppressPageTitle?: boolean;
  removeMargin?: boolean;
  subline?: string;
  id?: string;
  className?: string;
}

/** A generic title component for BIG TEXT. */
const Title = ({
  title,
  pageTitle,
  suppressPageTitle,
  removeMargin,
  subline,
  id,
  className,
}: Props) => {
  const shownTitle = pageTitle || title;
  return (
    <>
      {!suppressPageTitle && (
        <Head>
          <title>{shownTitle}</title>
        </Head>
      )}
      <h1
        id={id}
        className={cx('text-center', className, {
          small: title.length >= 20,
          'm-0': removeMargin,
        })}
      >
        <span>{title}</span>
      </h1>
      {subline && (
        <div className="subline font-title text-center">{subline}</div>
      )}

      <style jsx>{`
        h1.small {
          font-size: 10vh;
          line-height: 10vh;
        }

        .subline {
          color: var(--secondary);
          font-size: 24px;
          letter-spacing: 0.1em;
          margin-bottom: 20px;
        }

        span {
          padding: 0 16px;
        }

        @media (max-width: 600px) {
          h1 {
            font-size: 40px !important;
            line-height: 32px;
          }
        }
      `}</style>
    </>
  );
};

export default Title;
