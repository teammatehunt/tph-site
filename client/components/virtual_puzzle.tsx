import React, { FC, useMemo, useState } from 'react';
import { useRouter } from 'utils/router';

import { Countdown } from 'components/countdown';
import InfoIcon from 'components/info_icon';
import useDynamicEncrypted from 'utils/encrypted';

interface Props {
  module: string;
  unlockTime?: number;
}
const VirtualPuzzle: FC<Props> = ({ module: mod, unlockTime = undefined }) => {
  const router = useRouter();
  const unlocked = unlockTime !== undefined && unlockTime <= 0;
  const PuzzleContent = useDynamicEncrypted(mod, { enabled: unlocked });

  if (unlockTime === undefined) {
    return <></>;
  }

  if (unlockTime > 0) {
    return (
      <InfoIcon border>
        The virtual version will unlock in{' '}
        <Countdown
          showHours
          seconds={unlockTime}
          textOnCountdownFinish={
            <>a few seconds (this page should automatically refresh)</>
          }
          countdownFinishCallback={router.reload}
        />
        .
      </InfoIcon>
    );
  }

  return <PuzzleContent />;
};

export default VirtualPuzzle;
