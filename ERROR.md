Failed to load resource: net::ERR_INTERNET_DISCONNECTED
trueight-api.fly.dev/api/v1/checks/68bed7c8-1d86-4b38-a87e-3571619d5b97:1   Failed to load resource: net::ERR_INTERNET_DISCONNECTED
23-1dca4a946e13ff13.js:1  Failed to poll check status: TypeError: Failed to fetch
    at r.request (295-0c0d9133456b4fb0.js:1:5552)
    at r.getCheckById (295-0c0d9133456b4fb0.js:1:6586)
    at page-ec7e6aefb72c6165.js:1:40375
push.353.window.console.error @ 23-1dca4a946e13ff13.js:1
trueight-api.fly.dev/api/v1/checks/68bed7c8-1d86-4b38-a87e-3571619d5b97:1   Failed to load resource: net::ERR_INTERNET_DISCONNECTED
23-1dca4a946e13ff13.js:1  Failed to poll check status: TypeError: Failed to fetch
    at r.request (295-0c0d9133456b4fb0.js:1:5552)
    at r.getCheckById (295-0c0d9133456b4fb0.js:1:6586)
    at page-ec7e6aefb72c6165.js:1:40375
push.353.window.console.error @ 23-1dca4a946e13ff13.js:1
trueight-api.fly.dev/api/v1/checks/68bed7c8-1d86-4b38-a87e-3571619d5b97:1   Failed to load resource: net::ERR_NETWORK_CHANGED
23-1dca4a946e13ff13.js:1  Failed to poll check status: TypeError: Failed to fetch
    at r.request (295-0c0d9133456b4fb0.js:1:5552)
    at r.getCheckById (295-0c0d9133456b4fb0.js:1:6586)
    at page-ec7e6aefb72c6165.js:1:40375
push.353.window.console.error @ 23-1dca4a946e13ff13.js:1
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Effect triggered: Object
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Exiting early - enabled: false token: false
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Effect triggered: Object
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Exiting early - enabled: false token: true
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Effect triggered: Object
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Exiting early - enabled: false token: false
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Effect triggered: Object
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Exiting early - enabled: false token: true


Errors showed up i nthis run. 

But not i nthis one below? 

[PixelGrid] Generated 1600x2000 canvas: 0.23MB
page-9e7c910cb499fce1.js:1 [PixelGrid] Generated 11 pop shapes
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Effect triggered: {enabled: false, hasToken: false, checkId: '1a4424fe-e872-4e1e-bc03-511051197924'}
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Exiting early - enabled: false token: false
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Effect triggered: {enabled: false, hasToken: true, checkId: '1a4424fe-e872-4e1e-bc03-511051197924'}
page-ec7e6aefb72c6165.js:1 [useCheckProgress] Exiting early - enabled: false token: true


Console from previous check.  No errors in this run. HOWEVER - Nothing was instigated, no pipeline tasks, seemingly, were carried out.  The process was just hanging on "Pending"

