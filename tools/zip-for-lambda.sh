#!/bin/bash
rm -rf ./dist ./lambda.zip
pip install -r ./requirements.txt --target ./dist
cp ./*.py ./dist

cd ./dist
zip -r lambda.zip .

mv lambda.zip ../
