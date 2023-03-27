import React from 'react';

import Hint, { getHintServerSideProps } from 'components/hints';

const HintPage = ({ puzzleData }) => {
  return <Hint puzzleData={puzzleData} className="bg-white" />;
};

export default HintPage;

export const getServerSideProps = getHintServerSideProps(1);
