import React from 'react';

import assetBg from 'assets/museum/bg.png';

// FIXME: Customize your themes here!
const DefaultTheme = () => {
  return (
    <style global jsx>{`
      #__next {
        background-image: url(${assetBg});
        background-size: 730px 674px;
        background-repeat: repeat;
      }

      button[type='submit'],
      input[type='submit'] {
        border: 1px solid black;
        border-radius: 4px;
        padding: 4px;
      }
    `}</style>
  );
};

const Theme1 = () => (
  <style global jsx>{`
    :root {
      --primary: #a40000;
    }

    #__next {
      background-repeat: repeat;
    }
  `}</style>
);

const Theme2 = () => (
  <style global jsx>{`
    :root {
      --primary: #34b7bf;
    }

    #__next {
      background-repeat: repeat;
    }
  `}</style>
);

const RoundTheme = ({ roundSlug }) => {
  // A silly way to obfuscate round slugs.
  const firstChar = (roundSlug ?? '').charAt(0);

  if (firstChar === 'a') {
    return <Theme1 />;
  } else {
    return <Theme2 />;
  }

  return <DefaultTheme />;
};

export default RoundTheme;
