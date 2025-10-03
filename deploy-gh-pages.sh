#!/bin/bash

uv run mkdocs gh-deploy --force

# We need to add this file to enable male-cns.janelia.org host the github.io site.
echo "male-cns.janelia.org" > CNAME
git add CNAME
git commit -m 'add CNAME'
git push origin gh-pages
