const IS_SHARED_WORKER = (
  typeof SharedWorkerGlobalScope !== 'undefined' &&
  self instanceof SharedWorkerGlobalScope
);

function uuidv4() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

// If adding to requirements, you must make sure that we mirror new packages
// correctly if they exist in the Pyodide repo. Our repo only contains the
// subset that we use. (Packages not from Pyodide and only in PyPi will be
// fetched correctly.)
const requirements = {
  // organized by `import_name: package_name`
  // Pyodide built-ins
  'PIL.Image': 'Pillow',
  yaml: 'pyyaml',
  pytz: 'pytz',
  // PyPi
  django: 'Django==3.1.7',
  ratelimit: 'django-ratelimit==3.0.0',
  html2text: 'html2text==2020.1.16',
  importlib_resources: 'importlib_resources==5.2.2',
  markdown: 'Markdown==3.2.2',
  dateutil: 'python-dateutil==2.8.1',
  redis: 'redis==3.5.3',
  requests: 'requests==2.25.1',
  emoji: 'emoji==1.2.0', // server version is 1.5.0
};

/*
interface PyodideWorkerGlobalScope extends SharedWorkerGlobalScope {
  XMLHttpRequest: any;
  loadPyodide(config: any);
  pyodide: any;
  context: Map<string, any>;
  requirements: Map<string, string>[];
  broadcastChannel: BroadcastChannel;
}

declare var self: PyodideWorkerGlobalScope;
*/
self.context = new Map();
self.requirements = requirements;
if (IS_SHARED_WORKER) {
  self.broadcastChannel = new BroadcastChannel('shared-worker-broadcast');
} else {
  self.broadcastChannel = self;
}

// const indexURL = 'https://cdn.jsdelivr.net/pyodide/v0.18.1/full/';
const indexURL = '/pyodide/v0.18.1/';

const syncFsPromise = (self) => {
  return new Promise((success, reject) => {
    self.pyodide.FS.syncfs(true, (err) => {
      if (err) reject(err);
      else success(undefined);
    });
  });
};

self.importScripts(`${indexURL}pyodide.js`);
async function loadPyodideAndPackages() {
  try {
    console.log('Checking IndexedDB');
    const testDbName = 'canary';
    const testDbPromise = new Promise((resolve, reject) => {
      const testDb = self.indexedDB.open(testDbName);
      testDb.onsuccess = resolve;
      testDb.onerror = reject;
    });
    await testDbPromise;
    self.indexedDB.deleteDatabase(testDbName);
    console.log('Starting load');
    self.pyodide = await self.loadPyodide({
      indexURL: indexURL,
      fullStdLib: false,
    });
    console.log('Loading cache');
    self.pyodide.FS.mkdir('/indexeddb');
    self.pyodide.FS.mount(self.pyodide.FS.filesystems.IDBFS, {}, '/indexeddb');
    const syncPromise = syncFsPromise(self);
    console.log('Awaiting sync')
    await syncPromise;
    console.log('Synced')
    // TODO: move into pyodide_entrypoint
    await self.pyodide.runPythonAsync(`
    import importlib
    import logging
    import os
    import sys
    import zipfile
    import js
    sys.path.append('/indexeddb/site-packages.zip')
    sys.path.append('/server.zip')
    sys_packages = []
    os.environ['SETUPTOOLS_USE_DISTUTILS'] = 'local'
    try:
      with zipfile.ZipFile('/indexeddb/immovable-site-packages.zip') as zipf:
        site_packages = '/lib/python3.9/site-packages'
        for name in zipf.namelist():
          if not os.path.isfile(os.path.join(site_packages, name)):
            zipf.extract(name, site_packages)
    except Exception as e:
      logging.warn(e)
    print('Checking packages')
    for pkg, override in [
      ('micropip', None),
      ('setuptools', None),
    ]:
      try:
        if override is not None:
          override()
        else:
          importlib.import_module(pkg)
      except ImportError as e:
        logging.warn(e)
        logging.warn(pkg)
        sys_packages.append(pkg)
    if sys_packages:
      await js.pyodide.loadPackage(sys_packages)
    import micropip
    packages = []
    for req, pkg in js.requirements.to_py().items():
      try:
        importlib.import_module(req)
      except ImportError as e:
        packages.append(pkg)
    tasks = []
    if packages:
      tasks.append(micropip.install(packages))
    print('Fetching server code')
    response = await js.fetch('/api/server.zip')
    js_buffer = await response.arrayBuffer()
    with open('/server.zip', 'wb') as f:
      f.write(js_buffer.to_py())
    print('Awaiting python install')
    for task in tasks:
      await task
    importlib.invalidate_caches()
    print('Dependencies loaded')
    import pyodide_entrypoint
    `);
  } catch (error) {
    console.error(error);
    pyodideUnavailable = true;
    self.broadcastChannel.postMessage({
      type: 'worker-unavailable',
    });
    throw Error(error);
  }
  console.log('Finished load');
  pyodideReady = true;
  self.broadcastChannel.postMessage({
    type: 'worker-ready',
  });
}
let pyodideReady = false;
let pyodideUnavailable = false;
const pyodideReadyPromise = loadPyodideAndPackages();

