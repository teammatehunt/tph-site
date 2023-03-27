import { useEffect, useState } from 'react';
import { Howl } from 'howler';
import allSettled from 'promise.allsettled';

interface ImageData {
  isLoading: boolean;
  images: Record<string, HTMLImageElement>;
}

interface SoundData {
  isLoading: boolean;
  sounds: Record<string, Howl>;
}

allSettled.shim(); // polyfill for older versions of firefox

/**
 * Hook that loads images lazily and returns a boolean for whether they have loaded.
 */
export const useImages = (prefix: string, imageUrls: string[]): ImageData => {
  const [isLoading, setLoading] = useState<boolean>(true);
  const [images, setImages] = useState<Record<string, HTMLImageElement>>({});

  const loadImages = async () => {
    const imagePromises = await Promise.allSettled(
      imageUrls.map((url) => {
        // Load the image url chunk.
        const src = require(`assets/${prefix}${url}.png`).default;
        return new Promise((resolve, reject) => {
          const image = new Image();
          // Set the src on a new image element, and resolve when loaded.
          image.onload = () => resolve(image);
          image.onerror = () => reject();
          image.src = src;
        });
      })
    );
    const newImages = {};
    imagePromises.forEach((promise, i) => {
      // TODO(ivan): Handle the case if some images failed to load.
      if (promise.status === 'fulfilled') {
        newImages[imageUrls[i]] = promise.value;
      } else {
        console.log('Failed to load image!');
      }
    });
    setImages(newImages);
    setLoading(false);
  };

  useEffect(() => void loadImages(), imageUrls);

  return {
    isLoading,
    images,
  };
};

export interface Sprite {
  src: string;
  sprite: Record<string, [number, number] | [number, number, boolean]>;
  onend?: () => void;
}

export const MAIN_SOUND_EFFECTS: Sprite = {
  src: 'public/mainsfx',
  sprite: {
    win: [0, 2200],
    loss: [2560, 3500],
    select: [7497, 153],
    switchScreen: [7650, 69],
    flip: [7719, 689],
  },
};

/**
 * Hook that loads sound effects lazily and returns a boolean for whether they have loaded.
 */
export const useSounds = (
  prefix: string,
  soundUrls: (string | Sprite)[]
): SoundData => {
  const [isLoading, setLoading] = useState<boolean>(true);
  const [sounds, setSounds] = useState<Record<string, () => void>>({});

  const getSrc = (src: string) => [
    require(`assets/${prefix}${src}.mp3`).default,
  ];

  const loadSounds = async () => {
    const soundPromises = await Promise.allSettled(
      soundUrls.map(
        (urlOrSprite) =>
          new Promise((resolve, reject) => {
            const howlArgs =
              typeof urlOrSprite === 'string'
                ? {
                    src: getSrc(urlOrSprite),
                  }
                : {
                    ...urlOrSprite,
                    src: getSrc(urlOrSprite.src),
                  };

            new Howl({
              ...howlArgs,
              onload() {
                resolve(this);
              },
              onloaderror(soundId, error) {
                reject(error);
              },
              onfade() {
                this.stop();
                this.volume(1);
              },
            });
          })
      )
    );
    const newSounds = {};
    soundPromises.forEach((promise, i) => {
      // TODO(ivan): Handle the case if some sounds failed to load.
      if (promise.status === 'fulfilled') {
        const id: string =
          typeof soundUrls[i] === 'string'
            ? (soundUrls[i] as string)
            : (soundUrls[i] as Sprite).src;
        newSounds[id] = promise.value;
      } else {
        console.log('failed to load sound!');
      }
    });
    setSounds(newSounds);
    setLoading(false);
  };

  useEffect(() => void loadSounds(), soundUrls);

  return {
    isLoading,
    sounds,
  };
};
