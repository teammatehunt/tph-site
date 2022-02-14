import React, { FunctionComponent, useCallback, useContext } from 'react';

import HuntInfoContext from 'components/context';
import ResetLocalDatabaseButton from 'components/reset_local_database_button';
import dynamic from 'next/dynamic';

const ShowSolvedSwap = dynamic(() => import('components/show_solved_swap'), {
  ssr: false,
});

interface Props {
  showSolved: boolean;
  setShowSolved: (showSolved: boolean) => void;
}

const PostHuntSettings: FunctionComponent<Props> = ({
  showSolved,
  setShowSolved,
}) => {
  const { userInfo, huntInfo } = useContext(HuntInfoContext);
  const loggedIn = !!userInfo?.teamInfo;
  const huntIsOver = huntInfo && new Date() > new Date(huntInfo.endTime);

  if (!huntIsOver || loggedIn) {
    return null;
  }
  return (
    <>
      <div>
        <ShowSolvedSwap showSolved={showSolved} setShowSolved={setShowSolved} />
        <ResetLocalDatabaseButton />
      </div>
      <style jsx>{`
        div {
          display: flex;
          align-items: top;
          justify-content: space-between;
        }
      `}</style>
    </>
  );
};

export default PostHuntSettings;
