import ReactDOM from 'react-dom';
import ReactTwemoji from 'react-twemoji';
import { HIDDEN_CLASS, NO_COPY_CLASS } from 'components/copy';
import { forwardRef, useEffect, useRef, useState } from 'react';

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
}

/**
 * Twemoji are used to render consistent emojis cross-browser, as you might
 * see on Discord. This ensures that puzzle content is consistent regardless of
 * the browser. See https://twemoji.twitter.com/ for more details.
 *
 * This is a wrapper around react-twemoji which uses images to render emoji
 * on the page, but ensures that copy-to-clipboard copies the actual unicode.
 */
const Twemoji = forwardRef<HTMLImageElement, TwemojiProps>(
  ({ emoji = undefined, options = undefined, children, ...props }, ref) => (
    <>
      <ReactTwemoji
        className={NO_COPY_CLASS}
        ref={ref}
        options={options}
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

export const CopyableTwemoji = ({
  emoji,
  options = {} as TwemojiOptions,
  ...props
}) => {
  const [absSrc, setAbsSrc] = useState<string>('');
  const ref = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (ref.current) {
      // Because react-twemoji doesn't forwardRef, we have to grab the DOM node
      // manually.
      const rootEl = ReactDOM.findDOMNode(ref.current);
      if (rootEl?.firstChild && 'src' in rootEl.firstChild) {
        setAbsSrc((rootEl.firstChild as HTMLImageElement).src);
      }
    }
  }, []);

  return (
    <>
      <Twemoji
        ref={ref}
        emoji={emoji}
        options={{
          ...(options || {}),
          // Don't render the Twemoji when copy-pasting
          className: `${NO_COPY_CLASS} emoji`,
        }}
        {...props}
      />
      {/* Render image formula with Twemoji url for sheets. */}
      {(absSrc || options.copyUnicodeEmoji) && (
        <span className={HIDDEN_CLASS}>
          {options.copyUnicodeEmoji ? emoji : `=IMAGE("${absSrc}")`}
        </span>
      )}
    </>
  );
};

export default Twemoji;
