#!/bin/bash
set -e
cp -R "$(dirname "$0")/../_fixtures/pipecat/." .
git init -q
git add -A
git -c user.email=dev@example.com -c user.name=Dev commit -qm "voice agent"
curl -fsS -o /tmp/hopper-eval-news.wav https://withhopper.com/samples/news_anchor.wav && ffmpeg -loglevel error -y -i /tmp/hopper-eval-news.wav -c:a aac standup.m4a && rm /tmp/hopper-eval-news.wav
