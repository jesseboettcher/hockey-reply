import { getPageData, setCacheData } from './utils';

beforeEach(() => {
  window.localStorage.clear();
  global.fetch = jest.fn();
});

afterEach(() => {
  delete global.fetch;
});

test('starts independent requests together and displays replies before a slower endpoint', async () => {
  let finishGame;
  const gameHandler = jest.fn();
  const repliesHandler = jest.fn();
  const refreshed = jest.fn();
  setCacheData('/game', { cached: true });
  fetch.mockImplementation(url => url === '/game'
    ? new Promise(resolve => { finishGame = resolve; })
    : Promise.resolve({ status: 200, json: async () => ({ replies: [] }) }));

  const loading = getPageData([
    { url: '/game', handler: gameHandler },
    { url: '/replies', handler: repliesHandler },
  ], refreshed);

  expect(gameHandler).toHaveBeenCalledWith({ cached: true });
  expect(fetch).toHaveBeenCalledTimes(2);
  // Drain the already-resolved reply request while the game request is pending.
  await new Promise(resolve => setTimeout(resolve, 0));
  expect(repliesHandler).toHaveBeenCalledWith({ replies: [] });
  expect(refreshed).not.toHaveBeenCalled();

  finishGame({ status: 200, json: async () => ({ fresh: true }) });
  expect(await loading).toBe(true);
  expect(gameHandler).toHaveBeenLastCalledWith({ fresh: true });
  expect(refreshed).toHaveBeenCalledTimes(1);
});

test('a network failure still loads the other sections and reports failure', async () => {
  const handler = jest.fn();
  const refreshed = jest.fn();
  fetch.mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ status: 200, json: async () => ({ replies: [] }) });
  expect(await getPageData([
    { url: '/game', handler: jest.fn() },
    { url: '/replies', handler },
  ], refreshed)).toBe(false);
  expect(handler).toHaveBeenCalledWith({ replies: [] });
  expect(refreshed).not.toHaveBeenCalled();
});

test('pending membership is accepted but server errors are reported', async () => {
  const refreshed = jest.fn();
  fetch.mockResolvedValueOnce({ status: 401 }).mockResolvedValueOnce({ status: 500 });
  const endpoints = [{ url: '/replies', handler: jest.fn() }];
  expect(await getPageData(endpoints, refreshed)).toBe(true);
  expect(await getPageData(endpoints, refreshed)).toBe(false);
  expect(refreshed).toHaveBeenCalledTimes(1);
});
