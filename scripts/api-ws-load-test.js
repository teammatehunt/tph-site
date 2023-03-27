// Sample load testing script for MH 2023.

// k6 run scripts/api-ws-load-test.js for local run
// When hitting local dev rather than staging, include --insecure-skip-tls-verify

import { check, sleep } from "k6";
import http from "k6/http";
import ws from "k6/ws";
import { Counter } from "k6/metrics";
import {
  uuidv4,
  randomIntBetween,
} from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const requests = new Counter("http_reqs");

// Tests APIs under load.

const num_users = 30;

export let options = {
  stages: [
    { duration: "1m", target: num_users }, // ramp up
    { duration: "10m", target: num_users }, // sustain
    { duration: "1m", target: 0 }, // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95) < 2000"],
  },
};

const DEV = false;
const PROD = false;
const CREDENTIALS = "FIXME:FIXME"; // Change me to basic auth
const AUTHORIZATION_HEADERS = "Basic FIXME";

let SITE, FACTORY_SITE, HEADERS, BASE_URL, BASE_FACTORY_URL;
let USERNAMES = [];
let PASSWORDS = [];
if (DEV) {
  SITE = "localhost:8081";
  FACTORY_SITE = "localhost:8082";
  HEADERS = {};
  BASE_URL = `https://${SITE}`;
  BASE_FACTORY_URL = `https://${FACTORY_SITE}`;
  USERNAMES.push("admin");
  PASSWORDS.push("admin");
  // USERNAMES.push('dev');
  // PASSWORDS.push('dev');
} else if (PROD) {
  SITE = "mypuzzlehunt.com";
  FACTORY_SITE = "mypuzzlehunt2.com";
  BASE_URL = `https://${CREDENTIALS}@${SITE}`;
  BASE_FACTORY_URL = `https://${CREDENTIALS}@${FACTORY_SITE}`;
  // Websocket URLs can't have basic auth added, do via header.
  HEADERS = { Authorization: AUTHORIZATION_HEADERS };
  for (let i = 1; i <= 10; i++) {
    USERNAMES.push(`test${i}`);
    PASSWORDS.push(`test${i}`);
  }
} else {
  // basic auth
  SITE = "staging.teammatehunt.com";
  FACTORY_SITE = "staging2.teammatehunt.com";
  BASE_URL = `https://${CREDENTIALS}@${SITE}`;
  BASE_FACTORY_URL = `https://${CREDENTIALS}@${FACTORY_SITE}`;
  // Websocket URLs can't have basic auth added, do via header.
  HEADERS = { Authorization: AUTHORIZATION_HEADERS };
  // Add staging test teams here.
}

const WS_BASE_URL = `wss://${SITE}`;
const WS_BASE_FACTORY_URL = `wss://${FACTORY_SITE}`;
const BASE_API_URL = `${BASE_URL}/api`;
const BASE_FACTORY_API_URL = `${BASE_FACTORY_URL}/api`;

// copied from useEventWebSocket code, minus some dependencies on browser-only functions.
// This does not support key, which is used by the frontend code to filter what messages
// the onJson listens to. We don't need to reimplement this unless we care about sending
// differing websocket messages in load test based on the server response. Doesn't seem
// necessary?
const buildWebsocketUrl = (site, options = {}) => {
  const base = site === "museum" ? WS_BASE_URL : WS_BASE_FACTORY_URL;
  const puzzle = options.slug;
  let wsPath = puzzle ? `/ws/puzzles/${puzzle}` : "/ws/events";
  // This is a URLSearchParams in codebase but that only exists in browser
  // It generates query string with escaping - assume we do not have URL encoding issues.
  let params = [];
  if (options.uuid) {
    params.push(`uuid=${options.uuid}`);
  }
  if (options.session_id) {
    params.push(`session_id=${options.session_id.toString()}`);
  }
  return `${base}${wsPath}?${params.join("&")}`;
};

