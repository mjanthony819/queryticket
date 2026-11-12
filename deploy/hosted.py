"""Owner-only hosted role preview. Do not use for independent buyer accounts."""
import os,sys,time,secrets,hmac,hashlib,json,base64,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import core
if os.environ.get('QUERYTICKET_TEST_SQLITE')!='1':
 from storage import install
 install(core)
import app
# Only an authenticated single owner can reach these demo role controls.
html=app.ROOT/'static/index.html'
html.write_text(html.read_text().replace('Synthetic lab / local prototype','Private owner demo / test money').replace('This is not multi-user authentication and must not be exposed to the internet.','Private owner access is required. These controls are role previews, not independent buyer accounts.'))
HOST=os.environ.get('QUERYTICKET_HOST') or os.environ['RENDER_EXTERNAL_HOSTNAME'];KEY=os.environ['SESSION_SIGNING_KEY'].encode();PASSWORD_HASH=os.environ['OWNER_PASSWORD_HASH'];failures={};lock=threading.Lock()
os.environ.setdefault('PAYPAL_RETURN_BASE','https://'+HOST)
if len(KEY)<32 or '/' in HOST:raise RuntimeError('Invalid hosted configuration')
def password_ok(password):
 try:
  salt,expected=PASSWORD_HASH.split(':');actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex();return hmac.compare_digest(actual,expected)
 except Exception:return False
def signature(value):return hmac.new(KEY,value.encode(),hashlib.sha256).hexdigest()
class Handler(app.Handler):
 def allowed_host(self):return self.headers.get('Host')==HOST
 def authenticated(self):
  try:
   raw=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x)['qt_session'];value,sig=raw.rsplit('.',1)
   return hmac.compare_digest(signature(value),sig) and 0<int(value.split(':')[0])-time.time()<=28800
  except Exception:return False
 def security(self):
  if not self.allowed_host():self.reply({'error':'Unknown host'},403);return False
  if not self.authenticated():self.reply({'error':'Sign in required'},401);return False
  return True
 def do_GET(self):
  if not self.allowed_host():return self.reply({'error':'Unknown host'},403)
  if self.path=='/health':return self.reply({'status':'ready'})
  if self.path=='/logout':
   self.send_response(303);self.send_header('Location','/');self.send_header('Cache-Control','no-store');self.send_header('Set-Cookie','qt_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0');self.end_headers();return
  if not self.authenticated():
   if self.path!='/' and self.path!='/login':return self.reply({'error':'Sign in required'},401)
   return self.reply('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>QueryTicket private demo</title><main style="max-width:420px;margin:15vh auto;padding:24px;font:18px system-ui"><h1>QueryTicket</h1><p>Private, owner-only synthetic sandbox demo.</p><form method="post" action="/login"><label>Demo password<input style="display:block;width:100%;padding:12px;box-sizing:border-box;margin:16px 0" name="password" type="password" autocomplete="current-password" required maxlength="200"></label><button style="padding:12px 24px">Sign in</button></form><p>No production payments.</p></main>',kind='text/html; charset=utf-8')
  self.headers.replace_header('Host','localhost:8765');return super().do_GET()
 def do_POST(self):
  if not self.allowed_host():return self.reply({'error':'Unknown host'},403)
  if self.headers.get('Origin')!='https://'+HOST:return self.reply({'error':'Invalid origin'},403)
  if self.path=='/login':
   ip=self.client_address[0];now=time.time()
   with lock:
    attempts=[t for t in failures.get(ip,[]) if t>now-900];failures[ip]=attempts
    if len(attempts)>=10:return self.reply({'error':'Too many attempts. Try again later.'},429)
   try:
    n=int(self.headers.get('Content-Length','0'))
    if n>1024:raise ValueError()
    pwd=parse_qs(self.rfile.read(n).decode()).get('password',[''])[0]
   except Exception:return self.reply({'error':'Invalid login'},400)
   if not password_ok(pwd):
    with lock:failures[ip].append(now)
    return self.reply({'error':'Sign-in failed'},401)
   value=str(int(now+28800))+':'+secrets.token_hex(16);cookie=value+'.'+signature(value)
   self.send_response(303);self.send_header('Location','/');self.send_header('Cache-Control','no-store');self.send_header('Set-Cookie','qt_session='+cookie+'; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=28800');self.end_headers();return
  if not self.security():return
  self.headers.replace_header('Host','localhost:8765');return super().do_POST()
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','10000'))),Handler).serve_forever()
