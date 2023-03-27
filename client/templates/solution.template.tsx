import { FC } from 'react';

import AuthorsNotes from 'components/authors_notes';
import SheetableImage from 'components/sheetable_image';
import Solution, { Answerize } from 'components/solution';
import Table from 'components/table';
import { Monospace } from 'components/copy';
import { PuzzleDataProps, getPuzzleProps } from 'components/puzzle';

/*[[INSERT IMPORTS]]*/

const SLUG = '[[INSERT SLUG]]';
const ANSWER = `[[INSERT ANSWER]]`;
const AUTHORS = '[[INSERT AUTHORS]]';

const PuzzleSolution: FC<PuzzleDataProps> = ({ puzzleData }) => (
  <Solution puzzleData={puzzleData} answer={ANSWER} authors={AUTHORS}>
    [[INSERT CONTENT]]
  </Solution>
);

export default PuzzleSolution;
export const getServerSideProps = getPuzzleProps(SLUG);
