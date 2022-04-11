
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
  const data = await response.json();

  if (response.status == 200) {
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

export function getData(url, setFn) {

    // Use localStorage to make site more responsive. Save fetch results in local storage.
    // When fetching in the future, this function will apply the currently cached results
    // before making the request, and then update the results when the request completes.
    //
    // sessionStorage is intentionally NOT used here (and for the auth token) because session
    // data is frequently unavailable on mobile where pages are always opened in new tabs.
    const cachedData = getCacheData(url);
    if (cachedData) {
      setFn(cachedData);
    }

    function setFnWrapper(data) {
        setCacheData(url, data);
        setFn(data);
    }

    fetch(url, {
      credentials: 'include',
      headers: {'Authorization': getAuthHeader()},
    })
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
      .then(obj => {
          return setFnWrapper(obj.body)
      });
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
