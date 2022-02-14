import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { ReadyState } from 'react-use-websocket';
import { v4 as uuidv4 } from 'uuid';

export const SUPPORTS_SHARED_WORKER =
  !!globalThis.SharedWorker && !!globalThis.BroadcastChannel;
export const SUPPORTS_WORKER = SUPPORTS_SHARED_WORKER || !!globalThis.Worker;
export const WORKER_NAME = SUPPORTS_SHARED_WORKER ? 'SharedWorker' : 'Worker';

export const ERROR_SERVICE_WORKER_NOT_SUPPORTED = `${WORKER_NAME} is not supported in this browser.`;
export const ERROR_SERVICE_WORKER_NOT_READY = `${WORKER_NAME} is not ready yet.`;

/*
 * Interface is a subset of useWebSocket
 */
export const useWorkerChannel = ({ onMessage, url }) => {
  const { broadcastChannel, port, ready, readyPromise } = useWorker();
  const sendJsonMessage = useCallback(
    (jsonMessage: any) => {
      const func = async () => {
        const data = {
          type: 'websocket',
          url,
          data: jsonMessage,
        };
        await readyPromise;
        port?.postMessage(data);
      };
      func();
    },
    [url]
  );
  const onMessageToJson = useMemo(() => {
    if (!onMessage) return undefined;
    return (message) => {
      const data = JSON.stringify(message.data);
      onMessage({ data });
    };
  }, [onMessage]);
  useEffect(() => {
    if (onMessageToJson) {
      broadcastChannel?.addEventListener('message', onMessageToJson);
      return () => {
        broadcastChannel?.removeEventListener('message', onMessageToJson);
      };
    }
  }, [onMessageToJson]);
  const readyState = ready ? ReadyState.OPEN : ReadyState.CONNECTING;
  return { readyState, sendJsonMessage };
};

export const createWorker = () => {
  const workerUrl = '/worker.js';
  globalThis.workerContext = {};
  if (typeof window === 'undefined') {
    return;
  }
  let worker: SharedWorker | Worker | undefined = undefined;
  let broadcastChannel: BroadcastChannel | Worker | undefined = undefined;
  let port: MessagePort | Worker | undefined = undefined;
  if (SUPPORTS_SHARED_WORKER) {
    worker = new SharedWorker(workerUrl);
    broadcastChannel = new BroadcastChannel('shared-worker-broadcast');
    port = worker.port;
  } else if (SUPPORTS_WORKER) {
    worker = new Worker(workerUrl);
    broadcastChannel = worker;
    port = worker;
  }
  globalThis.workerContext.ready = false;
  globalThis.workerContext.error = false;
  globalThis.workerContext.readyPromise = new Promise((resolve, reject) => {
    if (!worker || !broadcastChannel) {
      globalThis.workerContext.error = Error(`${WORKER_NAME} is unavailable.`);
      resolve(false);
      console.error(globalThis.workerContext.error);
      return;
    }
    const workerReadyCallback = (message) => {
      if (message.data.type === 'worker-ready') {
        console.log(`${WORKER_NAME} is ready.`);
        globalThis.workerContext.ready = true;
        resolve(true);
        broadcastChannel?.removeEventListener('message', workerReadyCallback);
      }
      if (message.data.type === 'worker-unavailable') {
        globalThis.workerContext.error = Error(
          `${WORKER_NAME} is unavailable.`
        );
        resolve(false);
        console.error(globalThis.workerContext.error);
        broadcastChannel?.removeEventListener('message', workerReadyCallback);
      }
    };
    broadcastChannel.addEventListener('message', workerReadyCallback);
    port?.addEventListener('error', (e) => {
      console.error(e);
    });
    if (port instanceof MessagePort) {
      port.start();
    }
  });
  globalThis.workerContext.worker = worker;
  globalThis.workerContext.broadcastChannel = broadcastChannel;
  globalThis.workerContext.port = port;
  globalThis.runPythonAsync = runPythonAsync;
};

export const getWorkerContext = (): {
  worker: SharedWorker | Worker | undefined;
  broadcastChannel: BroadcastChannel | Worker | undefined;
  port: MessagePort | Worker | undefined;
  ready: boolean;
  error: boolean;
  readyPromise: Promise<boolean>;
} => {
  return globalThis.workerContext;
};

/*
 * The difference between useWorker and getWorkerContext is that useWorker is a
 * hook whose ready value updates.
 */
export const useWorker = () => {
  const workerContext = getWorkerContext();
  const [ready, setReady] = useState(workerContext?.ready);
  const [error, setError] = useState(workerContext?.error);
  useEffect(() => {
    workerContext?.readyPromise?.then((success) => {
      setReady(success);
      setError(!success);
    });
  }, []);
  return {
    ...workerContext,
    ready,
    error,
  };
};

export const workerFetch = async (
  path: string,
  { body, ...options }: any
): Promise<{ content: Uint8Array; status: number }> => {
  const id = uuidv4();
  const { port, readyPromise } = getWorkerContext();
  if (body instanceof FormData) {
    // Convert from FormData to json. This will not work with files (like team
    // photos) but we shouldn't allow team photos post hunt.
    body = Object.fromEntries(body);
  }
  await readyPromise;
  return new Promise((resolve) => {
    const onMessage = (e) => {
      if (e.data.type === 'fetch' && e.data.id === id) {
        port?.removeEventListener('message', onMessage);
        resolve(e.data.response);
      }
    };
    port?.addEventListener('message', onMessage);
    port?.postMessage({
      body,
      ...options,
      type: 'fetch',
      path: path,
      id,
    });
  });
};

/*
 * Test python functionality.
 */
export const runPython = (script, onSuccess, onError) => {
  const id = uuidv4();
  const { port } = getWorkerContext();
  const onMessage = (e) => {
    if (e.data.type === 'python' && e.data.id === id) {
      port?.removeEventListener('message', onMessage);
      if ('result' in e.data) {
        onSuccess(e.data.result);
      } else {
        onError(e.data.error);
      }
    }
  };
  port?.addEventListener('message', onMessage);
  port?.postMessage({
    type: 'python',
    id,
    script,
  });
};

export const runPythonAsync = (script) => {
  return new Promise((onSuccess, onError) => {
    runPython(script, onSuccess, onError);
  });
};
