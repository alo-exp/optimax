# Website deployment

The Optimax website is deployed through GitHub Pages at **https://alo-exp.github.io/optimax/**. OpenAI Sites was used for the initial preview; GitHub Pages is the intended production host.

## Build and publish

The static source is in `site/`. From that directory, run:

```sh
npm ci
npm test
npm run build
```

The default build targets the GitHub project URL, including its `/optimax/` path. `SITE_URL` selects another HTTPS deployment root, such as `https://optimax.alolabs.dev/` when the custom domain is ready. The public output remains in `site/dist/`; the URL prefix does not create another output subdirectory.

The repository's Pages source is GitHub Actions. `.github/workflows/pages.yml` runs on changes to the site/workflow on `main`, or a manual dispatch. It installs locked dependencies, runs the tests, builds using the actual Pages base URL, uploads only `site/dist`, and deploys after the build succeeds. The upload has one-day retention for its deployment consumer. Production deployments are serialized without cancelling active runs. Only the deploy job receives Pages write and OIDC permissions, and deployment is restricted to `main` and the `github-pages` environment.

## Acceptance and domains

Qualify generated links, assets, metadata, search fetch/navigation, deep article anchors and the styled 404 in both project-path and root-domain builds. The workflow has automated semantic checks for permissions, dependencies and artifact handling. Live acceptance additionally checks the actual GitHub Pages responses and deployed content; a successful upload alone is insufficient.

The custom hostname `optimax.alolabs.dev` is a separate pending cutover. Its eventual CNAME target is `alo-exp.github.io`, not the earlier Sites target. Configure and verify the GitHub Pages domain and DNS together when ready; attaching a custom domain redirects the default `github.io` address. Private credentials, project learning and source/configuration directories must never be included in the published static artifact.
