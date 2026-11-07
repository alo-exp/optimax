// Only literal path segments are accepted: no URL normalization, encoded separators,
// traversal, credentials, or query/hash configuration can change the site boundary.
export function validateBasePath(basePath) {
 if(typeof basePath!=='string'||/\s/.test(basePath)||!/^\/(?:[A-Za-z0-9_-]+\/)*$/.test(basePath))throw new Error('Invalid site base path');
 return basePath;
}
export function deploymentUrl(value='https://alo-exp.github.io/optimax/') {
 if(typeof value!=='string'||/\s/.test(value)||!/^https:\/\/[^/?#\\]+(?:\/[A-Za-z0-9_-]+)*\/?$/.test(value))throw new Error('Invalid SITE_URL: expected an HTTPS URL with a safe deployment path');
 let url;
 try{url=new URL(value)}catch{throw new Error('Invalid SITE_URL')}
 if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash)throw new Error('Invalid SITE_URL');
 const basePath=validateBasePath(url.pathname.endsWith('/')?url.pathname:url.pathname+'/');
 return {basePath,url:url.origin+basePath};
}
export function sitePath(path,basePath='/') {
 validateBasePath(basePath);
 if(typeof path!=='string'||/\s/.test(path)||!/^\/(?:[A-Za-z0-9_.~-]+\/)*[A-Za-z0-9_.~-]*(?:#[A-Za-z0-9_-]+)?$/.test(path)||path.split('#')[0].split('/').some(part=>part==='.'||part==='..'))throw new Error('Invalid internal path');
 return basePath+path.slice(1);
}
