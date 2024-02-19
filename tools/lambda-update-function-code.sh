#!/bin/bash
export AWS_PAGER=""
aws lambda update-function-code --function-name one-cloud-native-a-day --zip-file fileb://lambda.zip
