import { createContext } from 'react';
import { Sprite } from 'components/game/message_box';

interface RoundData {
  slug: string;
  name: string;
  url: string;
}

export interface TeamInfo {
  name: string;
  slug: string;
  rounds?: RoundData[][]; // Grouped by act
  state?: number;
}

export interface Errata {
  text: string;
  time: string;
  puzzleName: string;
}

export interface HuntInfo {
  huntInfo: {
    startTime: string;
    secondsToStartTime: number;
    endTime: string;
    closeTime?: string;
    hintReleaseTime: string;
    toggle?: string;
    worker?: string;
    site?: 'hunt' | 'registration' | null;
  };
  // This data is only present if the user is logged in.
  userInfo?: {
    // This data is only present if the user has a team.
    teamInfo?: TeamInfo;
    superuser?: boolean;
    public?: boolean;
    isImpersonate?: boolean;
    // Additional urls that are unlocked and visible on the navbar.
    unlocks?: {
      url: string;
      pageName: string;
    }[];
    errata?: Errata[];
  };
  uuid: string;
  round: {
    theme?: string;
    slug?: string;
    act?: number;
  };
}

// Only useful to distinguish logging in as a team/individual during registration,
// since "free agents" can edit registration without being part of a team,
// but during the hunt, every user should be logging in via a team.
export const isLoggedInAs = (
  huntInfo: HuntInfo
): 'team' | 'individual' | undefined =>
  huntInfo.userInfo?.teamInfo
    ? 'team'
    : huntInfo.userInfo
    ? 'individual'
    : undefined;

export const EMPTY_HUNT_INFO: HuntInfo = {
  // Provide some default values for typechecking. However, the server will
  // provide this context in App.getInitialProps before rendering any component.
  huntInfo: {
    startTime: '',
    secondsToStartTime: 1234567,
    endTime: '',
    closeTime: '',
    hintReleaseTime: '',
  },
  uuid: '',
  round: {},
};

interface MessageBox {
  text: string;
  setText: (text: string) => void;
  sprite?: Sprite;
  setSprite: (sprite?: Sprite) => void;
}

const EMPTY_MESSAGE_BOX: MessageBox = {
  text: '',
  setText: () => {},
  sprite: undefined,
  setSprite: () => {},
};

// Context that will be present for any component.
const HuntInfoContext = createContext<HuntInfo>(EMPTY_HUNT_INFO);

// Context for setting message box in factory
export const MessageBoxContext = createContext<MessageBox>(EMPTY_MESSAGE_BOX);

export default HuntInfoContext;
