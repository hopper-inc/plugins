#!/bin/bash
set -e
cp -R "$(dirname "$0")/../_fixtures/livekit/." .
git init -q
git add -A
git -c user.email=dev@example.com -c user.name=Dev commit -qm "voice agent"

