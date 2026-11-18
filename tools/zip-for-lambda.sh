#!/bin/bash
rm -rf ./dist ./lambda.zip

uv export --format requirements-txt --no-emit-project --no-dev -o requirements.txt
uv pip install -r ./requirements.txt --target ./dist \
  --python-platform x86_64-manylinux_2_28 \
  --only-binary=:all: \
  --no-installer-metadata \
  --no-compile-bytecode

cp ./src/*.py ./dist

cd ./dist
zip -r lambda.zip .

mv lambda.zip ../
