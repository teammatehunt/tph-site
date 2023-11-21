import React, { useContext } from 'react';
import Link, { LinkIfStatic } from 'components/link';
import parse from 'html-react-parser';

import HuntInfoContext from 'components/context';
import InfoIcon from 'components/info_icon';
import Section from 'components/section';
import { serverFetch } from 'utils/fetch';

interface Event {
  slug: string;
  name: string;
  location: string;
  expected_start_time: string;
  min_participants: number;
  max_participants: number;
  description: string;
  status: string;
}

interface Props {
  events: Event[];
  currency: number;
  strongCurrency: number;
  info: string;
}

// Formats as "Friday, 9 pm"
const formattedDateTime = (time) => {
  const date = new Date(time);
  return (
    date
      .toLocaleDateString('en-US', {
        weekday: 'long',
        hour: 'numeric',
        timeZone: 'US/Eastern',
      })
      .replace(/.M/, (match) => match.toLowerCase()) + ' EST'
  );
};

const Events: React.FC<Props> = ({
  currency,
  strongCurrency,
  events,
  info,
}) => {
  const { userInfo, huntInfo } = useContext(HuntInfoContext);
  return (
    <Section title="Events" narrow>
      {!!userInfo?.teamInfo &&
        huntInfo.secondsToStartTime <= 0 &&
        !userInfo?.public && (
          <div className="mt-4 border border-dashed border-black p-2 rounded">
            <InfoIcon>
              You have{' '}
              <b>
                {currency} event reward{currency === 1 ? '' : 's'}
              </b>
              . Each event gives two event rewards.
              <br />
              You have{' '}
              <b>
                {strongCurrency} strong reward{strongCurrency === 1 ? '' : 's'}
              </b>
              .
            </InfoIcon>
            <p>{parse(info)}</p>
            <Link href="/events/free-answer">
              <a>Use a free answer</a>
            </Link>
            <br />
            <Link href="/events/unlock">
              <a>Unlock a new puzzle</a>
            </Link>
            <br />
            <Link href="/events/stronger-free-answer">
              <a>Use a strong free answer</a>
            </Link>
          </div>
        )}
      <p>
        Please show up on time! All events are at the MIT Student Center (84
        Massachusetts Avenue).
      </p>
      {events.map((event, idx) => (
        <div key={idx}>
          <h2>{event.name}</h2>
          <h4>
            {formattedDateTime(event.expected_start_time)} - {event.location}
          </h4>
          <h5>
            {event.min_participants && `${event.min_participants}–`}
            {event.max_participants} participants
          </h5>
          {event.status === 'post' && (
            <div className="primary">
              This event is now over. You may{' '}
              <LinkIfStatic
                href={`${
                  process.env.isArchive ? `/20xx/${process.env.domainName}` : ''
                }/${userInfo?.public ? 'solutions' : 'events'}/${event.slug}`}
              >
                {userInfo?.public ? 'view event details' : 'submit an answer'}
              </LinkIfStatic>{' '}
              here.
            </div>
          )}
          <p>{event.description}</p>
        </div>
      ))}
    </Section>
  );
};

export default Events;

export const getServerSideProps = async (context) => {
  const props = await serverFetch<Props>(context, '/events', {
    method: 'GET',
  });
  return { props };
};
