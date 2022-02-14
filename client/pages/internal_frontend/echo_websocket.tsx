import Head from 'next/head';
import React, { FC, useEffect, useCallback, useRef } from 'react';
import { useEventWebSocket } from 'utils/fetch';

const Echo: FC = () => {
  const dataHandler = useCallback((data) => {
    console.log(data);
  }, []);
  useEventWebSocket({
    onJson: dataHandler,
    // key: 'submission', // can filter for events with a certain key
  });
  return (
    <>
      <Head>
        <title>Echo Websocket</title>
      </Head>
      <p>Check the console for team site-wide events (must be logged in).</p>
    </>
  );
};

export default Echo;
