import React, {
  FunctionComponent,
  RefObject,
  useEffect,
  useRef,
  useState,
} from 'react';
import dynamic from 'next/dynamic';
import $ from 'jquery';

const ReactTooltip = dynamic(() => import('react-tooltip'), {
  ssr: false,
});
import Twemoji from 'components/twemoji';
import { useLocalStorage } from 'utils/storage';

export const HIDDEN_CLASS = 'copy-only';
export const NO_COPY_CLASS = 'no-copy';

/**
 * Returns a list element with a hidden value that can be copy-pasted.
 * For some reason, li numbers don't get copied...
 * but we want to use it for accessibility reasons.
 */
export const Li = ({ value, children }) => (
  <li value={value}>
    <span className={HIDDEN_CLASS}>{value}. </span>
    {children}
  </li>
);

/** Anything rendered in this component will be hidden from view, but copied. */
export const HiddenText = ({ children }) => (
  <div className={HIDDEN_CLASS}>{children}</div>
);

interface MonospaceProps {
  as?: React.ElementType;
  children?: React.ReactNode;
}

/**
 * Component for rendering monospace via font (pre tags and class styling don't
 * work in Google Sheets).
 */
export const Monospace: FunctionComponent<MonospaceProps> = ({
  as = undefined,
  children,
}) => {
  const Component = as || 'span';
  return (
    <>
      <Component className={HIDDEN_CLASS} style={{ fontFamily: 'Roboto Mono' }}>
        {children}
      </Component>
      <Component className={`monospace ${NO_COPY_CLASS}`}>{children}</Component>
    </>
  );
};

/**
 * Empty inline element to reset text to normal which works with clipboard.
 */
export const Normal: FunctionComponent = ({ children }) => (
  <span
    style={{
      color: 'initial',
      fontWeight: 'initial',
      fontStyle: 'initial',
      fontSize: 'initial',
      fontFamily: 'initial',
      textAlign: 'initial',
    }}
  >
    {children}
  </span>
);

interface Props {
  text?: string | string[];
  textRef?: RefObject<HTMLElement>;
}

const CopyToClipboard: FunctionComponent<Props> = ({ text, textRef }) => {
  const copyRef = useRef<HTMLTextAreaElement>(null);
  const selfRef = useRef<HTMLButtonElement>(null);
  const [message, setMessage] = useState<string>('');
  const savedClickedClipboard = useLocalStorage<boolean>(
    'clicked-clipboard',
    false
  );
  const [clickedClipboard, setClickedClipboard] = useState<boolean>(true);

  useEffect(() => {
    // purposely animate a bit after page load
    setTimeout(() => setClickedClipboard(savedClickedClipboard.get()), 1000);
  }, []);

  // Use \r\n for Windows Notepad compatibility
  const copyableText = Array.isArray(text) ? text.join('\r\n') : text;

  const onClick = async () => {
    const copyableEl = textRef?.current;
    const selfEl = selfRef?.current;
    if ('navigator' in window && navigator.clipboard && copyableText) {
      // Modern navigator API, supports writing text.
      await navigator.clipboard.writeText(copyableText);
      setMessage('Copied to clipboard!');
    } else if (copyRef.current) {
      // Fallback if navigator API is not supported in older browsers, or if we need to copy actual HTML.
      if (copyableEl) {
        // Temporarily unhide any invisible elements.
        $(copyableEl).find(`.${HIDDEN_CLASS}`).show();
        $(copyableEl).find(`.${NO_COPY_CLASS}`).hide();
        window.getSelection()?.removeAllRanges();
        const range = document.createRange();
        range.selectNode(copyableEl);
        window.getSelection()?.addRange(range);
        if (selfEl) $(selfEl).hide();
        document.execCommand('copy');
        if (selfEl) $(selfEl).show();
        $(copyableEl).find(`.${NO_COPY_CLASS}`).show();
        $(copyableEl).find(`.${HIDDEN_CLASS}`).hide();
      } else {
        // Temporarily show the textarea so it can be copied.
        copyRef.current.style.display = 'block';
        copyRef.current.select();
        document.execCommand('copy');
        copyRef.current.style.display = 'none';
      }
      window.getSelection()?.removeAllRanges();
      setMessage('Copied to clipboard!');
    } else {
      setMessage(
        'Failed to copy to clipboard! Please contact us if you see this error.'
      );
      return;
    }
    setTimeout(() => void setMessage(''), 3000);
    setClickedClipboard(true);
    savedClickedClipboard.set(true);
  };

  return (
    <>
      <textarea ref={copyRef} value={copyableText} readOnly />

      <button
        ref={selfRef}
        data-tip=""
        data-for="tooltip"
        className={message || !clickedClipboard ? 'expanded' : ''}
        onClick={onClick}
      >
        <Twemoji emoji="📋" options={{ className: 'clip-twemoji' }}>
          {message || 'Copy to clipboard'}
        </Twemoji>
      </button>
      <ReactTooltip
        id="tooltip"
        effect="solid"
        multiline
        offset={clickedClipboard ? { left: 64 } : undefined}
        getContent={() =>
          message || (
            <span>
              Click to copy puzzle content
              <br /> for ease of pasting into
              <br /> Google Sheets or Excel.
            </span>
          )
        }
      />

      <style jsx>{`
        textarea {
          /* Hide the text to copy. */
          display: none;
        }

        button {
          border-radius: 20px;
          font-size: 20px;
          line-height: 48px;
          height: 48px;
          padding: 0 12px;
          position: fixed;
          bottom: 32px;
          right: 32px;
          overflow: hidden;
          max-width: 480px;
          transition: max-width 300ms ease-in-out;
          word-break: break-all;
        }

        :global(.clip-twemoji) {
          display: inline-block;
          height: 1em;
          width: 1em;
          vertical-align: middle;
        }

        button:not(:hover):not(.expanded) {
          max-width: 48px;
        }

        @media (max-width: 550px) {
          button {
            display: none;
          }
        }
      `}</style>
    </>
  );
};

export default CopyToClipboard;
