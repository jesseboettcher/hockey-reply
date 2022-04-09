
export const checkLogin = async (navigate) => {

  const response = await fetch("/api/hello", {credentials: 'include'});
  const data = await response.json();

  if (response.status == 200) {
    return data;
  }
  navigate(`/sign-in?redirect=${window.location.pathname}`, {replace: true});
  return {}
}

export function getData(url, setFn) {
    fetch(url, {credentials: 'include'})
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
      .then(obj => {
          return setFn(obj.body)
      });
}

function delete_cookie(name) {
  document.cookie = name+'=; Max-Age=-99999999;';
}

export function logout(navigate) {
  delete_cookie('user');
  navigate('/sign-in', {replace: true})
}
