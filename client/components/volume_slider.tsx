import React, { FunctionComponent, useEffect, useState } from 'react';
import Slider from 'react-rangeslider';
import { Howler } from 'howler';
import { VolumeOffIcon, VolumeUpIcon } from '@heroicons/react/solid';

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

  const toggleMute = () => {
    let value;
    if (volume === 0) {
      value = lastVolume || DEFAULT_VOLUME;
    } else {
      setLastVolume(volume);
      value = 0;
    }
    updateVolume(value);
  };

  const updateVolume = (value) => {
    setVolume(value);
    savedVolume.set(value);
    Howler.volume(value / 100);
  };

  useEffect(() => {
    // initialize volume
    Howler.volume(volume / 100);
  }, []);

  return (
    <>
      <div className="flex items-center justify-center m-1">
        {volume <= 0 ? (
          <VolumeOffIcon
            className="h-5 w-5 mr-2 volume-icon"
            onClick={toggleMute}
          />
        ) : (
          <VolumeUpIcon
            className="h-5 w-5 mr-2 volume-icon"
            onClick={toggleMute}
          />
        )}
        <Slider onChange={(value) => void updateVolume(value)} value={volume} />
      </div>

      <style jsx>{`
        button {
          background: transparent;
          border: none;
        }

        :global(.volume-icon) {
          cursor: pointer;
          color: var(--link);
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
          background-color: var(--muted);
          border-radius: 5px;
        }

        :global(.rangeslider-horizontal) :global(.rangeslider__fill) {
          position: absolute;
          background-color: var(--link);
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
          border: 3px solid var(--link);
          background-color: var(--background);
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
