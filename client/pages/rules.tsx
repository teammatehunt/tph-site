import React, { useContext } from 'react';
import Link from 'next/link';

import HuntInfoContext from 'components/context';
import Section from 'components/section';
import Title from 'components/title';
import { formattedDateTime } from 'utils/timer';

const Rules = () => {
  const { huntInfo } = useContext(HuntInfoContext);

  // FIXME
  return (
    <>
      <Title title="Rules" subline="For All Our Guests" />

      {/* FIXME: Update based on this year's rules. */}
      <Section narrow heading="Format">
        <ul>
          <li>
            FIXME Hunt Title (i.e. the puzzlehunt) starts on{' '}
            <strong>{formattedDateTime(huntInfo.startTime)}</strong> and ends on{' '}
            <strong>{formattedDateTime(huntInfo.endTime)}</strong>.
          </li>
        </ul>
      </Section>

      <style jsx>{`
        li {
          padding-bottom: 8px;
        }
      `}</style>
    </>
  );
};

export default Rules;
