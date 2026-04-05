Key challenges vs a typical Apptainer conversion:

1. Multi-stage build — the Docker file does a frontend Vite build then continues with the same image. 
   Apptainer has no multi-stage concept, so the %post section needs to do it all sequentially.
2. `pn` user — the Dockerfile switches to a non-root `pn` user (from nikolaik/python-nodejs). 
   In Apptainer %post runs as root, and at runtime it runs as the invoking user — so the user-switching logic disappears, but path assumptions (e.g. poetry venv ownership) need adjusting.
3. `PostgreSQL` — in Docker this is a separate sidecar container (mdv_db). In Apptainer/OOD we'll need to decide: 
   - external shared Postgres, or bundle postgresql inside the container and run it as a subprocess. 
   - For OOD per-user instances, an embedded Postgres started by the container's runscript is probably cleanest.
4. Writable paths at runtime — `/app/mdv` (user data), the poetry `.venv`, and any `SQLite/Postgres` data dirs need to be 
   either bind-mounted or overlaid.
