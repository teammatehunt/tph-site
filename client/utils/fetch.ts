import HuntInfoContext from 'components/context';
import { useRouter } from 'next/router';
import { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import _useWebSocket, {
  Options as WebSocketOptions,
} from 'react-use-websocket';

import { useWorkerChannel, workerFetch } from 'utils/worker';

const SERVER_ENDPOINT = 'http://localhost:8000';

interface StatusCode {
  statusCode: number;
}

export const serverFetch = async <T>(
  context,
  endpoint: string,
  options: object = { method: 'GET' }
): Promise<StatusCode & T> => {
  if (typeof window !== 'undefined') {
    throw new Error('called serverFetch from a browser!');
  }
  // Constructing a URL object is required to make URLs with emojis work
  // (i.e. fetching info for a team with emojis in its name).
  const url = new URL(SERVER_ENDPOINT + '/api' + endpoint);
  const response = await fetch(url.toString(), {
    headers: { cookie: context.req.headers.cookie },
    ...options,
  });

  const statusCode = response.status;
  if (statusCode == 401) {
    context.res.writeHead(307, {
      Location: '/login?next=' + encodeURIComponent(context.req.url),
    });
    context.res.end();
  }

  // Override response status code if initial req is 200, but API call is not.
  if (context.res.statusCode === 200 && statusCode !== 200) {
    context.res.statusCode = statusCode;
  }
  return response.json().then((data: T) => ({
    statusCode,
    ...data,
  }));
};

export const clientFetch = async <T>(
  router,
  endpoint,
  options: object = { method: 'GET' },
  force = false
): Promise<StatusCode & T> => {
  // URL objects are not valid unless they have http:// at the start.
  // But, we cannot add SERVER_ENDPOINT for clientFetch becuase it triggers
  // Cross-Origin Request Blocked. For now, since the requests with emoji URLs
  // only get called through serverFetch, leave it as-is.
  const path = '/api' + endpoint;

  let result;
  if (force || !process.env.useWorker) {
    const response = await fetch(path, options);
    result = response.json().then((data: T) => ({
      ...data,
      statusCode: response.status,
    }));
  } else {
    const response = await workerFetch(path, {
      cookie: document?.cookie,
      ...options,
    });
    const data = JSON.parse(new TextDecoder().decode(response.content));
    result = {
      ...data,
      statusCode: response.status,
    };
  }

  if (result.statusCode == 401) {
    router.push('/login?next=' + encodeURIComponent(window.location.pathname));
  }

  return result;
};

// use react-use-websocket with reconnect options
export const useWebSocket = (
  url: string | null,
  options: WebSocketOptions = {},
  connect = true
) => {
  const defaults = {
    retryOnError: true,
    shouldReconnect: (e) => true,
    reconnectAttempts: Infinity,
    reconnectInterval: 20 * 1000, // ms
    onError: (e) => {
      console.log('Error connecting to websocket: ', e);
    },
  };
  return _useWebSocket(url, { ...defaults, ...options }, connect);
};

export const getPuzzleSlug = () => {
  if (typeof window !== 'undefined') {
    const regexPuzzlePath = /\/puzzles\/([^\/]+)/;
    const match = window.location.pathname.match(regexPuzzlePath);
    if (match) {
      const puzzle = match[1];
      return puzzle;
    }
  }
  return null;
};

interface EventWebSocketOptions extends WebSocketOptions {
  uuid?: string;
}

interface EventWebSocketProps {
  onJson?: ({ key: string, data: any }) => any;
  key?: string;
  options?: EventWebSocketOptions;
  allowLoggedOut?: boolean;
}
// This is the default web socket hook that should be used within our code. It
// will detect whether the user is on a puzzle page (not counting hint /
// solution pages) and get events for the entire team and also for the current
// puzzle.
//
// Parameters:
// onJson: message callback taking {key: string, data: any}, where key and data
//   are the values given to ClientConsumer.send_event. This should be a
//   static function or else create from a useCallback hook.
// key: key to filter by before handling. Using a filter key is slightly
//   preferable to filtering in the callback to reduce rerendering.
// options (optional): other options to override defaults
export const useEventWebSocket = ({
  onJson,
  key,
  options = {},
  allowLoggedOut = false,
}: EventWebSocketProps) => {
  const { userInfo } = useContext(HuntInfoContext);
  let url: string | null = null;
  if (typeof window !== 'undefined') {
    const puzzle = getPuzzleSlug();
    let wsPath = puzzle ? `/ws/puzzles/${puzzle}` : '/ws/events';
    const queryString = options.uuid ? `?uuid=${options.uuid}` : '';
    url = `wss://${window.location.host}${wsPath}${queryString}`;
  }

  const defaults: WebSocketOptions = {
    share: true,
  };
  if (key) {
    defaults.filter = (message) => JSON.parse(message.data).key === key;
  }
  const onMessage = useMemo(() => {
    if (!onJson) return undefined;
    return (message) => {
      const data = JSON.parse(message.data);
      if (key && data.key !== key) {
        return;
      }
      return onJson(data);
    };
  }, [onJson]);
  if (onJson) {
    defaults.onMessage = onMessage;
  }

  if (process.env.useWorker) {
    return useWorkerChannel({
      onMessage: onJson && onMessage,
      url,
    });
  } else {
    // Only connect if logged into a team and the server is running
    const connect = Boolean(
      (allowLoggedOut || userInfo?.teamInfo) && !process.env.isStatic
    );
    return useWebSocket(url, { ...defaults, ...options }, connect);
  }
};
