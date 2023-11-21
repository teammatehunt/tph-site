import React from 'react';

import Section from 'components/section';
import Title from 'components/title';

const HaveYouTried = () => (
  <>
    <Title title="Have You Tried..." subline="the carnival guidebook" />

    <Section narrow heading="Getting Started">
      <h5>Have you tried&hellip;</h5>
      <ul>
        <li>
          &hellip; reading the title and the flavor text: what parts stand out
          as clues?
        </li>
        <li>&hellip; typing key words into a search engine?</li>
        <li>
          &hellip; checking if the clues are sorted, and finding another way to
          sort them?
        </li>
        <li>&hellip; putting it in a spreadsheet?</li>
      </ul>
    </Section>

    <Section narrow heading="Puzzlehunt classics">
      <h5>Have you tried&hellip;</h5>
      <ul>
        <li>&hellip; reading the first letters of each sentence or clue?</li>
        <li>&hellip; rearranging the letters (aka “anagramming”)?</li>
        <li>
          &hellip; diagonalizing (taking the first letter of the first answer,
          the second letter of the second&hellip;)?
        </li>
        <li>
          &hellip; looking for references to a song/poem/book/movie/TV show?
        </li>
        <li>&hellip; changing the base of numbers (including hex)?</li>
        <li>
          &hellip; interpreting words as{' '}
          <a href="https://puzzling.stackexchange.com/a/45985">
            cryptic crossword clues
          </a>
          ? As puns?
        </li>
        <li>&hellip; looking for unusual letter frequencies?</li>
        <li>&hellip; looking for double letters?</li>
        <li>&hellip; adding a letter to everything?</li>
        <li>&hellip; removing a letter from everything?</li>
        <li>
          &hellip; looking for compass directions (N, E, S, W) or relative
          directions (L, R, U, D)?
        </li>
        <li>&hellip; looking at a computer keyboard?</li>
        <li>
          &hellip; ”doing it again” (repeating the puzzle mechanic on the
          output)?
        </li>
        <li>
          &hellip; doing it in reverse (e.g. re-ciphering after deciphering)?
        </li>
        <li>
          &hellip; counting different things in the puzzle and checking if the
          counts match up?
        </li>
        <li>&hellip; chaining answers together into a sequence or cycle?</li>
        <li>
          &hellip; looking up{' '}
          <a href="https://phenomist.wordpress.com/storage/sets/">
            sets of things
          </a>
          ? (courtesy of phenomist)
        </li>
      </ul>
    </Section>

    <Section narrow heading="Common Encodings">
      <h5>Have you tried&hellip;</h5>
      <ul>
        <li>&hellip; letters to numbers (A=1, Z=26)?</li>
        <li>&hellip; Binary?</li>
        <li>&hellip; Braille?</li>
        <li>&hellip; Morse code?</li>
        <li>&hellip; Pigpen?</li>
        <li>&hellip; Flag semaphore?</li>
        <li>&hellip; ROT13/Caesar shift?</li>
        <li>&hellip; QWERTY?</li>
        <li>&hellip; ASCII?</li>
        <li>&hellip; International Phonetic Alphabet?</li>
        <li>&hellip; Seeing if it looks like a picture of something?</li>
        <li>&hellip; Atomic weights, numbers, etc.?</li>
        <li>&hellip; Element symbols?</li>
        <li>&hellip; Latitude/longitude or GPS coordinates?</li>
      </ul>
    </Section>

    <Section narrow heading="Another Perspective">
      <h5>Have you tried&hellip;</h5>
      <ul>
        <li>&hellip; asking for fresh eyes?</li>
        <li>&hellip; explaining the puzzle to a teammate?</li>
        <li>
          &hellip; writing up a hint request with everything you tried? (even if
          hints aren’t available)
        </li>
        <li>
          &hellip; asking people if it looks like anything they recognize?
        </li>
        <li>&hellip; rereading the instructions?</li>
        <li>&hellip; saying everything out loud?</li>
        <li>
          &hellip; thinking like the puzzle authors: what was obviously an
          intentional decision vs a possible coincidence? If a clue seems
          particularly odd or bad, why might they have been forced to use it?
        </li>
        <li>&hellip; asking “what’s the pattern”?</li>
        <li>&hellip; thinking about what’s missing?</li>
        <li>
          &hellip; asking yourself whether you’ve used all the information?
        </li>
        <li>&hellip; going outside and coming back to it later?</li>
        <li>&hellip; writing it down on a piece of paper?</li>
        <li>&hellip; changing a file to a different file extension?</li>
      </ul>
    </Section>

    <Section narrow heading="Extraction">
      <h5>Have you tried&hellip;</h5>
      <ul>
        <li>
          &hellip; tracking the lengths of answers?
          <ul>
            <li>&hellip; are they all the same length?</li>
            <li>
              &hellip; can you form a shape, such as a square or interlocking
              grid?
            </li>
            <li>
              &hellip; are they consecutive lengths that you can order by?
            </li>
          </ul>
        </li>
        <li>
          &hellip; prefacing or following your answers by another word or letter
          to make a common word or phrase?
        </li>
        <li>
          &hellip; looking for semantically related words or phrases with
          something in common?
        </li>
        <li>
          &hellip; looking for a thematic transformation that could be applied
          to all the answers?
        </li>
        <li>
          &hellip; checking if your answers collectively have all the letters of
          the alphabet?
        </li>
        <li>
          &hellip; counting the total number of letters in the answers? Does it
          correspond to something else in the puzzle?
        </li>
        <li>
          &hellip; breaking up the answers into two parts and extracting each
          half separately (e.g. if each answer is two words, sort using the
          lengths of the firsts and find something in common with the seconds)?
        </li>
        <li>
          &hellip; dividing your answers into two sets, and pairing them up?
        </li>
      </ul>
    </Section>

    <style jsx>{`
      h5 {
        margin: 4px 0;
      }

      li {
        list-style-type: none;
        margin: 0 0 4px 16px;
        text-indent: -16px;
      }
    `}</style>
  </>
);

export default HaveYouTried;
