import { useContext } from 'react';

import HuntInfoContext from 'components/context';
import InfoIcon from 'components/info_icon';
import WorkerLoadingIcon from 'components/worker_loading_icon';

export const UnsupportedMessage = ({ obj = 'puzzle', ...props }) => (
  <InfoIcon border {...props}>
    Sorry! This {obj} is not currently supported in the public access team. We
    are working to bring this functionality back as soon as possible.
  </InfoIcon>
);

const Unsupported = ({ obj = 'puzzle' }) => {
  const { userInfo } = useContext(HuntInfoContext);
  if (userInfo?.public) {
    if (process.env.useWorker) {
      return <WorkerLoadingIcon />;
    } else {
      return <UnsupportedMessage obj={obj} />;
    }
  }

  return null;
};

export default Unsupported;
