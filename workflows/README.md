# v2 workflow directory

This folder contains the active ComfyUI Export(API) workflows used by DOBEDUB STUDIO v2.

The current active set was promoted from `Workflow2/`:

- `1-images.json`
- `2-images.json`
- `3-images.json`
- `4-images.json`
- `5-images.json`
- `6-images.json`

Each workflow must have a matching `*.paramconfig.json` file. The paramconfig files map UI controls to the exact node IDs and input fields in the active workflow JSON.

The v2 workflows already include final and segment `SaveVideo` nodes. The server uses those existing nodes and does not add dynamic `SaveVideo` nodes at runtime.
