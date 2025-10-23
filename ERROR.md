Unhandled Runtime Error
Error: Hydration failed because the initial UI does not match what was rendered on the server.
See more info here: https://nextjs.org/docs/messages/react-hydration-error

Expected server HTML to contain a matching <div> in <a>.


<a>
^^^
  <div>
  ^^^^^
Call Stack
React
throwOnHydrationMismatch
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (6981:1)
tryToClaimNextHydratableInstance
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (7016:1)
updateHostComponent$1
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (16621:1)
beginWork$1
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (18503:1)
HTMLUnknownElement.callCallback
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (20565:1)
Object.invokeGuardedCallbackImpl
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (20614:1)
invokeGuardedCallback
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (20689:1)
beginWork
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (26949:1)
performUnitOfWork
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (25748:1)
workLoopConcurrent
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (25734:1)
renderRootConcurrent
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (25690:1)
performConcurrentWorkOnRoot
node_modules\next\dist\compiled\react-dom\cjs\react-dom.development.js (24504:1)
workLoop
node_modules\next\dist\compiled\scheduler\cjs\scheduler.development.js (256:1)
flushWork
node_modules\next\dist\compiled\scheduler\cjs\scheduler.development.js (225:1)
MessagePort.performWorkUntilDeadline
node_modules\next\dist\compiled\scheduler\cjs\scheduler.development.js (534:1)