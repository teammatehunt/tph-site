import React, { forwardRef } from 'react';
import ReactTwemoji from 'react-twemoji';
import { HIDDEN_CLASS, NO_COPY_CLASS } from 'components/copy';
import cx from 'classnames';

interface TwemojiOptions {
  size?: number | string;
  className?: string;
  // Set this to true for copy to clipboard to copy the actual emoji character
  // instead of linking to the twemoji image.
  copyUnicodeEmoji?: boolean;
}

interface TwemojiProps {
  emoji?: React.ReactFragment;
  options?: TwemojiOptions;
  tag?: string;
  children?: React.ReactNode;
  className?: string;
}

/**
 * Twemoji are used to render consistent emojis cross-browser, as you might
 * see on Discord. This ensures that puzzle content is consistent regardless of
 * the browser. See https://twemoji.twitter.com/ for more details.
 *
 * By default, copy-to-clipboard copies the image, not the unicode.
 * For the latter, use <CopyableTwemoji> with the copyUnicodeEmoji option enabled.
 */
const Twemoji = forwardRef<HTMLImageElement, TwemojiProps>(
  ({ emoji = undefined, options = undefined, children, ...props }, ref) => (
    <>
      <ReactTwemoji
        ref={ref}
        options={{
          base: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/',
          ...options,
        }}
        {...props}
      >
        {emoji}
        {children && <span> {children}</span>}
      </ReactTwemoji>

      <style jsx>{`
        :global(.emoji) {
          height: 1em;
          width: 1em;
          vertical-align: middle;
        }
        span {
          vertical-align: middle;
        }
      `}</style>
    </>
  )
);

export const CopyableTwemoji: React.FC<TwemojiProps> = ({
  emoji,
  className,
  options = {} as TwemojiOptions,
  ...props
}) => {
  return (
    <>
      <Twemoji
        emoji={emoji}
        options={options}
        className={cx(className, {
          // Don't render the text when copy-pasting if unicode enabled
          [NO_COPY_CLASS]: options.copyUnicodeEmoji,
        })}
        {...props}
      />
      {/* Render unicode emoji if enabled */}
      {options.copyUnicodeEmoji && (
        <span className={HIDDEN_CLASS}>{emoji}</span>
      )}
    </>
  );
};

export const InlineTwemoji: React.FC<{
  emoji?: string;
  copyImage?: boolean;
}> = ({ emoji, copyImage = false, children }) => (
  <CopyableTwemoji
    tag="span"
    emoji={emoji ?? children ?? undefined}
    options={{ className: 'emoji inline-block', copyUnicodeEmoji: !copyImage }}
  />
);

export default Twemoji;
