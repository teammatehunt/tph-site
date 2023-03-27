/**
 * **Update Jan 18 2022.**
 * Google Sheets changed how they do images, so the image copying code needs to
 * be redone. If you're fixing this, I recommend tools like InsideClipboard on
 * Windows or Clipboard Viewer on OSX. Then set up a Google Sheet with images in
 * cells, do some copy and pasting, and see what data format Sheets uses to
 * copy images.
 *
 * From a very cursory investigation, it appears to now use `img` tags with a
 * base64 encoded image. This should be possible to replicate and so restore
 * copy-to-clipboard support for images.
 */

/**
 * Helper to implement puzzle copying by setting inline styles on the copied elements.
 * Adapted from GPH and Palindrome's copyjack to work in React.
 * https://github.com/Palindrome-Puzzles/2022-hunt/blob/main/hunt/app/static/core/copyjack.js
 *
 * Behaviour:
 *  - Image copying! This tries its best to copy images so that they are
 *    displayed when pasted into spreadsheets. In general, images work when
 *    pasted into Google Sheets, and are replaced with descriptive text plus a
 *    link when pasted into Excel.
 *     - Images are automatically skipped if they (or an ancestor) are marked as
 *       no-copy or as ARIA hidden.
 *     - The descriptive text is used all the time for Excel, and in certain
 *       fallback cases for Sheets. It will be one of:
 *         - A link to the image with text "See original puzzle for image" if the
 *           image has no alt text.
 *         - A link to the image with text "Image: <alt text>" if the image has
 *           alt text.
 *     - Inline images (where multiple images are shown on one row in the puzzle)
 *       are each given their own row in the copied content. This is necessary
 *       for embedding images in Sheets, or making links work.
 *     - If an image is within a `td` or `th`, image embedding/linking will only
 *       work if the image is the only thing within the cell.
 *     - Background images will not be copied.
 *     - If developing locally, the images can't be fetched from localhost, so
 *       we fall back to the Excel behaviour.
 *     - If the image is already within a different link, we don't change that
 *       link.
 *  - It ignores the font-family and font-size as it is unlikely the paste target has our hunt font available.
 *  - If a paragraph contains linked text, the whole paragraph will become a link.
 *  - If a table cell contains linked text, the whole paragraph will become a
 *    link. (This needs a hacky workaround for Sheets, so may be brittle.)
 *  - When copying tables, only borders on `th` and `td` elements will have any
 *    effect. Make sure borders are set on those instead of relying on styles for
 *    the `table` or `tr` elements.
 *  - Copied borders can only be black or gray. If not one of these colors,
 *    borders get copied as gray.
 *  - If there is a border on every side, then due to browser weirdness, each
 *    side of the cell must have the same border (at least when copying into
 *    Google Sheets). This makes certain layouts such as having a thicker
 *    outside border challenging.
 *
 * Pass in a ref for the root container for all puzzle content.
 *  - Everything within this will be copied by default.
 *  - `HIDDEN_CLASS` contains content that should be included in the clipboard
 *    version only.
 *  - `NO_COPY_CLASS` contains content that should be included in the web version only.
 *
 * Puzzle settings can optionally be added to this component to control
 * copying globally, or to a DOM node to control copying for that element.
 * As an example, you could use the following to disable adding inline styles
 * globally or for a single element.
 *   `<Copy skipInlineStyles />`
 *   `<div src="..." alt="..." data-skip-inline-styles="true">`
 *
 * Available settings are:
 *  - `data-skip-inline-styles`: Don't inject inline styles. Use this is the
 *    styling is mostly decorative, and would be obtrusive in the copied content.
 *  - `data-skip-inline-borders`: Don't inject inline borders. Use this when the
 *    border styling is mostly decorative (say subtle gray borders).
 *  - `data-skip-table-breaks`: Don't inject a br after tables (and hr) elements.
 *  - `data-copy-only-styles`: Style string to inject when copying the element.
 *  - `data-copy-input-value`: Use the value of an input when copying.
 *
 * The global CSS should have the following styles to support copy-jacking.
 * ```
 * .copy-only {
 *   display: none;
 * }
 * ```
 *
 * *Warning*: If the puzzle content changes dynamically, newly added content may
 * be copied differently to original content.
 */

import React, {
  FunctionComponent,
  RefObject,
  useEffect,
  useRef,
  useState,
} from 'react';
import cx from 'classnames';
import dynamic from 'next/dynamic';

