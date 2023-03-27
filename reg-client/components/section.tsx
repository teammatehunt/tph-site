import React, { FC, ReactNode } from 'react';
import cx from 'classnames';

const Heading: React.FC<{}> = ({ children }) => (
  <div className="heading flex items-center text-center space-x-2">
    <hr />
    <h3 className="italic max-w-[85%]">{children}</h3>
    <hr />

    <style jsx>{`
      hr {
        border-color: var(--secondary);
        border-bottom: none;
        height: 1px;
        flex-grow: 1;
      }
    `}</style>
  </div>
);

export interface SectionProps {
  heading?: ReactNode;
  center?: boolean;
  narrow?: boolean;
  blur?: boolean;
  darkMode?: boolean;
}

const Section: React.FC<SectionProps & React.HTMLProps<HTMLElement>> = ({
  heading,
  center = false,
  narrow = false,
  blur = false,
  darkMode = false,
  children,
  className,
  ...props
}) => (
  <section
    className={cx(
      'mx-auto',
      { center, narrow, darkmode: darkMode, 'bg-blur': blur },
      className
    )}
    {...props}
  >
    {heading && <Heading>{heading}</Heading>}
    {children}

    <style jsx>{`
      section {
        padding: 20px 60px;
        width: min(100%, 80vw);
      }

      /* Remove extra margin for successive sections. */
      section.pt-0 {
        padding-top: 0;
      }

      section ~ section {
        margin-top: 20px;
        padding-top: 0;
      }

      /* Remove padding for nested sections. */
      section section {
        padding: 0;
      }

      section.narrow {
        max-width: 600px;
        padding: 20px;
      }

      section.medium {
        max-width: 900px;
        padding: 20px;
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
