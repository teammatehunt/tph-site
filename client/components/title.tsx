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
}

/** A generic title component for BIG TEXT. */
const Title = ({
  title,
  pageTitle,
  suppressPageTitle,
  removeMargin,
  subline,
  id,
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
        className={cx({ small: title.length >= 20, nomargin: removeMargin })}
      >
        <span>{title}</span>
      </h1>
      {subline && <div className="subline">{subline}</div>}

      <style jsx>{`
        h1 {
          text-align: center;
        }

        h1.small {
          font-size: 10vh;
          line-height: 10vh;
        }

        .subline {
          color: var(--secondary);
          font-family: var(--title-font), serif;
          font-size: 24px;
          letter-spacing: 0.1em;
          text-align: center;
          margin-bottom: 20px;
        }

        .nomargin {
          margin: 0px;
        }

        span {
          padding: 0 16px;
        }

        @media (max-width: 600px) {
          h1 {
            font-size: 80px;
            line-height: 88px;
          }
        }
      `}</style>
    </>
  );
};

export default Title;
