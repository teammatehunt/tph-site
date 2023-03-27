import { createContext } from 'react';

export interface TeamInfo {
  name: string;
  slug: string;
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
    closeTime: string;
    hintReleaseTime: string;
    toggle?: string;
    worker?: string;
  };
  // This data is only present if the user is logged in.
  userInfo?: {
    // This data is only present if the user has a team.
    teamInfo?: TeamInfo;
    superuser?: boolean;
    isImpersonate?: boolean;
    // Additional urls that are unlocked and visible on the navbar.
    unlocks?: {
      url: string;
      pageName: string;
    }[];
    errata?: Errata[];
  };
  uuid: string;
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
};

// Context that will be present for any component.
const HuntInfoContext = createContext<HuntInfo>(EMPTY_HUNT_INFO);

export default HuntInfoContext;
