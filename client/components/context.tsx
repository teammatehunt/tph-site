import { createContext } from 'react';

import { TeamMember } from 'components/register';

export interface TeamInfo {
  name: string;
  slug: string;
  solves: number;
  members?: TeamMember[];
  stage?: string;
}

export interface Story {
  slug: string;
  text: string;
  url?: string;
  deep: number;
  modal: boolean;
  puzzleSlug?: string;
  introOnly?: boolean;
}

export interface Errata {
  text: string;
  time: string;
  formattedTime?: string;
  puzzleName: string;
}

export interface HuntInfo {
  huntInfo: {
    startTime: string;
    secondsToStartTime: number;
    endTime: string;
    closeTime: string;
    hintReleaseTime: string;
    storyUnlocks: Story[];
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
}

export const EMPTY_HUNT_INFO: HuntInfo = {
  // Provide some default values for typechecking. However, the server will
  // provide this context in App.getInitialProps before rendering any component.
  huntInfo: {
    startTime: '',
    secondsToStartTime: 1234567,
    endTime: '',
    closeTime: '',
    hintReleaseTime: '',
    storyUnlocks: [],
  },
};

// Context that will be present for any component.
const HuntInfoContext = createContext<HuntInfo>(EMPTY_HUNT_INFO);

export default HuntInfoContext;
