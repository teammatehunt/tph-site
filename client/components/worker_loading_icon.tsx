import React from 'react';
import InfoIcon from 'components/info_icon';
import { SUPPORTS_SHARED_WORKER, useWorker } from 'utils/worker';

const WorkerLoadingIcon: React.FC<{ needsShared?: boolean }> = ({
  children,
  needsShared = false,
}) => {
  if (!process.env.useWorker) return null;
  const { ready, error } = useWorker();
  if (error || (needsShared && !SUPPORTS_SHARED_WORKER)) {
    return (
      <InfoIcon warning>
        Some interactive components are not supported by your browser. Please
        use a recent version of Firefox without private browsing or desktop
        Chrome.
      </InfoIcon>
    );
  }
  if (ready) return null;
  return (
    <InfoIcon>
      {children ? children : 'Loading interactive components...'}
    </InfoIcon>
  );
};

export default WorkerLoadingIcon;
