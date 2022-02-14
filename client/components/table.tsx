import React, { FunctionComponent } from 'react';

const Table = (props) => (
  <div className="wrapper">
    <table {...props} />

    <style jsx>{`
      .wrapper {
        max-width: 100%;
        overflow-x: auto;
      }
    `}</style>
  </div>
);

export const FullTable = (props) => (
  <>
    <table {...props} />

    <style jsx>{`
      table {
        min-width: 100%;
        max-width: 100%;
        overflow-x: auto;
      }
    `}</style>
  </>
);

export default Table;
