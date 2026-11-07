import {createServer} from 'node:http';
import {readFile,stat,realpath} from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {resolve,extname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateBasePath} from '../src/deployment.js';

const defaultRoot=fileURLToPath(new URL('../dist/',import.meta.url));
export function builtBasePath(root=process.env.PREVIEW_ROOT||defaultRoot){
 const html=readFileSync(resolve(root,'index.html'),'utf8');
 const prefix=html.match(/<meta name="site-base" content="([^"]+)">/)?.[1];
 if(!prefix)throw new Error('Build is missing its site-base deployment metadata');
 return validateBasePath(prefix);
}
export function previewUrl(root){return `http://127.0.0.1:${process.env.PORT||4173}${builtBasePath(root)}`;}
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.woff2':'font/woff2','.png':'image/png','.ico':'image/x-icon','.txt':'text/plain; charset=utf-8','.xml':'application/xml'};
export function createPreviewServer({root=process.env.PREVIEW_ROOT||defaultRoot,prefix=builtBasePath(root)}={}){
 const publicRoot=resolve(root),canonicalRoot=realpath(publicRoot);
 async function contained(file){
  const [base,target]=await Promise.all([canonicalRoot,realpath(file)]);
  if(target!==base&&!target.startsWith(base+sep))throw new Error('Outside canonical public build');
  return target;
 }
 return createServer(async(request,response)=>{
  try {
   const path=decodeURIComponent(new URL(request.url,'http://localhost').pathname);
   if(!path.startsWith(prefix))throw new Error('Outside deployment prefix');
   let file=resolve(publicRoot,path.slice(prefix.length));
   if(file!==publicRoot&&!file.startsWith(publicRoot+sep))throw new Error('Outside public build');
   file=await contained(file);
   if((await stat(file)).isDirectory())file=await contained(resolve(file,'index.html'));
   const body=await readFile(file);
   response.writeHead(200,{'content-type':mime[extname(file)]||'application/octet-stream'});response.end(body);
  }catch{
   response.writeHead(404,{'content-type':'text/html; charset=utf-8'});
   const fallback=await contained(resolve(publicRoot,'404.html')).then(file=>readFile(file)).catch(()=> 'Not found');
   response.end(fallback);
  }
 });
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const server=createPreviewServer();server.listen(Number(process.env.PORT||4173),'127.0.0.1');
 for(const signal of ['SIGTERM','SIGINT'])process.once(signal,()=>server.close(()=>process.exit(0)));
}
