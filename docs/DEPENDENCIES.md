# Dependencies and distribution

## Packaging audit (2026-10-11)

EventMan is distributed as a Git/source checkout and a locally built Docker image.
There is no Python package metadata, wheel/sdist build, console entry point,
release pipeline or published-image configuration in this repository. Run the
server from the checkout root: the static fallback uses the relative
`angular_app` directory. Installing with `pip install .` is not supported.

Previously, installation instructions listed unbounded pip commands and Docker
mixed Debian Python packages with a system-wide pip install. The source tree
also carried 140 third-party files (16,326,272 bytes) despite the current
frontend never loading them. They were included by Docker's broad `COPY .`.

Python dependencies now live in requirement files, and Docker installs from the
same files using a separate wheel-building stage. Its explicit copy list includes
only the active frontend and server resources. MongoDB remains an external
service, provided by its own image in Compose.

## Dependency inventory

| Component | Owner / source | How it is supplied |
| --- | --- | --- |
| Server: Tornado, PyMongo, python-dateutil | External Python projects | `requirements.txt`, installed by pip |
| Eventbrite SDK | External Python project | Optional `requirements-eventbrite.txt`; also installed in Docker |
| Scanner: pyserial, requests | External Python projects | Optional host-only `requirements-scanner.txt` |
| Label printing: pycups, Pillow | External Python projects | Optional `requirements-printing.txt`; also installed in Docker |
| CUPS libraries and development headers | Operating system | Host package manager; Docker headers/compiler stay in build stage |
| Text and Code 39 barcode fonts | External font projects | Installed outside the checkout and selected by absolute path |
| MongoDB | External server | Separate host service or `mongo:7.0` Compose image |
| Modern HTML, CSS and ES module client | EventMan | First-party source, no npm/CDN/runtime dependencies |
| `monco.py`, `tools/monco.py` | EventMan / RaspiBO | Project-owned MongoDB helper; both copies retained |

`bson` comes from PyMongo. Do not install the unrelated standalone `bson` package.
Likewise, the scanner imports `serial` from **pyserial**, not the package named
`serial`. Optional requirement files include the core requirements, so they can
also be installed independently into a fresh environment.

Monco shares the project's author, copyright and license, and its Git history
contains project-specific changes. It is retained as first-party code rather
than replaced with an unverified similarly named package. The duplicate under
`tools/` allows the existing directly executed utilities to import it.

## Removed bundled projects

The inactive browser dependencies were moved out of the working tree:
AngularJS (including animation, resource, routing and touch modules), Angular
Translate, Angular UI Router, Angular WebSocket, Angular Strap, UI Bootstrap,
Angular File Upload, Angular Formly and Bootstrap templates, api-check, jQuery,
Lodash, Bootstrap (including Glyphicons), Font Awesome, textAngular/rangy,
AngularJS Toaster, nya-bs-select, easyFormGenerator, json2csv, Animate.css,
Normalize.css, Dropzone styles and Angular Loading Bar styles. Their minified
copies, source maps, Font Awesome sources and fonts were also removed.

The Ubuntu Condensed and Free 3 of 9 fonts previously bundled with the label
trigger were moved out too. Retired first-party Angular sources and styles are
retained as reference; they cannot run without restoring their old dependencies.
The Grunt translation task belongs to that retired implementation and is not a
current build requirement. No unused libraries were replaced with CDN loads or
submodules.

For this migration, the exact bytes were preserved outside the repository in
`/tmp/eventman-third-party-20261011-qmeycb_2`, with relative paths and SHA-256
checksums in `manifest.json`. This is a temporary local archive, not a required
runtime directory or durable distribution channel. The durable recovery source
is Git revision `d9dd5de`, which predates this removal. To recover old assets
outside the checkout:

```sh
mkdir -p /tmp/eventman-legacy
git archive d9dd5de static angular_app data/triggers-available | tar -x -C /tmp/eventman-legacy
```

Retain upstream license notices if redistributing recovered assets; the EventMan
Apache license does not relicense third-party code or fonts. Git history still
contains the old assets; this change does not rewrite repository history.

## Label printing

Install `requirements-printing.txt` in the environment used to execute triggers.
On Debian/Ubuntu, building pycups requires `libcups2-dev`, a C compiler and Python
development headers. CUPS must be configured separately.

Install appropriately licensed text and Code 39 barcode fonts through the host's
package manager or their upstream distributions, outside this repository. Set
these variables in the server/trigger process environment:

```sh
export EVENTMAN_LABEL_TEXT_FONT=/absolute/external/path/to/text-font.ttf
export EVENTMAN_LABEL_BARCODE_FONT=/absolute/external/path/to/code39-font.ttf
```

The barcode font must use `*` for Code 39 start/stop markers. Existing deployments
can move their current fonts to an external directory and point to those same
files. Docker deployments need read-only font mounts and the variables set to
container paths. Missing or invalid paths produce an explicit configuration
error. The trigger now accepts Python 3 text and uses Pillow's supported
`textbbox` API, replacing the removed `textsize` API.

Label images are created atomically in the system temporary directory with
owner-only permissions (0600 on POSIX). `KEEP_IMG=True` in `print_label.py`
preserves completed images named `eventman_print_label_*.png` after submission,
including submission failures, for troubleshooting. They contain attendee data;
operators should remove retained images when no longer needed. Set `KEEP_IMG=False`
to remove images when submission finishes or fails. Generation failures remove
partial files in either mode. File handles are closed in all these paths.

## Reproducibility and remaining limits

Requirement files specify bounded compatibility ranges, not a fully resolved,
hashed dependency lock. Transitive versions are selected by pip at installation
or image-build time. The Python and MongoDB image tags permit patch updates.
For an immutable production release, resolve and archive a tested dependency
lock with hashes and pin container image digests for the chosen architecture.

This work does not introduce a wheel: the current filesystem-relative static
and writable data layout needs a separate packaging design before `pip install .`
can provide a reliable installation. It also does not modernize the legacy
`docker-tools` scripts, which still use old container names and `mongo` commands.

## Migration validation

- All 140 moved files matched the external archive's SHA-256 manifest; none
  remain at their old source paths.
- Fresh Python 3.14 virtual environment: core, Eventbrite and scanner dependency
  installation, imports and `pip check` passed. Host pycups compilation requires
  the documented CUPS headers, which are not installed on this host.
- Docker image `eventman-dependency-check:local` built on Python 3.12, including
  pycups compiled with CUPS headers in the build stage.
- Local and container HTTP smoke checks fetched the application shell and both
  active assets; removed AngularJS and Bootstrap asset requests returned 404.
- Container checks verified dependency imports, the non-root user, writable data,
  absent compiler and absence of bundled fonts/legacy frontend libraries.
- Label PNG generation passed using the externally archived Ubuntu and Code 39
  fonts, Unicode/bytes input and invalid-font configuration checks. No physical
  printing or scanner actions were performed.
- Python compilation, JavaScript syntax, Compose configuration and
  `git diff --check` passed. Database integration and browser visual acceptance
  were not exercised by these packaging checks.
