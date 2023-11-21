import HuntInfoContext from 'components/context';
import { GetServerSidePropsContext, NextPageContext } from 'next';
import { NextRouter } from 'next/router';
import { Router, useRouter } from 'utils/router';
import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import _useWebSocket, {
  Options as WebSocketOptions,
} from 'react-use-websocket';
import { gunzipSync } from 'fflate';

import { useWorkerChannel, workerFetch } from 'utils/worker';

const SERVER_ENDPOINT = 'http://django:8000';

interface StatusCode {
  statusCode: number;
}

export type CryptKeys = Record<string, string>;
type AddDecryptKeysProps<T extends Object> = T & {
  cryptKeys?: CryptKeys;
};
// Add global keys to be used by encrypted js sources.
// Ignore on the server since serverside sources are not encrypted.
// Returns the object with keys removed.
export const addDecryptionKeys = <T>({
  cryptKeys,
  ...rest
}: AddDecryptKeysProps<T>) => {
  if (cryptKeys && typeof window !== 'undefined') {
    const s = self as any;
    s.cryptKeys = Object.assign(s.cryptKeys || {}, cryptKeys);
  }
  return rest;
};

// extract the /20xx/mypuzzlehunt.com etc
// Note that this gets called by the router in utils/router and thus that
// router should use router.basePath directly unless also needing error validation.
// The input to this should be a Next.js router or context, not our Router proxy.
export const getBasePath = (context: NextRouter | NextPageContext | GetServerSidePropsContext, errIfInvalid=false) : string => {
  const rootBasePath = process.env.basePath ?? '';
  if (!process.env.isArchive) return rootBasePath;
  const pathname = 'pathname' in context ? context.pathname : context.resolvedUrl;
  let basePath = (rootBasePath + pathname).split('/').slice(0, 3).join('/');
  // NB: tree shaking ensures these are not in the source when isArchive is false
  const allowedBasePaths = [
    '/20xx/mypuzzlehunt.com',
    '/20xx/registration.mypuzzlehunt.com',
  ];
  if (!allowedBasePaths.includes(basePath)) {
    if (errIfInvalid) {
      throw new Error(`Invalid base path from concatenating "${rootBasePath}" and "${pathname}"`);
    }
    basePath = allowedBasePaths[0];
  }
  return basePath;
};

// Simulate fetch /api/hunt_info from the Next.js server to the Django server
// while building the static site. This function is synchronous.
// NB: GetStaticPropsContext doesn't have pathname in Next.js but we patch the
//     render function to include pathname during export
export const fetchHuntInfoStaticSync = <T>(
  router: Router,
) : StatusCode & T => {
  if (!process.env.isStatic) {
    throw new Error('called fetchStaticSync when not generating the static site');
  } else {
    // NB: needs conditional guard because webpack won't deduce that throwing exits
    const basePath = router.basePath;
    // use dumped api response for the static site
    // NB: these are loaded individually and explicitly so that Next.js does not
    //     try to pull in all possible asset paths
    // FIXME: replace 20xx and domains
    const data = {
      '/20xx/mypuzzlehunt.com': require('assets/json_responses/20xx/mypuzzlehunt.com/api/hunt_info'),
      '/20xx/registration.mypuzzlehunt.com': require('assets/json_responses/20xx/registration.mypuzzlehunt.com/api/hunt_info'),
    }[basePath];
    if (data === undefined) {
      throw new Error('did not find api response json');
    }
    return {
      statusCode: 200,
      ...data,
    };
  }
};

