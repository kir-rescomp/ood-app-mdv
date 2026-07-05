# Deploying Multi-Dimensional Viewer (MDV) via OpenOnDemand

<p align="center">
<img src="icon.png" alt="icon" width="400"/>
</p>

# License & Attribution

The MIT license in this repository applies solely to the deployment scripts, configuration files, and documentation 
provided here for running MDV (https://mdv.ndm.ox.ac.uk/) on the BMRC cluster OpenOnDemand service at the University of Oxford. 
MDV itself is not covered by this license. 

All intellectual property rights for MDV remain with the original authors. Please refer to the [original license](https://github.com/Taylor-CCB-Group/MDV/blob/main/LICENSE) 
before using, modifying, or redistributing MDV.

## How a session starts

```mermaid
flowchart LR
    B[Browser] -->|/rnode/host/port/...| R[OOD rnode]
    R -->|strips prefix| P["proxy.py<br/>BIND_PORT"]
    P -->|rewrites asset paths| F["Flask + Gunicorn<br/>BIND_PORT + 1"]
```

On the compute node, inside one Apptainer container:

| Component          | Notes                                                    |
| ------------------ | -------------------------------------------------------- |
| Flask + Gunicorn   | `gevent` worker, serves the app and API                  |
| Vite frontend      | Built at image time into `/app/dist`                     |
| PostgreSQL         | Initialised per session, not a sidecar                   |
| Projects directory | On GPFS, supplied by the user — persists across sessions |

The database is an index rebuilt from the projects directory at startup. The projects
directory is the only thing that has to survive.

## Version handling

The container path lives in an Lmod module, not in the app config. The form offers a
version dropdown; the chosen module is loaded at launch and exports `MDV_SIF`.

```lua
-- MDV/main.lua
local version = "main"
local sif = "/apps/.../MDV/mdv-" .. version .. ".sif"

setenv("MDV_SIF",     sif)
setenv("MDV_VERSION", version)
```

```bash
# template/script.sh.erb
module load <%= context.mdv_module %>
apptainer run ... "${MDV_SIF}"
```

**To add a version:** build a SIF, drop in a `.lua`, add one line to the form dropdown.
Nothing in the launch script changes.

## 

# `template/proxy.py` 


MDV is designed to run as a standalone web server at the root path (`/`), with its Vite-built 
frontend referencing static assets using absolute URLs such as `/flask/assets/catalog.css` and `/flask/js/mdv.js`.

OpenOnDemand's reverse proxy (`rnode`) works by routing requests through a URL of the form `/rnode/<hostname>/<port>/path`
on the OOD server, stripping the `/rnode/<hostname>/<port>` prefix before forwarding to the application. This means 
the application itself always receives requests at the correct path — but the browser does not know about the stripping. 
When the browser loads a page served at `https://ood-server/rnode/host/port/`, it resolves absolute asset paths such as  
`/flask/assets/catalog.css` relative to the OOD server root, not through the rnode proxy. The result is 404 or 500 
errors for all static assets, leaving the application as a blank page.

A secondary complication arises from nested routes. When a user opens a project, the page URL deepens to something 
similar to `/rnode/host/port/project/1/`. Simply converting absolute paths to relative ones (e.g. `flask/assets/catalog.css`)
does not solve the problem here, because the browser would then resolve those relative paths against the current 
sub-path, producing incorrect URLs such as `/rnode/host/port/project/1/flask/assets/catalog.css`.

`proxy.py` solves this by sitting between OOD's rnode proxy and the MDV Flask application. Flask runs on an internal port 
(`BIND_PORT + 1`), invisible to OOD. The proxy listens on `BIND_PORT` (the port OOD knows about) and forwards all requests to 
Flask. For HTML responses specifically, it rewrites every absolute `/flask/` asset reference to a fully-qualified r
node-prefixed path — for example `/flask/assets/catalog.css` becomes `/rnode/<hostname>/<port>/flask/assets/catalog.css`. 
Because these are now absolute URLs that include the full rnode path, the browser routes them correctly through OOD's 
proxy to Flask regardless of the current page depth.

WebSocket connections (used by MDV's socket.io real-time features) are handled separately via a raw socket bridge, 
since HTTP-level proxying cannot perform the WebSocket protocol upgrade.


### Constraints — don't undo these

**Rewrite to the absolute rnode-prefixed path, not a relative one.** See the nested-route
problem above. Relative paths appear to work until someone opens a project.

**Strip `Content-Encoding` on the way out.** Flask gzips responses; `urllib` silently
decompresses them. Forwarding the original `Content-Encoding` header makes the browser
try to gunzip plain bytes. Drop the header and send a fresh `Content-Length`.