# opera-rtc-s1-browse

A tool for creating OPERA RTC Sentinel-1 browse images for [NASA Worldview](https://worldview.earthdata.nasa.gov).

## Usage
Once installed (see below for details) you can run the tool using the command:
```bash
create_browse OPERA_L2_RTC-S1_T035-073251-IW2_20240113T020816Z_20240113T113128Z_S1A_30_v1.0
```
Where you replace `OPERA_L2_RTC-S1_T035-073251-IW2_20240113T020816Z_20240113T113128Z_S1A_30_v1.0` with the name of OPERA RTC S1 product you want to create a browse image for.

To explore the available options, run:
```bash
create_browse --help
```
These options allow you to specify an AWS S3 bucket path where the browse image will be uploaded.

## Setup
### Installation
1. Ensure that conda is installed on your system (we recommend using [mambaforge](https://github.com/conda-forge/miniforge#mambaforge) to reduce setup times).
2. Download a local version of the `opera-rtc-s1-browse` repository (`git clone git@github.com:ASFHyP3/opera-rtc-s1-browse.git`)
3. In the base directory for this project, call `mamba env create -f environment.yml` to create your Python environment and activate it (`mamba activate opera-rtc-s1-browse`)

To run all commands in sequence use:
```bash
git clone git@github.com:ASFHyP3/opera-rtc-s1-browse.git
cd opera-rtc-s1-browse
mamba env create -f environment.yml
mamba activate opera-rtc-s1-browse
```

### Credentials
To use `create_browse`, you must provide your Earthdata Login credentials via two environment variables (`EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`), or via your `.netrc` file.

If you do not already have an Earthdata account, you can sign up [here](https://urs.earthdata.nasa.gov/home).

If you would like to set up Earthdata Login via your `.netrc` file, check out this [guide](https://harmony.earthdata.nasa.gov/docs#getting-started) to get started.

To use the S3 upload functionality, you will also need to have [AWS credentials configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) that have permission to write to the specified S3 bucket.

## License
`opera-rtc-s1-browse` is licensed under the BSD 2-Clause License. See the LICENSE file for more details.

## Contributing
Contributions to this project are welcome! If you would like to contribute, please submit a pull request on the GitHub repository.

## Contact Us
Want to talk about `opera-rtc-s1-browse`? We would love to hear from you!

Found a bug? Want to request a feature?
[open an issue](https://github.com/ASFHyP3/opera-rtc-s1-browse/issues/new)

General questions? Suggestions? Or just want to talk to the team?
[chat with us on gitter](https://gitter.im/ASFHyP3/community)
