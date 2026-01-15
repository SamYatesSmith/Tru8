==> Building image with Depot   
--> build:  (​)
[+] Building 1.5s (9/19)
 => [internal] load build definition from Dockerfile                                                                                                  0.2s
 => => transferring dockerfile: 1.69kB                                                                                                                0.2s 
 => [internal] load metadata for docker.io/library/node:20-alpine                                                                                     0.3s
 => [internal] load .dockerignore                                                                                                                     0.3s
 => => transferring context: 600B                                                                                                                     0.2s 
 => [internal] load build context                                                                                                                     0.6s
 => => transferring context: 297.21kB                                                                                                                 0.6s 
 => [builder  1/10] FROM docker.io/library/node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e7d704537c9d9272f488ac03a370d448                     0.0s 
 => => resolve docker.io/library/node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e7d704537c9d9272f488ac03a370d448                               0.0s 
 => CACHED [builder  2/10] WORKDIR /app                                                                                                               0.0s 
 => [runner 3/7] RUN addgroup --system --gid 1001 nodejs                                                                                              0.1s 
 => [runner 4/7] RUN adduser --system --uid 1001 nextjs                                                                                               0.1s
 => ERROR [builder  3/10] COPY package.json package-lock.json* ./                                                                                     0.0s
------
 > [builder  3/10] COPY package.json package-lock.json* ./:
------
==> Building image
Waiting for depot builder...
Waiting for depot builder...
Waiting for depot builder...
Waiting for depot builder...
==> Building image with Depot   
--> build:  (​)
[+] Building 1.0s (9/19)
 => [internal] load build definition from Dockerfile                                                                                                  0.2s 
 => => transferring dockerfile: 1.69kB                                                                                                                0.2s
 => [internal] load metadata for docker.io/library/node:20-alpine                                                                                     0.2s
 => [internal] load .dockerignore                                                                                                                     0.2s
 => => transferring context: 600B                                                                                                                     0.2s 
 => [internal] load build context                                                                                                                     0.2s
 => => transferring context: 8.29kB                                                                                                                   0.2s 
 => [runner 1/7] FROM docker.io/library/node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e7d704537c9d9272f488ac03a370d448                        0.0s 
 => => resolve docker.io/library/node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e7d704537c9d9272f488ac03a370d448                               0.0s 
 => CACHED [runner 2/7] WORKDIR /app                                                                                                                  0.0s 
 => [runner 3/7] RUN addgroup --system --gid 1001 nodejs                                                                                              0.1s 
 => [runner 4/7] RUN adduser --system --uid 1001 nextjs                                                                                               0.1s
 => ERROR [builder  3/10] COPY package.json package-lock.json* ./                                                                                     0.0s
------
 > [builder  3/10] COPY package.json package-lock.json* ./:
------
Error: failed to fetch an image or build from source: error building: failed to solve: failed to compute cache key: failed to calculate checksum of ref ptu52tlu9yntrlcbk269lfcsi::ygbjgx9cg0zcbmb8z9rrf18mk: "/package.json": not found




