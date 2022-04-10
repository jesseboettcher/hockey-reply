
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

export function getData(url, setFn) {
    fetch(url, {
      credentials: 'include',
      headers: {'Authorization': getAuthHeader()},
    })
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
      .then(obj => {
          return setFn(obj.body)
      });
}

function delete_cookie(name) {
  document.cookie = name+'=; Max-Age=-99999999;';
}

export function logout(navigate) {
  window.localStorage.removeItem('token');
  navigate('/sign-in', {replace: true})
}
