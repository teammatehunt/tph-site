import React, { FunctionComponent, useEffect, useState } from 'react';
import Slider from 'react-rangeslider';
import { Howler } from 'howler';
import { Volume, Volume1, Volume2, VolumeX } from 'react-feather';

import { TICK_SOUND_EFFECTS } from 'utils/timer';
import { useLocalStorage } from 'utils/storage';
import { useSounds } from 'utils/assets';

export const VOLUME_KEY = 'volume';
export const DEFAULT_VOLUME = 50;

const VolumeSlider: FunctionComponent<{}> = () => {
  const savedVolume = useLocalStorage(VOLUME_KEY, DEFAULT_VOLUME);
  const [volume, setVolume] = useState<number>(
    savedVolume.get() ?? DEFAULT_VOLUME
  );
  const [lastVolume, setLastVolume] = useState<number>(volume);

  const { isLoading, sounds } = useSounds('', [TICK_SOUND_EFFECTS]);

  const toggleMute = () => {
    let value;
    if (volume === 0) {
      value = lastVolume || DEFAULT_VOLUME;
    } else {
      setLastVolume(volume);
      value = 0;
    }
    updateVolume(value);
    endUpdateVolume();
  };

  const updateVolume = (value) => {
    setVolume(value);
    savedVolume.set(value);
    Howler.volume(value / 100);
  };

  const endUpdateVolume = () => {
    if (!isLoading) {
      sounds['public/tick'].play('tick');
    }
  };

  useEffect(() => {
    // initialize volume
    Howler.volume(volume / 100);
  }, []);

  return (
    <>
      <div className="flex-center-vert">
        <button onClick={toggleMute}>
          {volume <= 0 ? (
            <VolumeX />
          ) : volume < 20 ? (
            <Volume />
          ) : volume < 60 ? (
            <Volume1 />
          ) : (
            <Volume2 />
          )}
        </button>
        <Slider
          onChange={(value) => void updateVolume(value)}
          onChangeComplete={() => endUpdateVolume()}
          value={volume}
        />
      </div>

      <style jsx>{`
        button {
          background: transparent;
          border: none;
        }

        button :global(svg) {
          display: block;
          margin: auto;
          width: 32px;
          height: 100%;
        }

        :global(.rangeslider) {
          position: relative;
          width: 250px;
          height: 10px;
          background-color: gray;
          border-radius: 5px;
        }

        :global(.rangeslider-horizontal) :global(.rangeslider__fill) {
          position: absolute;
          background-color: #3cc;
          height: 10px;
          border-radius: 5px;
        }

        :global(.rangeslider-horizontal) :global(.rangeslider__handle) {
          position: absolute;
          width: 20px;
          height: 20px;
          top: 50%;
          transform: translate(-50%, -50%);
          border-radius: 50%;
          border: 3px solid dimgray;
          background-color: silver;
          cursor: pointer;
        }

        :global(.rangeslider-horizontal) :global(.rangeslider__handle-tooltip) {
          display: none;
        }
      `}</style>
    </>
  );
};

export default VolumeSlider;
