import { ReadyState } from 'react-use-websocket';
import HuntEmail from 'components/hunt_email';

const badStatuses = [ReadyState.CLOSING, ReadyState.CLOSED];

// Websocket connection happens in parallel to React doing its thing, so we need to make sure the
// number of child elements stays fixed no matter what the websocket connect state is. For that
// reason we don't use an InfoIcon here because we want to revert to an empty element after
// connection is done.
const WebsocketNotice = ({ readyState, showPostHunt = false }) => {
  if (process.env.useWorker && !showPostHunt) {
    return null;
  }
  return (
    <>
      {readyState === ReadyState.CONNECTING ? (
        <p className="text-center" suppressHydrationWarning>
          <i>Loading...</i>
        </p>
      ) : badStatuses.includes(readyState) ? (
        <p className="text-center" suppressHydrationWarning>
          Sorry, we're having trouble connecting to the server. Please refresh
          the page. If this error persists, please try again on the latest
          version of Chrome or Firefox, or report the issue to <HuntEmail />.
        </p>
      ) : (
        <p className="hidden"></p>
      )}

      <style jsx>{`
        :global(.darkmode) p {
          color: white;
        }
      `}</style>
    </>
  );
};

export default WebsocketNotice;