const ReactTooltip = dynamic(() => import('react-tooltip'), {
  ssr: false,
});

import Twemoji from 'components/twemoji';
import { useLocalStorage } from 'utils/storage';

export const HIDDEN_CLASS = 'copy-only';
export const HTML_COPY_ONLY_CLASS = 'copy-html-only';
export const NO_COPY_CLASS = 'no-copy';

// Constants for Google Sheets defaults
const DEFAULT_FONT_FAMILY = 'Arial, sans-serif';
const MONOSPACE_FONT_FAMILY = 'Consolas, monospace';
const DEFAULT_FONT_SIZE = '13px';

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
  return <Component className="font-mono">{children}</Component>;
};

export interface CopyConfig {
  skipInlineBorders?: boolean;
  skipInlineStyles?: boolean;
  skipTableBreaks?: boolean;
  preserveStyles?: boolean;
}

interface Props {
  textRef: RefObject<HTMLElement>;
  selfRef?: RefObject<HTMLButtonElement>;
  hidden?: boolean;
  preload?: boolean;
  config?: CopyConfig;
}

const CopyToClipboard: FunctionComponent<Props> = ({
  textRef,
  selfRef = undefined,
  hidden = false,
  preload = false,
  config = {},
}) => {
  if (!selfRef) {
    selfRef = useRef<HTMLButtonElement>(null);
  }
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

  useEffect(() => {
    if (preload) {
      const copyableEl = textRef.current!;
      // For very large pages, we'll want to eagerly copyjack so that the
      // copyable elements are cached and speed up the copy action itself.
      maybeCopyJack(copyableEl, config);
    }
  }, [preload]);

  const onClick = async () => {
    const copyableEl = textRef.current!;
    copyContents(copyableEl, config);
    setMessage('Copied to clipboard!');
    setTimeout(() => void setMessage(''), 3000);
    setClickedClipboard(true);
    savedClickedClipboard.set(true);
  };

  useEffect(() => {
    // Intercept copies that were due to clicking clipboardButton, and assemble
    // the copied HTML.
    //
    // Note: this is a little awkward to work around an issue in Chrome with
    // Google Sheets.
    //
    // A simpler solution that works in Firefox is to remove this copy handler,
    // and do the following in `copyContents`.
    //   ```
    //   // Toggle .copy-only and .no-copy content.
    //   rootElement.classList.add("copying");
    //   selection.removeAllRanges();
    //
    //   // Select and copy the puzzle.
    //   const range = document.createRange();
    //   range.selectNode(rootElement);
    //   selection.addRange(range);
    //   document.execCommand("copy");
    //
    //   // Restore initial state.
    //   selection.removeAllRanges();
    //   rootElement.classList.remove("copying");
    //   ''`
    //
    // In Chrome, this breaks because execCommand injects default text styles on
    // the `<google-sheets-html-origin>` tag, and then Sheets doesn't show images
    // any more.
    //
    // Instead, we assemble our own versions of the plain text and HTML clipboard
    // data. The main downside is it is more inefficient, and the plain text
    // version is less sophisticated.
    document.addEventListener('copy', (event) => {
      const puzzleElement = textRef.current;
      if (!puzzleElement || !puzzleElement.dataset.interceptNextCopy) {
        return;
      }
      delete puzzleElement.dataset.interceptNextCopy;

      const cloned = recursiveClone(
        puzzleElement,
        (node) => {
          if (node.nodeType !== Node.ELEMENT_NODE) return true;
          if (node.tagName.toLowerCase() === 'script') return false;
          if (node.tagName.toLowerCase() === 'style') return false;
          if (node.tagName.toLowerCase() === 'link') return false;
          if (node.tagName.toLowerCase() === 'math') return false;
          return (
            !node.classList.contains(NO_COPY_CLASS) &&
            !node.classList.contains('hidden') &&
            !node.classList.contains('errata')
          );
        },
        (node) => {
          if (node.nodeType !== Node.ELEMENT_NODE) return;

          if (node.dataset.copyOnlyStyles) {
            node.setAttribute(
              'style',
              `${node.style.cssText} ${node.dataset.copyOnlyStyles}`
            );
            delete node.dataset.copyOnlyStyles;
          }
          // Make links absolute.
          if (node instanceof HTMLAnchorElement && node.href) {
            node.href = makeHrefAbsolute(node.href);
          }
          // Set the font family to a websafe default if it matches our default hunt font.
          // In this case, the font family carries no information, and as the paste target
          // probably won't have the font available, use something it can handle.
          if (node.style.fontFamily.startsWith('"DM Mono"')) {
            node.style.fontFamily = MONOSPACE_FONT_FAMILY;
          } else {
            node.style.fontFamily = DEFAULT_FONT_FAMILY;
          }
          node.style.fontSize = DEFAULT_FONT_SIZE;
          // Adjust font weight for headings, which otherwise lose their font size.
          if (
            ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(node.tagName) &&
            node.style.fontWeight === '400'
          ) {
            node.style.fontWeight = '700';
          }
          // Coerce start -> left as otherwise Sheets treats it as right-aligned sometimes.
          if (node.style.textAlign && node.style.textAlign === 'start') {
            node.style.textAlign = 'left';
          }
          // Copy values out of inputs. Do this lazily on copy as inputs can change.
          if (node instanceof HTMLInputElement && node.dataset.copyInputValue) {
            return document.createTextNode(node.value);
          }
        }
      );

      const plainTextVersion = trimPlainText(cloned.innerText);
      event.clipboardData?.setData('text/plain', plainTextVersion);
      event.clipboardData?.setData('text/html', cloned.innerHTML);
      event.preventDefault();
    });
  });

  return (
    <>
      <button
        ref={selfRef}
        data-tip=""
        data-for="tooltip"
        data-tooltip-place="top"
        className="clipboard"
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

        .clipboard {
          height: 64px;
          font-size: 20px;
          padding: 0;
          position: sticky;
          bottom: 2rem;
          left: 100%;
          overflow: hidden;
          width: 64px;
          margin-right: -80px;
          word-break: break-all;
        }

        @media (max-width: 550px), print {
          .clipboard {
            display: none;
          }
        }
      `}</style>
    </>
  );
};

export default CopyToClipboard;

function maybeCopyJack(rootElement: HTMLElement, config: CopyConfig = {}) {
  const selection = window.getSelection();
  if (!selection) return;

  // Modify the puzzle content (once), so that it is amenable to copying.
  if (!rootElement.dataset.copyjacked) {
    copyJack(rootElement, config);
    rootElement.dataset.copyjacked = 'true';
  }
}

function copyContents(rootElement: HTMLElement, config: CopyConfig = {}) {
  const selection = window.getSelection();
  if (!selection) return;

  maybeCopyJack(rootElement, config);

  // Defer to the copy handler to assemble the copied content. Ideally, we'd
  // select rootElement and let the browser assemble the copied content, but it
  // breaks Sheets interop in Chrome. See the comment for the copy handler for
  // info.
  rootElement.dataset.interceptNextCopy = 'true';

  // Select and copy the puzzle.
  // This is needed for Safari, which won't let us execute 'copy' unless we have
  // selected something.
  selection.removeAllRanges();
  const range = document.createRange();
  range.selectNode(rootElement);
  selection.addRange(range);

  document.execCommand('copy');

  // Restore initial state.
  selection.removeAllRanges();
}

/**
 * One-time processing for puzzle content in `rootElement` to make it amenable to copying.
 */
function copyJack(rootElement: HTMLElement, config: CopyConfig = {}) {
  const getSetting = (element: Element, setting: keyof CopyConfig) =>
    (element as HTMLElement).dataset[setting] ?? config[setting];

  // Inject <google-sheets-html-origin> element so Google Sheets interop works.
  const sheetsInteropElement = document.createElement(
    'google-sheets-html-origin'
  );
  sheetsInteropElement.classList.add(HIDDEN_CLASS); // Hide to avoid messing up flex
  rootElement.insertBefore(
    sheetsInteropElement,
    rootElement.firstElementChild?.nextSibling ?? null
  );

  // Ensure everything with aria-hidden="true" is not copied, unless it's within
  // some copy-only content.
  for (const element of document.querySelectorAll('[aria-hidden="true"]')) {
    if (!element.closest(`.${HIDDEN_CLASS}`)) {
      element.classList.add(NO_COPY_CLASS);
    }
  }

  // Change blank tags to pre, and handle boxed blanks.
  for (const element of rootElement.querySelectorAll('.blanks')) {
    element.classList.add(NO_COPY_CLASS);

    const copiedElement = document.createElement('pre');
    copiedElement.classList.add(HIDDEN_CLASS);

    for (const child of element.childNodes) {
      copiedElement.appendChild(child.cloneNode(true));
    }

    for (const boxedElement of copiedElement.querySelectorAll('.boxed')) {
      boxedElement.innerHTML = '[' + boxedElement.innerHTML + ']';
    }
    element.parentNode?.insertBefore(copiedElement, element.nextSibling);
    copyJackInlineStyles(copiedElement, config);
  }

  // Change numbered blank tags to pre, change <u>x</u> to _(x), and inject some spaces.
  for (const element of rootElement.querySelectorAll('.numbered-blanks')) {
    element.classList.add(NO_COPY_CLASS);

    const copiedElement = document.createElement('pre');
    copiedElement.classList.add(HIDDEN_CLASS);

    // Skip text nodes, and only keep element children.
    for (const child of element.children) {
      const isWordBreak =
        child.nodeType === Node.ELEMENT_NODE &&
        child.classList.contains('word-break');
      copiedElement.appendChild(
        isWordBreak ? document.createTextNode('   ') : child.cloneNode(true)
      );
    }

    for (const underlineElement of copiedElement.querySelectorAll('u')) {
      // Prevent underlines showing up in the copied content, as they won't be
      // spaced out nicely. Also inject a space after the underlined element.
      underlineElement.style.textDecoration = 'none';
      underlineElement.innerHTML = underlineElement.innerHTML
        ? '_(' + underlineElement.innerHTML + ') '
        : '_ ';
    }
    element.parentNode?.insertBefore(copiedElement, element.nextSibling);
    copyJackInlineStyles(copiedElement, config);
  }

  // Change .blank-word tags to some underscores.
  for (const element of rootElement.querySelectorAll('.blank-word')) {
    const copiedElement = element.cloneNode(true) as HTMLElement;
    copiedElement.classList.add(HIDDEN_CLASS);
    copiedElement.innerText = '_____';
    element.parentNode?.insertBefore(copiedElement, element.nextSibling);

    element.classList.add(NO_COPY_CLASS);
  }

  // Replace images with a link to the image, unless it is decorational.
  for (const element of rootElement.querySelectorAll('img')) {
    copyJackImage(element);
  }

  // Insert numbers and letters for ordered lists.
  for (const list of rootElement.querySelectorAll('ol')) {
    if (list.classList.contains('no-bullets')) {
      continue;
    }
    const listStyleType = window
      .getComputedStyle(list)
      .getPropertyValue('list-style-type');
    let lastIndex = 0;
    for (const item of list.querySelectorAll('li')) {
      var displayedIndex = '';
      if (!item.classList.contains('no-index')) {
        const index = item.value || lastIndex + 1;
        displayedIndex = resolveListIndex(index, listStyleType);
        lastIndex = index;
      }

      const span = document.createElement('span');
      span.classList.add(HIDDEN_CLASS);
      span.setAttribute('data-skip-inline-styles', 'true');
      span.innerText = displayedIndex;
      item.insertBefore(span, item.firstChild);
    }
  }

  // Wrap .italicized.preserve-on-copy with underscores.
  for (const element of rootElement.querySelectorAll(
    '.italicized.preserve-on-copy'
  )) {
    const prefix = document.createElement('span');
    prefix.classList.add(HIDDEN_CLASS);
    prefix.innerText = '_';

    const suffix = prefix.cloneNode(true);
    element.insertBefore(prefix, element.firstChild);
    element.appendChild(suffix);
  }

  // Insert copy-only versions of a caption before the table, as google sheets
  // does not like them.
  for (const element of rootElement.querySelectorAll('caption')) {
    if (element.classList.contains(NO_COPY_CLASS)) continue;
    if (element.classList.contains('sr-only')) continue;
    const parentTable = element.closest('table');

    const copyableCaption = document.createElement('div');
    copyableCaption.innerHTML = element.innerHTML;
    copyableCaption.classList.toggle(HIDDEN_CLASS, true);
    element.classList.toggle(NO_COPY_CLASS, true);

    for (const key in element.dataset) {
      copyableCaption.dataset[key] = element.dataset[key];
    }

    parentTable?.parentNode?.insertBefore(copyableCaption, parentTable);
  }

  // Add inline styles to content elements and follow them with a reset span.
  for (const tag of [
    'span',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'div',
    'p',
    'pre',
    'code',
    'ul',
    'ol',
    'i',
    'u',
    'b',
    'strong',
    'em',
    'sub',
    'sup',
    'a',
  ]) {
    for (const element of rootElement.querySelectorAll(tag)) {
      if (element.closest(NO_COPY_CLASS)) continue;
      if (
        findAncestor(element, shouldBeSkipped) ||
        getSetting(element, 'skipInlineStyles')
      )
        continue;

      copyJackInlineStyles(element as HTMLElement, config);
      maybeAppendResetSpan(element);
    }
  }

  // Add inline styles and borders to table cells.
  for (const tag of ['th', 'td']) {
    for (const element of rootElement.querySelectorAll(tag)) {
      if (findAncestor(element, shouldBeSkipped)) {
        continue;
      }
      if (!getSetting(element, 'skipInlineBorders')) {
        copyJackInlineBorders(element);
      }
      if (!getSetting(element, 'skipInlineStyles')) {
        copyJackInlineStyles(
          element as HTMLElement,
          config,
          ['text-align'] // Keep text-align inside table cells
        );
      }

      // Fix table cells that contain links for Google Sheets.
      copyJackTableLinks(element);
    }
  }

  // Crossword and grid copying.
  // Add a blank line after each child of .prefer-2-col.
  for (const container of rootElement.querySelectorAll('.prefer-2-col')) {
    for (const child of Array.from(container.children)) {
      const br = document.createElement('br');
      br.classList.add(HIDDEN_CLASS);
      container.insertBefore(br, child);
    }
  }

  // Move the clues to the bottom in a .clued-item-container.
  for (const container of rootElement.querySelectorAll(
    '.clued-item-container'
  )) {
    for (const clues of container.querySelectorAll('.clues')) {
      if (clues.parentNode !== container) continue;

      const copied = recursiveClone(clues);
      copied.classList.add(HIDDEN_CLASS);
      clues.classList.add(NO_COPY_CLASS);

      container.appendChild(copied);
    }
  }

  // If a crossword grid contains clues, make two copies.
  for (const crossword of rootElement.querySelectorAll('table.crossword')) {
    if (!crossword.querySelectorAll('.clue').length) continue;

    const copied = recursiveClone(
      crossword,
      (node) =>
        node.nodeType !== Node.ELEMENT_NODE || !node.classList.contains('clue')
    );
    copied.classList.add(HIDDEN_CLASS);
    crossword.parentNode?.insertBefore(copied, crossword.nextSibling);
  }

  // Append a . and space to each crossword clue.
  for (const clue of rootElement.querySelectorAll('table.crossword .clue')) {
    const hasOtherText =
      (clue.parentNode as HTMLElement).innerText.trim() !==
      (clue as HTMLElement).innerText.trim();
    const span = document.createElement('span');
    span.classList.add(HIDDEN_CLASS);
    span.innerText = hasOtherText ? '. ' : '';
    clue.appendChild(span);
  }

  // Fix top borders of barred grids. We remove them when copying to allow
  // different border widths when pasting to Sheets.
  for (const barredGrid of rootElement.querySelectorAll('table.barred.grid')) {
    const firstRow = barredGrid.querySelector('tr');
    if (!firstRow) continue;
    const numberOfColumns = firstRow.querySelectorAll('td, th').length;

    const fakeRow = document.createElement('tr');
    fakeRow.classList.add(HIDDEN_CLASS);
    for (let i = 0; i < numberOfColumns; i++) {
      const fakeCell = document.createElement('td');
      fakeCell.classList.add('no-border');
      fakeRow.appendChild(fakeCell);
    }
    firstRow.parentNode?.insertBefore(fakeRow, firstRow);

    // Iterate through each row and add a border-bottom to the row above.
    const rows = Array.from(
      barredGrid.querySelectorAll('tr')
    ) as HTMLTableRowElement[];
    let lastRowCells = Array.from(fakeRow.children) as HTMLTableCellElement[];
    for (let i = 1; i < rows.length; i++) {
      const rowCells = Array.from(
        rows[i].querySelectorAll('td, th')
      ) as HTMLTableCellElement[];

      // Check that the columns match up including colSpan
      const lastRowColumns = lastRowCells.reduce(
        (count, cell) => count + cell.colSpan,
        0
      );
      const rowColumns = rowCells.reduce(
        (count, cell) => count + cell.colSpan,
        0
      );
      if (lastRowColumns !== rowColumns) {
        console.warn(
          "Can't include top borders for barred grid - col count mismatch"
        );
        break;
      }

      for (let j = 0; j < lastRowCells.length; j++) {
        const lastCellStyle = window.getComputedStyle(lastRowCells[j]);
        const cellStyle = window.getComputedStyle(
          // if the cell count doesn't match, assume the last one has extra colSpan.
          // TODO: this will not work for cells in the middle with extra colSpan.
          rowCells[Math.min(j, rowCells.length - 1)]
        );
        if (
          lastCellStyle.getPropertyValue('border-bottom-width') === '0px' &&
          cellStyle.getPropertyValue('border-top-width') !== '0px'
        ) {
          const width = cellStyle.getPropertyValue('border-top-width');
          const style = cellStyle.getPropertyValue('border-top-style');
          const color = cellStyle.getPropertyValue('border-top-color');

          const coercedWidth = parseInt(width, 10) < 2 ? '1px' : '3px';
          const coercedColor = color === 'rgb(0, 0, 0)' ? 'black' : 'gray';
          const injectedStyle = `border-bottom: ${coercedWidth} ${style} ${coercedColor};`;
          addCopyOnlyStyles(lastRowCells[j], injectedStyle);
        }
      }

      lastRowCells = rowCells;
    }
  }

  // Add breaks after tables and hr elements.
  // Should be done after we duplicate grids with clues.
  for (const tag of ['table', 'hr']) {
    for (const element of rootElement.querySelectorAll(tag)) {
      if (
        findAncestor(element, shouldBeSkipped) ||
        getSetting(element, 'skipTableBreaks')
      )
        continue;

      const br = document.createElement('br');
      br.classList.add(HIDDEN_CLASS);
      element.parentNode?.insertBefore(br, element.nextSibling);
    }
  }
}

/** Marks an element with copyOnlyStyles to avoid changing the visual display of the grid. */
function addCopyOnlyStyles(element: HTMLElement, newStyles: string | string[]) {
  const styleText = Array.isArray(newStyles)
    ? newStyles.join(' ').trim()
    : newStyles;
  if (styleText) {
    const oldStyles = element.dataset.copyOnlyStyles || '';
    element.dataset.copyOnlyStyles =
      // Add an extra separator if it's missing
      (oldStyles.endsWith(';') ? oldStyles : oldStyles + ';') + styleText;
  }
}

function copyJackInlineStyles(
  element: HTMLElement,
  config: CopyConfig,
  keepStyles: string[] = []
) {
  const styles = window.getComputedStyle(element);
  // We can't read the styles reliably if it is hidden.
  if (styles.getPropertyValue('display') === 'none') {
    return;
  }

  const isDarkMode = !!element.closest('.darkmode');
  const isBackgroundColorTransparent =
    styles.getPropertyValue('background-color') === 'rgba(0, 0, 0, 0)';
  const isWhite = styles.getPropertyValue('color') === 'rgb(255, 255, 255)';

  const overriddenStyles = config.preserveStyles
    ? []
    : [
        ...(isDarkMode && isWhite && isBackgroundColorTransparent
          ? ['color: rgb(0, 0, 0);']
          : []),
      ];

  const jackedStyles = [
    // Only copyjack the background color if it isn't transparent. Otherwise, we
    // could clobber an inherited background color.
    ...(isBackgroundColorTransparent && !config.preserveStyles
      ? []
      : ['background-color']),
    // Only copyjack color if styles should be preserved
    ...(config.preserveStyles ? ['color'] : []),
    'font-family',
    'font-weight',
    'font-style',
    ...keepStyles, // Additional copies to keep
  ].map((prop) => `${prop}: ${styles.getPropertyValue(prop)};`);
  element.setAttribute(
    'style',
    [...jackedStyles, element.style.cssText].join(' ')
  );
  addCopyOnlyStyles(element, overriddenStyles);
}

function maybeAppendResetSpan(element) {
  // Don't break flex/grid containers by adding extra spans into them.
  const parentStyles = window.getComputedStyle(element.parentNode);
  const parentDisplay = parentStyles.getPropertyValue('display');
  if (parentDisplay.endsWith('flex') || parentDisplay.endsWith('grid')) return;

  const display = window.getComputedStyle(element).getPropertyValue('display');
  if (display.startsWith('inline')) {
    let nonInlineParent = element.parentNode;
    while (
      nonInlineParent &&
      window
        .getComputedStyle(nonInlineParent)
        .getPropertyValue('display')
        .startsWith('inline')
    ) {
      nonInlineParent = nonInlineParent.parentNode;
    }
    const nonInlineParentDisplay = window
      .getComputedStyle(nonInlineParent)
      .getPropertyValue('display');
    if (
      nonInlineParent === element.parentNode &&
      (nonInlineParentDisplay.endsWith('flex') ||
        nonInlineParentDisplay.endsWith('grid'))
    )
      return;

    // Keep the inline element styles if it is the only text content.
    if (nonInlineParent.innerText.trim() === element.innerText.trim()) {
      return;
    }
  }

  const reset = document.createElement('span');
  reset.style.backgroundColor = 'transparent';
  reset.style.color = 'black';
  reset.style.fontFamily = DEFAULT_FONT_FAMILY;
  reset.style.fontWeight = 'normal';
  reset.style.fontSize = DEFAULT_FONT_SIZE;
  reset.style.fontStyle = 'normal';
  reset.style.textAlign = 'left';

  // Hide reset to prevent from messing up page layout
  reset.classList.toggle('copyjack-reset', true);
  reset.classList.toggle(HIDDEN_CLASS, true);

  element.parentNode.insertBefore(reset, element.nextSibling);
}

function copyJackInlineBorders(element) {
  // For barred grids, we need some awkward workarounds so they copy correctly.
  // Essentially, if we want borders with different thickness, one of the
  // borders must be missing or it copies wrong.
  //
  // We hack it by removing the top border. And then injecting a row at the top
  // of the table and give it a bottom-border. There's some sophistication to
  // handle cells that have no border though.
  const inBarredGrid = !!element.closest('.barred');
  const styles = window.getComputedStyle(element);
  const borderStyles = ['top', 'bottom', 'right', 'left'].map((dir) => {
    const [width, style, color] = ['width', 'style', 'color'].map((attribute) =>
      styles.getPropertyValue(`border-${dir}-${attribute}`)
    );
    if (width === '0px') return '';
    // In barred grids, force the top border to 0px. Separately, a top row will
    // be injected at copy time.
    if (inBarredGrid && dir === 'top') return '';
    // Google Sheets only handles black or gray borders (untested). Treat black
    // as black, and everything else as gray.
    // Also, getComputedStyle returns resolved values, so the color has a
    // standard format.
    // And Sheets only likes 1px and 3px borders, so coerce it.
    const coercedWidth = parseInt(width, 10) < 2 ? '1px' : '3px';
    const coercedColor = color === 'rgb(0, 0, 0)' ? 'black' : 'gray';
    return `border-${dir}: ${coercedWidth} ${style} ${coercedColor};`;
  });
  addCopyOnlyStyles(element, borderStyles);
}

function copyJackTableLinks(element) {
  if (
    element.children.length === 1 &&
    element.firstElementChild.tagName.toLowerCase() === 'a'
  ) {
    // In Google Sheets, links within table cells won't work. Add special case
    // handling for the case where the table cell directly contains an anchor tag.
    //
    // Note: we use children and firstElementChild to ignore text/comment nodes.
    element.dataset.sheetsValue = '';
    element.dataset.sheetsHyperlink = makeHrefAbsolute(
      element.firstElementChild.href
    );
  }
}

function copyJackImage(element: HTMLImageElement) {
  if (findAncestor(element, shouldBeSkipped)) {
    return;
  }

  element.classList.add(NO_COPY_CLASS);

  const altText = element.getAttribute('alt');
  const label = altText
    ? `[Image: ${altText}]`
    : '[See original puzzle for image]';

  const container = document.createElement('div');
  container.className = HIDDEN_CLASS;

  let labelElement = container;

  // Nested links don't work, so don't wrap the image with an anchor tag if
  // there is a parent anchor tag already.
  const ancestorLink = findAncestor(
    element,
    (el) => el.tagName.toLowerCase() === 'a'
  );
  const copiedImageLink = ancestorLink ? ancestorLink.href : element.src;

  // In Google Sheets, we can use special attributes to let images render
  // inline. If the image is inside a `th` or `td` tag already, then these
  // special attributes need to be placed on that element.
  let sheetsImageWrapper;
  const ancestorTableCell = findAncestor(element, (el) => {
    const parentTagName = el.tagName.toLowerCase();
    return parentTagName === 'td' || parentTagName === 'th';
  });
  if (ancestorTableCell) {
    // If there is other content, placing the special attributes will hide the
    // other content. That's bad, so bail out of embedding our inline images.
    //
    // As an approximation, content can either be images or text. We can use
    // innerText instead of textContent, so that if the text if hidden (say with
    // no-copy), then it doesn't break us.
    const tableCellHasOtherContent =
      ancestorTableCell.innerText.trim() ||
      ancestorTableCell.querySelectorAll('img').length > 1;
    if (!tableCellHasOtherContent) {
      sheetsImageWrapper = ancestorTableCell;
    }
  } else {
    sheetsImageWrapper = document.createElement('div');
    labelElement = sheetsImageWrapper;
    container.appendChild(sheetsImageWrapper);
  }

  let sheetsFormula = '';
  if (sheetsImageWrapper) {
    sheetsImageWrapper.dataset.sheetsValue = '';
    if (element.src) {
      if (isSvg(element.src)) {
        sheetsImageWrapper.dataset.sheetsHyperlink = copiedImageLink;
      } else if (isLocalhostUrl(element.src)) {
        // Local URLs won't load when pasted into Google Sheets, so skip embedding them.
        // TODO: Image copying is broken, so just override the text.
        sheetsFormula = `IMAGE("${element.src}")`;
        sheetsImageWrapper.dataset.sheetsHyperlink = copiedImageLink;
      } else {
        sheetsFormula = `=HYPERLINK("${element.src}", IMAGE("${element.src}"))`;
        sheetsImageWrapper.dataset.sheetsFormula = `=HYPERLINK("${element.src}", IMAGE("${element.src}"))`;
      }
    } else {
      // Links in table cell elements won't work for Google Sheets, set the
      // hyperlink on the cell directly.
      //
      // This will only have an effect if we haven't already embedded an image
      // in the cell, so check that first.
      sheetsImageWrapper.dataset.sheetsHyperlink = copiedImageLink;
    }
  }

  if (ancestorLink) {
    //labelElement.textContent = label;
    labelElement.textContent = sheetsFormula || label;
  } else {
    const imageLink = document.createElement('a');
    imageLink.href = makeHrefAbsolute(copiedImageLink);
    //imageLink.textContent = label;
    imageLink.textContent = sheetsFormula || label;
    labelElement.appendChild(imageLink);
  }

  element.parentNode?.insertBefore(container, element.nextSibling);
}

const shouldBeSkipped = (el) => el.classList.contains(NO_COPY_CLASS);

function findAncestor(el, predicate) {
  while (el && el !== document.body) {
    if (predicate(el)) {
      return el;
    }
    el = el.parentNode;
  }
  return null;
}

function isLocalhostUrl(url) {
  const parsed = new URL(url);
  return (
    parsed.hostname.toLowerCase() === 'localhost' ||
    parsed.hostname === '127.0.0.1'
  );
}

function isSvg(url) {
  const parsed = new URL(url);
  return parsed.pathname.endsWith('.svg');
}

function recursiveClone(
  rootNode,
  filterPredicate: (node: HTMLElement) => boolean = () => true,
  transformer: (node: HTMLElement) => Node | void = () => {}
) {
  const result = rootNode.cloneNode();
  const transformedResult = transformer(result) || result;

  for (const child of rootNode.childNodes) {
    if (filterPredicate(child)) {
      transformedResult.appendChild(
        recursiveClone(child, filterPredicate, transformer)
      );
    }
  }
  return transformedResult;
}

export function makeHrefAbsolute(href) {
  return href.startsWith('/') ? location.origin + href : href;
}

function resolveListIndex(index: number, listStyleType) {
  switch (listStyleType) {
    case 'upper-alpha':
      return String.fromCharCode(64 + Math.max(Math.min(index, 26), 1)) + '. ';

    case 'lower-alpha':
      return String.fromCharCode(96 + Math.max(Math.min(index, 26), 1)) + '. ';

    case 'decimal':
    default:
      return index.toString() + '. ';
  }
}

// TODO(sahil): I'm sure this can be made more efficient.
const LEADING_WHITESPACE_REGEX = /^[^\S\r\n]+/gm;
const MANY_LF_REGEX = /\n{3,}/g;
const MANY_CRLF_REGEX = /(\r\n){3,}/g;
function trimPlainText(rawPlainText) {
  let result = rawPlainText.trim();
  result = result.replaceAll(LEADING_WHITESPACE_REGEX, '');
  result = result.replaceAll(MANY_LF_REGEX, '\n\n');
  result = result.replaceAll(MANY_CRLF_REGEX, '\r\n\r\n');
  return result;
}
