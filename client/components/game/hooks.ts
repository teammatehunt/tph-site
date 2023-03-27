import { useMemo } from 'react';
import {
  BaseTexture,
  ImageResource,
  Texture,
  VideoResource,
} from 'pixi.js-legacy';

export const useTexture = (imageUrl?: string): Texture | undefined => {
  return useMemo(() => {
    if (typeof window === 'undefined' || !imageUrl) {
      return undefined;
    }

    let baseTexture: BaseTexture;
    if (imageUrl.endsWith('mp4') || imageUrl.endsWith('webm')) {
      const video = document.createElement('video');
      video.loop = true;
      video.muted = true;
      video.autoplay = true;
      video.crossOrigin = 'anonymous';
      video.src = imageUrl;
      const videoResource = new VideoResource(video, {
        updateFPS: 30, // limit FPS for performance
        crossorigin: true, // allow crossorigin "anonymous" to access CDN in canvas
      });
      baseTexture = new BaseTexture(videoResource);
    } else {
      const imageResource = new ImageResource(imageUrl, {
        crossorigin: true, // allow crossorigin "anonymous" to access CDN in canvas
      });
      baseTexture = new BaseTexture(imageResource);
    }
    return Texture.from(baseTexture);
  }, [imageUrl]);
};