// perform a fetch from the Next.js server to the Django server
export const serverFetch = async <T>(
  context,
  endpoint: string,
  options: any = { method: 'GET' }
): Promise<StatusCode & T> => {
  if (typeof window !== 'undefined') {
    throw new Error('called serverFetch from a browser!');
  }
  // NB: GetStaticPropsContext doesn't have pathname in Next.js but we patch the
  //     render function to include pathname during export
  const basePath = getBasePath(context);

  const path = basePath + '/api' + endpoint;

  if (process.env.isStatic) {
    // Simulate performing a fetch from the Next.js server to the Django server
    // while building the static site.
    if (options.method !== 'GET') {
      throw new Error(`serverFetch ${endpoint} must be used with method GET`);
    }
    // use dumped api response for the static site
    let data;
    try {
      // `?` are converted to `+` so that require doesn't chop off the query
      data = await import(`assets/json_responses${path.replace(/\?/g, "+")}`);
    } catch {
      console.warn(`No response for ${path}`);
      // 404 if not found
      return {
        statusCode: 404,
      } as StatusCode & T;
    }
    return Promise.resolve({
      statusCode: 200,
      ...data,
    });
  }

  // Constructing a URL object is required to make URLs with emojis work
  // (i.e. fetching info for a team with emojis in its name).
  const url = new URL(SERVER_ENDPOINT + path);
  const response = await fetch(url.toString(), {
    headers: {
      cookie: context.req.headers.cookie,
      'x-forwarded-host': context.req.headers.host,
      'x-tph-site': context.req.headers['x-tph-site'],
    },
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
  context: NextRouter | NextPageContext,
  endpoint,
  options: object = { method: 'GET' },
  force = false
): Promise<StatusCode & T> => {
  // URL objects are not valid unless they have http:// at the start.
  // But, we cannot add SERVER_ENDPOINT for clientFetch becuase it triggers
  // Cross-Origin Request Blocked. For now, since the requests with emoji URLs
  // only get called through serverFetch, leave it as-is.
  const basePath = 'basePath' in context ? context.basePath : getBasePath(context);
  const path = basePath + '/api' + endpoint;

  let result;
  if (force || !process.env.useWorker) {
    const response = await fetch(path, options);
    result = {
      ...(await response.json()),
      statusCode: response.status,
    };
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

  // add any received keys
  result = addDecryptionKeys(result);

  if (result.statusCode == 401 && 'push' in context) {
    context.push('/login?next=' + encodeURIComponent(window.location.pathname));
  }

  return result;
};

// use react-use-websocket with reconnect options
export const useWebSocket = (
  url: string | null,
  options: WebSocketOptions = {},
  connect = true
) => {
  const didUnmount = useRef<boolean>(false); // track whether we've closed manually

  const defaults = {
    retryOnError: true,
    // Only reconnect if we haven't explicitly unmounted
    shouldReconnect: (e) => !didUnmount.current,
    reconnectAttempts: Infinity,
    reconnectInterval: 20 * 1000, // ms
    onError: (e) => {
      console.log('Error connecting to websocket: ', e);
    },
  };

  const websocketResponse = _useWebSocket(
    url,
    { ...defaults, ...options },
    connect
  );

  useEffect(() => {
    // On closing the window or tab, disconnect from the websocket.
    window.addEventListener('beforeunload', () => {
      didUnmount.current = true; // prevent from auto-reconnecting
      websocketResponse.getWebSocket()?.close();
    });
  }, []);

  return websocketResponse;
};

export const getRoundSlug = () => {
  if (typeof window !== 'undefined') {
    const regexRoundPath = /\/rounds\/([^\/]+)/;
    const match = window.location.pathname.match(regexRoundPath);
    if (match) {
      const round = match[1];
      return round;
    }
  }
  return null;
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
  // Override puzzle slug
  slug?: string;
  // Subpuzzle
  subpuzzle?: string;
  // Story slug for interactions
  storySlug?: string;
  // Round slug for rounds
  roundSlug?: string;
  // For tracking interactice puzzle sessions
  session_id?: number;
  // Whether or not to enable the websocket connection. Defaults to true.
  connect?: boolean;
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
//
// Returns:
//   sendJsonMessage: serialize a javascript Object to json and send over the
//     websocket.
//   readyState: boolean for whether the websocket is connected yet.
export const useEventWebSocket = ({
  onJson,
  key,
  options = {},
  allowLoggedOut = false,
}: EventWebSocketProps) => {
  const { userInfo } = useContext(HuntInfoContext);
  const router = useRouter();
  let url: string | null = null;
  if (typeof window !== 'undefined') {
    const puzzle = options.slug ?? getPuzzleSlug();
    const round = options.roundSlug ?? getRoundSlug();
    const storySlug = options.storySlug;
    let wsPath =
      router.basePath +
      (storySlug
        ? `/ws/story/${storySlug}`
        : puzzle
        ? `/ws/puzzles/${puzzle}`
        : '/ws/events');
    const params = new URLSearchParams();
    if (options.uuid) {
      params.append('uuid', options.uuid);
    }
    if (puzzle) {
      params.append('slug', puzzle);
    }
    if (options.subpuzzle) {
      params.append('subpuzzle', options.subpuzzle);
    }
    if (options.session_id) {
      params.append('session_id', options.session_id.toString());
    }
    if (round) {
      params.append('round_slug', round);
    }
    url = `wss://${window.location.host}${wsPath}?${params.toString()}`;
  }

  const defaults: WebSocketOptions = {
    share: true,
  };
  // conditioning is slightly messy due to Blobs only working in async contexts
  if (key) {
    defaults.filter = (message) => {
      return (
        typeof message.data !== 'string' || JSON.parse(message.data).key === key
      );
    };
  }
  const onMessage = useMemo(() => {
    if (!onJson) return undefined;
    return (message) => {
      const processMessage = (data) => {
        // Set and remove decryption keys if available.
        // NB: This will only run if there's at least one hook subscriber with a
        //     matching websocket filter key.
        data = addDecryptionKeys(data);
        if (key && data.key !== key) {
          return;
        }
        onJson(data);
      };
      if (typeof message.data === 'string') {
        // json data
        processMessage(JSON.parse(message.data));
      } else {
        // else binary blob with gzipped json data
        (async () => {
          // Blob is only async
          const data = new Uint8Array(await message.data.arrayBuffer());
          const decompressed = gunzipSync(data);
          const decoded = new TextDecoder().decode(decompressed);
          processMessage(JSON.parse(decoded));
        })();
      }
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
    const connect =
      (options.connect ?? true) &&
      Boolean((allowLoggedOut || userInfo?.teamInfo) && !process.env.isStatic);
    return useWebSocket(url, { ...defaults, ...options }, connect);
  }
};
