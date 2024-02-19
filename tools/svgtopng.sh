#!/bin/bash
sudo rm -rf tools/landscape tools/png

mkdir tools/png
git clone https://github.com/cncf/landscape.git tools/landscape
rm -rf tools/landscape/.git

sed -i 's/<?xml version="1.0" encoding="utf-16"?>/<?xml version="1.0" encoding="utf-8"?>/g' tools/landscape/hosted_logos/american-express.svg

docker run --rm -it \
  -v ${PWD}/tools/landscape/hosted_logos:/hosted_logos \
  -v ${PWD}/tools/png:/png \
  vulhub/librsvg:2.50.7 \
  bash -c 'ls hosted_logos/ | xargs -I{} -P 3 -n 1 rsvg-convert hosted_logos/{} -o png/{}.png'

echo "SVG 数：$(ls tools/landscape/hosted_logos | wc -l)"
echo "PNG 数：$(ls tools/png | wc -l)"