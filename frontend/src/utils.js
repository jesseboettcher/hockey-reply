import dayjs from 'dayjs';

// hasAuthToken is used as an indicator of whether is a user is logged in or not. It is
// possible the auth token is invalid, but unlikely. Using this lets the UI adjust immediately,
// without having to wait for server feedback to confirm sign in - and avoids blinky UI
export function hasAuthToken() {
  return window.localStorage.getItem('token') != undefined;
}

export function getAuthHeader() {
  let bearer = '';
  if (window.localStorage.getItem('token')) {
    bearer = `Bearer ${window.localStorage.getItem('token')}`;
  }
  return bearer;
}

export const checkLogin = async (navigate) => {

  const response = await fetch("/api/hello", {
    credentials: 'include',
    headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
  });

  if (response.status == 200) {
    const data = await response.json();
    return data;
  }

  if (navigate) {
    navigate(`/sign-in?redirect=${window.location.pathname}`, {replace: true});
  }
  return {}
}

export function logout(navigate) {
  window.localStorage.removeItem('token');
  navigate('/sign-in', {replace: true})
}

export const getPageData = async (url_handler_list, setLastRefreshHandler) => {

  // getPageData - Retrieve all the data required for a page, multiple endpoints

  let allSucceeded = true;

  // Apply cached data separately and immediately, so there are no delays with the async
  // functions, in getting something in front of the user
  for (const url_handler of url_handler_list) {
    applyCachedData(url_handler.url, url_handler.handler);
  }

  for (const url_handler of url_handler_list) {
    const responseStatus = await getData(url_handler.url, url_handler.handler, true);

    if (responseStatus != 200) {
      allSucceeded = false;
    }
  }
  if (allSucceeded) {
    setLastRefreshHandler(dayjs());
  }
  return allSucceeded;
}

export const getData = async (url, setFn, skipCached) => {

  // getData - Retrieve the data for a URL and sotre the results in the cache.

  // Use localStorage to make site more responsive. Save fetch results in local storage.
  // When fetching in the future, this function will apply the currently cached results
  // before making the request, and then update the results when the request completes.
  //
  // sessionStorage is intentionally NOT used here (and for the auth token) because session
  // data is frequently unavailable on mobile where pages are always opened in new tabs.
  if (!skipCached) {
    applyCachedData(url, setFn);
  }

  function setFnWrapper(data) {
      setCacheData(url, data);
      setFn(data);
  }

  const response = await fetch(url, {
      credentials: 'include',
      headers: {'Authorization': getAuthHeader()},
    });

  if (response.status == 200) {
    const data = await response.json();
    setFnWrapper(data);
  }
  return response.status;
}

export function setCacheData(key, saveData) {

  const DAYS_TO_EXPIRATION = 7;
  let expire = new Date();
  expire.setDate(expire.getDate() + DAYS_TO_EXPIRATION);

  window.localStorage.setItem(key, JSON.stringify({ expires_at: expire, data: saveData }));
}

export function getCacheData(key) {

  let retrieved = window.localStorage.getItem(key);
  try {
    retrieved = JSON.parse(retrieved);
  } catch(e) {
    // key is unparsable. Removing from cache
    window.localStorage.removeItem(key);
    return null;
  }

  if (retrieved) {
    let today = new Date();

    if (today > Date.parse(retrieved.expires_at)) {
      // key expired. Removing from cache
      window.localStorage.removeItem(key);
      return null;
    }

    return retrieved.data;
  }
  window.localStorage.getItem(key);
}

function applyCachedData(url, handler) {

    const cachedData = getCacheData(url);
    if (cachedData) {
      handler(cachedData);
    }
}
