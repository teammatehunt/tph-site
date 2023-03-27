import { AnimatedSprite as PixiAnimatedSprite, Texture } from 'pixi.js-legacy';
import { applyDefaultProps, PixiComponent } from '@inlet/react-pixi/legacy';

const makeTexture = (textures) => {
  return textures.map((texture) =>
    texture instanceof Texture ? texture : texture?.texture
  );
};

/**
 * Mostly copied from https://github.com/inlet/react-pixi/blob/master/src/components/AnimatedSprite.js
 * but with some bugfixes
 */
const AnimatedSprite = {
  create: ({
    textures,
    images = undefined,
    isPlaying = true,
    initialFrame = undefined,
    animationSpeed = 1,
    x,
    y,
    width,
    height,
  }) => {
    const animatedSprite = images
      ? PixiAnimatedSprite.fromImages(images)
      : new PixiAnimatedSprite(makeTexture(textures));
    animatedSprite[isPlaying ? 'gotoAndPlay' : 'gotoAndStop'](
      initialFrame || 0
    );
    animatedSprite.animationSpeed = animationSpeed;
    animatedSprite.x = x;
    animatedSprite.y = y;
    animatedSprite.width = width;
    animatedSprite.height = height;

    return animatedSprite;
  },

  applyProps: (instance, oldProps, newProps) => {
    const { textures, isPlaying, initialFrame, ...props } = newProps;

    applyDefaultProps(instance, oldProps, props);

    if (textures && oldProps['textures'] !== textures) {
      instance.textures = makeTexture(textures);
    }

    if (
      /* always animate if the sprite is playing */
      isPlaying ||
      isPlaying !== oldProps.isPlaying ||
      initialFrame !== oldProps.initialFrame
    ) {
      const frame =
        typeof initialFrame === 'number'
          ? initialFrame
          : instance.currentFrame || 0;
      instance[isPlaying ? 'gotoAndPlay' : 'gotoAndStop'](frame);
    }
  },
};

export default PixiComponent('CustomAnimatedSprite', AnimatedSprite);
