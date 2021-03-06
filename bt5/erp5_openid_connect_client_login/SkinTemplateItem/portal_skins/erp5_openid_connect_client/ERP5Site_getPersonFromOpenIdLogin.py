from zExceptions import Unauthorized

if REQUEST is not None:
  raise Unauthorized

login = context.ERP5Site_getOpenIdConnectLogin(login)

if login is None or not len(login):
  return None

if len(login) > 1:
  raise ValueError("Duplicated User")

return login[0].getParentValue().getRelativeUrl()
