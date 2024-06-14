# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0]

### Added
* A GIBS-compliant metadata XML file is now also created along with the browse GeoTIFF.

### Changed
* Output files are now deleted from disk when running in AWS Lambda

## [0.2.0]

### Added
* `create_browse` can now be deployed as AWS Lambda Function that takes in an OPERA RTC granule name and outputs a
  browse image to an S3 bucket. The function is available in Earthdata Cloud UAT and Earthdata Cloud production.
  ```
  aws lambda invoke \
    --profile <profile> \
    --function-name <function_name> \
    --payload '{ "granule": "OPERA_L2_RTC-S1_T035-073251-IW2_20240113T020816Z_20240113T113128Z_S1A_30_v1.0" }' \
    --cli-binary-format raw-in-base64-out \
    /dev/null
  ```

### Removed
* Support for uploading output files under a specific S3 prefix

## [0.1.0]

### Added
* RTC granule download functionality
* Browse image creation functionality

### Removed
* Unused functionality created during HyP3-Cookiecutter setup