const login = (ind) => {
  const username = USERNAMES[ind];
  const password = PASSWORDS[ind];
  const loginPostParams = {
    // csrfmiddlewaretoken: csrfMiddlewareToken,
    username: username,
    password: password,
  };
  const loginApiUrl = `${BASE_API_URL}/login`;
  const loginPostRes = http.post(loginApiUrl, loginPostParams, {
    // Required for CSRF verification.
    headers: {
      Origin: BASE_URL,
      Referer: loginApiUrl,
    },
  });
  const loginFactoryApiUrl = `${BASE_FACTORY_API_URL}/login`;
  const loginFactoryPostRes = http.post(loginFactoryApiUrl, loginPostParams, {
    // Required for CSRF verification.
    headers: {
      Origin: BASE_URL,
      Referer: loginFactoryApiUrl,
    },
  });
  check(loginFactoryPostRes, {
    "login succeeds": (r) => r.status === 200,
  });
};

// Sample load test for the Collage puzzle from MH 2023.
// The guess response of collage is an HTTP endpoint that saves guesses to DB and
// sends websocket messages to all viewers of the page, so it should be one of the more
// intensive puzzles of the site.
const collage = () => {
  // Do the client fetch for puzzle data.
  fetchPuzzleProps("collage");
  // Tried using the experimental websocket code in k6 and it just, didn't work as expected?
  // So we do everything inside the blocking ws.connect() call.
  const collageApiUrl = `${BASE_API_URL}/puzzle/collage/guess`;
  const makeGuess = () => {
    let randomGuess = [];
    for (let i = 0; i < 3; i++) {
      randomGuess.push(
        String.fromCharCode(65 + Math.floor(26 * Math.random()))
      );
    }
    const collagePostParams = { guess: randomGuess.join("") };
    const collagePostRes = http.post(collageApiUrl, collagePostParams, {
      // Required for CSRF verification.
      // (Or is it? Not sure)
      headers: {
        Origin: BASE_URL,
        Referer: collageApiUrl,
      },
    });
    check(collagePostRes, {
      "collage guess succeeds": (r) => r.status === 200,
    });
  };
  const params = {
    headers: HEADERS,
    tags: { key: "collage" },
  };
  // We start the websocket first, then make guesses while it's open.
  // This way different workers see each other's guesses.
  const collageWsUrl = buildWebsocketUrl("museum", { slug: "collage" });
  const res = ws.connect(collageWsUrl, params, (socket) => {
    // The HTTP and websocket APIs are both blocking, only one can run at a time.
    // https://community.k6.io/t/batch-execute-websocket-connect-request-and-http-request/3723
    // But you can attach the HTTP request to websocket setInterval to schedule it to run later
    // https://community.k6.io/t/websockets-and-http-requests-on-k6-scripts/861
    socket.on("open", () => {
      console.log("connected to collage");
    });
    socket.on("message", (data) => console.log("Message received: ", data));
    socket.on("close", () => console.log("disconnected"));
    socket.on("error", (e) => console.log("Error: ", e.error()));
    socket.setInterval(makeGuess, randomIntBetween(1000, 3000));
    socket.setTimeout(() => {
      socket.close();
    }, 30000);
  });
};

// A list of URLs that may request a large number of assets for #reasons
// We assume the team has access to all such URLs
const urls = [
  BASE_URL,
  BASE_FACTORY_URL,
  `${BASE_URL}/puzzles`,
  `${BASE_URL}/rounds/atrium`,
  `${BASE_URL}/rounds/science`,
  `${BASE_URL}/rounds/natural-history`,
  `${BASE_URL}/rounds/art`,
  `${BASE_URL}/rounds/world-history`,
  `${BASE_URL}/rounds/innovation`,
  `${BASE_FACTORY_URL}/puzzles`,
];
const loadPage = () => {
  const ind = randomIntBetween(0, urls.length - 1);
  console.log(`Hitting ${urls[ind]}`);
  const res = http.get(urls[ind]);
  let msg = {};
  msg[urls[ind]] = (r) => r.status === 200;
  check(res, msg);
};

export default () => {
  // Login as a test user.
  const ind = randomIntBetween(0, USERNAMES.length - 1);
  login(ind);
  sleep(1);

  const uuid = uuidv4();
  const weights = [10, 0, 0, 0, 0, 0];
  const tot = weights.reduce((partialSum, a) => partialSum + a, 0);
  let val = randomIntBetween(0, tot - 1);
  const funcs = [collage, loadPage];
  for (let i = 0; i < weights.length; i++) {
    if (val <= weights[i]) {
      funcs[i]();
      break;
    } else {
      val -= weights[i];
    }
  }
  sleep(3);
};
