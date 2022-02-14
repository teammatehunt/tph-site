import React, { FunctionComponent, ReactNode } from 'react';
import cx from 'classnames';

const Heading: FunctionComponent<{}> = ({ children }) => (
  <div className="heading center">
    <hr />
    <h3>{children}</h3>
    <hr />
    <style jsx>{`
      .heading {
        display: flex;
        align-items: center;
      }

      hr {
        border-color: var(--secondary);
        border-bottom: none;
        height: 1px;
        flex-grow: 1;
      }

      hr:first-child {
        margin-right: 12px;
      }

      hr:last-child {
        margin-left: 12px;
      }

      h3 {
        font-style: italic;
        font-weight: 400;
        max-width: 85%;
      }
    `}</style>
  </div>
);

interface Props {
  heading?: ReactNode;
  center?: boolean;
  background?: boolean;
  narrow?: boolean;
}

const Section: FunctionComponent<Props & React.HTMLProps<HTMLElement>> = ({
  heading,
  center = false,
  background = false,
  narrow = false,
  children,
  className,
  ...props
}) => (
  <section className={cx({ center, background, narrow }, className)} {...props}>
    {heading && <Heading>{heading}</Heading>}
    {children}

    <style jsx>{`
      section {
        padding: 20px 60px;
        width: 80vw;
        margin-left: auto;
        margin-right: auto;
      }

      /* Remove extra margin for successive sections. */
      section ~ section {
        padding-top: 0;
      }

      section.background {
        background-color: rgba(255, 255, 255, 0.8);
        outline: solid 1px var(--yellow);
        outline-offset: 12px;
      }

      :global(body) section.background,
      section.background :global(h1),
      section.background :global(h2),
      section.background :global(h3),
      section.background :global(h4),
      section.background :global(h5),
      section.background :global(h6),
      section.background :global(.primary) {
        color: var(--black);
      }

      section.background :global(.secondary) {
        color: var(--red);
      }

      section.background :global(input) {
        border: 1px solid var(--black);
        color: var(--black);
      }

      section.narrow {
        max-width: 600px;
        padding: 20px 10px;
      }

      section[id]::before {
        content: '';
        display: block;
        height: 72px;
        margin-top: -72px;
        visibility: hidden;
      }

      @media (max-width: 800px) {
        section {
          padding: 20px;
          width: 100%;
        }
      }
    `}</style>
  </section>
);

export default Section;
