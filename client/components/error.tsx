const getErrorComponent = (error: Error) => () => {
  return (
    <div className="bg-white">
      <h2>Something went wrong!</h2>
      <p>Please refresh or contact HQ with the following error:</p>
      <code className="text-red-900">{error.toString()}</code>
    </div>
  );
};

export default getErrorComponent;
