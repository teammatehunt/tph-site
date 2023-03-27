import React, { FC } from 'react';

const FlavorText: FC = ({ children }) => {
  return (
    <>
      <p className="block flavortext">{children}</p>
      <style jsx>{`
        .flavortext {
          font-style: italic;
        }
      `}</style>
    </>
  );
};

export default FlavorText;
