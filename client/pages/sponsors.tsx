import React from 'react';

import Section from 'components/section';

const Sponsors = () => {
  return (
    <Section title="Sponsors">
      <p>Insert sponsors here.</p>
      <style jsx>{`
        .mystery {
          font-size: 200px;
          line-height: 200px;
        }
        .sponsor {
          background-color: white;
          max-width: min(70%, 50vw);
          margin-bottom: 2rem;
        }
      `}</style>
    </Section>
  );
};

export default Sponsors;
