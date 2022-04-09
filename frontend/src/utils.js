
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
  navigate(`/sign-in?redirect=${window.location.pathname}`, {replace: true});
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
