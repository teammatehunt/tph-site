import React, { ReactNode, useEffect } from 'react';

import LinkIfStatic from 'components/link';
import Section from 'components/section';
import Title from 'components/title';

const Wrapup = () => {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const id = entry.target.getAttribute('id');
        if (entry.intersectionRatio > 0) {
          document
            ?.querySelector(`nav li a[href="#${id}"]`)
            ?.classList.add('active');
        } else {
          document
            ?.querySelector(`nav li a[href="#${id}"]`)
            ?.classList.remove('active');
        }
      });
    });

    // Track all sections that have an `id` applied
    document?.querySelectorAll('section[id]').forEach((section) => {
      observer.observe(section);
    });
  }, []);

  const sections: {
    title: ReactNode;
    textTitle?: string;
    id: string;
    content?: ReactNode;
    subheadings?: {
      title: ReactNode;
      textTitle?: string;
      id: string;
      content?: ReactNode;
    }[];
  }[] = [
    {
      // FIXME
      title: '',
      id: 'fixme',
      content: <></>,
    },
  ];

  return (
    <>
      <div className="container flex-center">
        <nav>
          <h3>Table of Contents</h3>
          <ol>
            {sections.map(({ title, textTitle, id, subheadings }) => (
              <li key={`nav-${id}`}>
                <a href={id === 'intro' ? '#wrapup' : `#${id}`}>
                  <h4>{textTitle || title || 'Wrap-up'}</h4>
                </a>
                {subheadings && (
                  <ol>
                    {subheadings?.map((subsection) => (
                      <li key={`nav-${id}-${subsection.id}`}>
                        <a href={`#${id}-${subsection.id}`}>
                          <h4>{subsection.textTitle || subsection.title}</h4>
                        </a>
                      </li>
                    ))}
                  </ol>
                )}
              </li>
            ))}
          </ol>
        </nav>

        <div id="wrapup">
          <Title title="Wrap-up" />

          {sections.map(({ id, title, content, subheadings }) => (
            <Section key={id} id={id} heading={title}>
              {content &&
                (id === 'intro' ? content : <Section>{content}</Section>)}
              {subheadings?.map((subsection) => (
                <Section
                  key={`${id}-${subsection.id}`}
                  id={`${id}-${subsection.id}`}
                >
                  <h4>{subsection.title}</h4>
                  {subsection.content}
                </Section>
              ))}
            </Section>
          ))}
        </div>
      </div>

      <style jsx>{`
        #wrapup {
          flex-grow: 1;
          flex-shrink: 1;
          max-width: 100%;
        }

        nav {
          align-self: start;
          position: sticky;
          top: 2rem;
          overflow-y: auto;
          margin-left: 40px;
          max-height: 90vh;
          min-width: 280px;
          padding: 4px 8px;
        }

        @media (max-width: 600px) {
          .container {
            flex-wrap: wrap;
          }

          nav {
            position: initial;
          }
        }

        nav h4 {
          margin: 0;
        }

        nav li {
          list-style: none;
        }

        nav li a {
          text-decoration: none;
        }

        nav li a h4 {
          color: #888;
          transform: all 100ms ease-in-out;
        }

        nav li a:hover h4,
        nav li a.active h4,
        nav li a:focus h4 {
          color: #009;
        }
      `}</style>

      <style jsx global>{`
        html {
          scroll-behavior: smooth;
        }

        section {
          max-width: 1000px;
        }

        /*
          The <Section/> component sets the width of <section/> to 80vw. We
          only want this on the outermost <section/>.
         */
        section > section {
          width: 100% !important;
        }

        /* Allow word breaks anywhere for really long answers on mobile. */
        strong.monospace {
          word-break: break-all;
        }
      `}</style>
    </>
  );
};

export default Wrapup;
