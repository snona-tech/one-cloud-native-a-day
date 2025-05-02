#!/bin/bash
sudo rm -rf tools/landscape tools/png

mkdir tools/png
git clone https://github.com/cncf/landscape.git tools/landscape
rm -rf tools/landscape/.git

sed -i 's/<?xml version="1.0" encoding="utf-16"?>/<?xml version="1.0" encoding="utf-8"?>/g' tools/landscape/hosted_logos/american-express.svg

sed -i '/metadata/,/metadata/d' tools/landscape/hosted_logos/Seldon_idWf-VLClV_10.svg

special_filename=(
  'banco-de-cre'$'\314\201''dito-bcp.svg'
  'banco-de-cr'$'\303\251''dito-bcp.svg'
  ''$'\303\246''nix.svg'
)

tmp_filename=tmp
count=1

for filename in "${special_filename[@]}"; do
  mv tools/landscape/hosted_logos/${filename} tools/landscape/hosted_logos/${tmp_filename}${count}
  ((count++))
done

docker run --rm -it \
  -v ${PWD}/tools/landscape/hosted_logos:/hosted_logos \
  -v ${PWD}/tools/png:/png \
  vulhub/librsvg:2.50.7 \
  bash -c 'apt-get update;apt-get install -y pngquant;ls hosted_logos/ | xargs -I{} -P 3 -n 1 rsvg-convert hosted_logos/{} -o png/{}.png;pngquant --ext .png --force --speed 1 png/*.png'

count=1

for filename in "${special_filename[@]}"; do
  mv tools/png/${tmp_filename}${count}.png tools/png/${filename}.png
  ((count++))
done

echo "SVG 数：$(ls tools/landscape/hosted_logos | wc -l)"
echo "PNG 数：$(ls tools/png | wc -l)"
