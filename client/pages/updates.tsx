import React, { useContext } from 'react';
import parse from 'html-react-parser';

import HuntInfoContext, { Errata } from 'components/context';
import Section from 'components/section';
import Title from 'components/title';
import { formattedDateTime } from 'utils/timer';
import StoryNotifications from 'components/story_notifications';

const Updates = () => {
  const { userInfo } = useContext(HuntInfoContext);
  // If they're looking at Story they don't need to see the notification anymore.
  if (userInfo?.errata) {
  }
  return (
    <>
      <Title title="Updates and Errata" />
      <StoryNotifications onlyFinished />
      <Section>
        <p>Hunt updates and puzzle errata will appear here.</p>
        {(!userInfo || userInfo?.errata?.length == 0) && (
          <p>There is currently no puzzle errata. We hope it stays that way!</p>
        )}
        {userInfo?.errata?.map((err, i) => (
          <p className="error" key={`errata-${i}`}>
            <b>Erratum</b> on{' '}
            {formattedDateTime(err.time, {
              month: 'numeric',
              year: '2-digit',
              second: undefined,
            })}
            , for <b>{err.puzzleName}</b>: {parse(err.text)}
          </p>
        ))}
      </Section>
    </>
  );
};

export default Updates;
