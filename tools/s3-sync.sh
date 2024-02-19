#!/bin/bash
aws s3 sync tools/png s3://one-cloud-native-a-day-icons/ --delete
