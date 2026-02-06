# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.4]

### Changed
- Upgraded to Python 3.14 from 3.11
- Specified explicit permissions for all GitHub Actions workflows per https://github.com/ASFHyP3/actions/

## [0.5.3]

This is a maintenance release that includes various dependency upgrades.

### Fixed
- Upgraded to [Actions v0.20.0](https://github.com/ASFHyP3/actions/releases/tag/v0.20.0) so that Docker image `latest` tag will correspond to the actual version tag. See https://github.com/ASFHyP3/actions/issues/278

## [0.5.2]

### Added
- Add `mypy` to [`static-analysis`](.github/workflows/static-analysis.yml).

## [0.5.1]

### Changed
- The [`static-analysis`](.github/workflows/static-analysis.yml) Github Actions workflow now uses `ruff` rather than `flake8` for linting.

## [0.5.0]

### Added
* `harmony_service` module and Docker file enabling generating browse imagery via a Harmony service.

## [0.4.0]

### Changed
* `create_browse` now takes VV.tif and VH.tif paths as input rather than a granule name

### Removed
* `create_browse` option to download a granule via CMR
* `create_browse` option to upload the output rgb to an S3 bucket

## [0.3.0]

### Changed
* Output GeoTIFFs now have the same projection and pixel size as the input GeoTIFFs
* Scaling of browse images to convert to amplitude first, then scale between 0.14,0.52 for co-pol and 0.05,0.259 for cross pol

### Removed
* Support for deploying as an AWS Lambda application

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
