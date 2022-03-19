
export const checkLogin = async (navigate) => {

  const response = await fetch("/api/hello", {credentials: 'include'});
  const data = await response.json()

  if (response.status == 200) {
    return;
  }
  navigate('/sign-in', {replace: true});
}
