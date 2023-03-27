import Link from 'components/link';
import InfoIcon from 'components/info_icon';

const EventPuzzle = () => {
  return (
    <div>
      <InfoIcon>
        This event has ended. Solvers would have received an answer upon
        completing the event.
      </InfoIcon>
      <p>
        <Link href="/events">
          <a>Return to the Events page</a>
        </Link>
      </p>
    </div>
  );
};

export default EventPuzzle;
