#!/bin/bash
set -e

# build
next build
# replace prefix with variable for CDN
sed -i 's:\"/_next/\":`${process.env.CDN_ORIGIN || \"\"}/_next/`:' .next/server/webpack-runtime.js
# remove unneeded build cache
rm -r .next/cache
# compress text/structured files with brotli
find .next/static/ -type f \( \
    -name '*.css' \
    -o -name '*.js' \
    -o -name '*.json' \
    -o -name '*.svg' \
    -o -name '*.ttf' \
    -o -name '*.txt' \
    \) | xargs brotli
