import Head from 'next/head';

const COMMENT = `



For automated querying of unlocked puzzles, you can fetch a json from
/api/puzzle_list
. This endpoint is not a puzzle.



`;

const PuzzleApiComment = () => {
  /*if (typeof window === 'undefined') {
    return (
      <Head>
        <script type="comment">{COMMENT}</script>
      </Head>
    );
  }*/
  return null;
};
export default PuzzleApiComment;
