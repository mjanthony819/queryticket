from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import json,os,secrets,urllib.error
import core
ROOT=Path(__file__).parent; DB=os.environ.get('QUERYTICKET_DB',str(ROOT/'queryticket.sqlite'));TOKEN=secrets.token_urlsafe(32);core.init(DB)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def reply(self,obj,status=200,kind='application/json'):
  data=obj.encode() if isinstance(obj,str) else json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'");self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.headers.get('Host') not in ('localhost:8765','127.0.0.1:8765'):return self.reply({'error':'Localhost only'},403)
  p=self.path.split('?')[0]
  if p=='/api/state':
   with core.connect(DB) as c:items=[core.public_row(x) for x in c.execute('SELECT * FROM reports ORDER BY created DESC')]
   return self.reply({'token':TOKEN,'catalog':core.CATALOG,'reports':items,'sandbox_configured':bool(os.environ.get('PAYPAL_SANDBOX_CLIENT_ID') and os.environ.get('PAYPAL_SANDBOX_SECRET')),'ai_configured':bool(os.environ.get('GROQ_API_KEY'))})
  if p.startswith('/api/download/'):
   try:return self.reply(core.delivery(DB,p.rsplit('/',1)[1]))
   except ValueError as e:return self.reply({'error':str(e)},403)
  if p=='/api/ai-evidence':
   f=ROOT/'docs/ai-evaluation.json'
   return self.reply(json.loads(f.read_text()) if f.exists() else {'error':'No recorded live evaluation exists'},200 if f.exists() else 404)
  if p=='/':return self.reply((ROOT/'static/index.html').read_text(),kind='text/html; charset=utf-8')
  if p in ('/app.js','/style.css'):return self.reply((ROOT/'static'/p[1:]).read_text(),kind='text/javascript' if p.endswith('.js') else 'text/css')
  self.reply({'error':'Not found'},404)
 def do_POST(self):
  if self.headers.get('Host') not in ('localhost:8765','127.0.0.1:8765'):return self.reply({'error':'Localhost only'},403)
  if self.headers.get('X-QueryTicket-Token')!=TOKEN:return self.reply({'error':'Reload this local app before making changes.'},403)
  n=int(self.headers.get('Content-Length',0))
  if n>4096:return self.reply({'error':'Request too large'},413)
  try:
   body=json.loads(self.rfile.read(n));p=self.path
   if p=='/api/query':result=core.create_report(DB,body.get('question'),body.get('mapper','sample'))
   elif p=='/api/action':result=core.transition(DB,body['id'],body['action'])
   elif p=='/api/sandbox/create':result=core.create_sandbox_order(DB,body['id'])
   elif p=='/api/sandbox/capture':result=core.capture_sandbox(DB,body['id'])
   else:return self.reply({'error':'Not found'},404)
   self.reply(result)
  except urllib.error.HTTPError as e:self.reply({'error':f'Provider returned HTTP {e.code}. No success assumed. The report stays locked unless capture is verified.'},502)
  except (ValueError,KeyError,TypeError) as e:self.reply({'error':str(e)},400)
  except Exception:self.reply({'error':'Connection or processing failed. No success assumed. Check local logs/configuration; no secret is shown.'},502)
if __name__=='__main__':
 print('QueryTicket: http://localhost:8765 (local demo only)');ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
