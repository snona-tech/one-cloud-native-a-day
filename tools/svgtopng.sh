#!/bin/bash -l

if [ which docker >/dev/null 2>&1 ]; then
  echo "docker is installed"
else
  echo "docker is not installed"
  shopt -s expand_aliases
  alias docker='/mnt/c/Program\ Files/WSL/wslc.exe'
fi

sudo rm -rf tools/landscape tools/png

mkdir tools/png
git clone https://github.com/cncf/landscape.git tools/landscape
rm -rf tools/landscape/.git

sed -i 's/<?xml version="1.0" encoding="utf-16"?>/<?xml version="1.0" encoding="utf-8"?>/g' tools/landscape/hosted_logos/american-express.svg

sed -i '/metadata/,/metadata/d' tools/landscape/hosted_logos/Seldon_idWf-VLClV_10.svg

docker run --rm \
  -v ${PWD}/tools/landscape/hosted_logos:/hosted_logos \
  -v ${PWD}/tools/png:/png \
  -w /hosted_logos \
  ubuntu:24.04 \
  sh -c '
    apt-get update -qq
    apt-get install -y -qq apt-utils > /dev/null
    apt-get install -y -qq librsvg2-bin > /dev/null

    for f in /hosted_logos/*.png; do
      cp "$f" "/png/$(basename "$f" .png).svg.png"
    done

    for f in /hosted_logos/*.svg; do
      [ -f "$f" ] || continue
      name=$(basename "$f" .svg)
      rsvg-convert --unlimited -w 512 -b white --keep-aspect-ratio "$f" -o "/png/${name}.svg.png"
    done
  '

ls -1 tools/landscape/hosted_logos | sed 's/\.[^.]*$//' | sort -u > list_hosted.txt
ls -1 tools/png | sed 's/\.svg\.png$//' | sort -u > list_png.txt
diff list_hosted.txt list_png.txt
rm list_hosted.txt list_png.txt