const onmessage = (port) => (event) => {
  const func = async () => {
    if (!pyodideReady) return;
    switch(event.data.type) {
    case 'python':
      {
        const { script } = event.data;
        // const reply : any = {
        const reply = {
          type: 'python',
          id: event.data.id,
        };
        try {
          const result = self.pyodide.runPython(script);
          reply.result = result;
        } catch (error) {
          reply.error = error.message;
        }
        port.postMessage(reply);
      }
      break;
    case 'websocket':
      {
        const {url, data} = event.data;
        const pathname = new URL(url, 'https://teamamtehunt.com').pathname;
        const regexPuzzlePath = /\/puzzles\/([^\/]+)/;
        const match = pathname.match(regexPuzzlePath);
        // let puzzle : string | undefined = undefined;
        let puzzle;
        if (match) puzzle = match[1];
        const id = uuidv4();
        self.context.set(id, { data, puzzle });
        await syncFsPromise(self).catch(() => {});
        self.pyodide.runPython(`
        import js
        from puzzles.consumers import ClientConsumer
        context = js.globalThis.context['${id}'].to_py()
        ClientConsumer().receive_json(
          context['data'],
          puzzle_slug_override=context['puzzle'],
        )
        None
        `);
        self.context.delete(id);
      }
      break;
    case 'fetch':
      {
        const {type, path, id, ...options} = event.data;
        self.context.set(id, { path, ...options });
        await syncFsPromise(self).catch(() => {});
        self.pyodide.runPython(`
        import js
        import pyodide
        context = js.globalThis.context['${id}'].to_py()
        from tph.utils import get_mock_response
        js.globalThis.context['${id}'].response = pyodide.to_js(
          get_mock_response(**context),
          dict_converter=js.Object.fromEntries,
        )
        None
        `);
        const response = self.context.get(id).response;
        self.context.delete(id);
        port.postMessage({
          type: 'fetch',
          id,
          response,
        });
      }
      break;
    default:
      break;
    }
  };
  func();
};

if (IS_SHARED_WORKER) {
  self.addEventListener('connect', (event) => {
    console.log('Client has connected to the shared worker.');
    const port = event.ports[0];
    port.onmessage = onmessage(port);
    if (pyodideReady) {
      self.broadcastChannel.postMessage({
        type: 'worker-ready',
      });
    }
    if (pyodideUnavailable) {
      self.broadcastChannel.postMessage({
        type: 'worker-unavailable',
      });
    }
  });
} else {
  console.log('Client has connected to the worker.');
  self.onmessage = onmessage(self);
}
