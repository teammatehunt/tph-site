import { FC } from 'react';

import Solution from 'components/solution';
import { getPuzzleProps } from 'components/puzzle';

const SLUG = '[[INSERT SLUG]]';
const ANSWER = '[[INSERT ANSWER]]';
const AUTHORS = 'FIXME';

const PuzzleSolution: FC = () => (
  <Solution
    title="[[INSERT TITLE]]"
    slug={SLUG}
    answer={ANSWER}
    authors={AUTHORS}
  >
    [[INSERT SOLUTION CONTENT]]
  </Solution>
);

export default PuzzleSolution;
export const getServerSideProps = getPuzzleProps(SLUG);
