import React, { useContext } from 'react';
import Link from 'components/link';

import HuntEmail from 'components/hunt_email';
import HuntInfoContext from 'components/context';
import Section from 'components/section';
import Table from 'components/table';

const About = () => {
  const { huntInfo } = useContext(HuntInfoContext);

  return (
    <Section title="About" narrow>
      FIXME: Add about section.
      <style jsx>{`
        th,
        td {
          padding: 0.3em;
          hyphens: auto;
        }
      `}</style>
    </Section>
  );
};

export default About;
