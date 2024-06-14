"""
opera-rtc-s1-browse processing
"""

import argparse
import datetime
import os
import tempfile
from pathlib import Path

import boto3
import earthaccess
import numpy as np
from osgeo import gdal


gdal.UseExceptions()
s3 = boto3.client('s3')


def now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def create_metadata_xml(co_pol_path: Path, browse_path: Path) -> Path:
    info = gdal.Info(str(co_pol_path), format='json')
    start_time = datetime.datetime.fromisoformat(info["metadata"][""]["ZERO_DOPPLER_START_TIME"][:-1])
    end_time = datetime.datetime.fromisoformat(info["metadata"][""]["ZERO_DOPPLER_END_TIME"][:-1])
    content = (
        '<ImageryMetadata xmlns="http://www.w3.org/2005/Atom" xmlns:georss="http://www.georss.org/georss/10">\n'
        f'  <ProviderProductId>{browse_path.stem}</ProviderProductId>\n'
        f'  <ProductionDateTime>{now().isoformat(timespec="seconds")}Z</ProductionDateTime>\n'
        f'  <DataStartDateTime>{start_time.isoformat(timespec="seconds")}Z</DataStartDateTime>\n'
        f'  <DataEndDateTime>{end_time.isoformat(timespec="seconds")}Z</DataEndDateTime>\n'
        f'  <DataDay>{start_time.strftime("%Y%m%d")}</DataDay>\n'
        '</ImageryMetadata>\n'
    )
    xml_path = browse_path.with_suffix('.xml')
    xml_path.write_text(content)
    return xml_path


def download_data(granule: str, working_dir: Path) -> tuple[Path, Path]:
    """Download co-pol and cross-pol images for an OPERA S1 RTC granule.

    Args:
        granule: The granule to download data for.
        working_dir: Working directory to store the downloaded files.

    Returns:
        Path to the co-pol and cross-pol images.
    """
    results = earthaccess.search_data(
        short_name='OPERA_L2_RTC-S1_V1',
        granule_ur=granule,
    )
    if not results:
        raise ValueError(f'Granule {granule} not found in collection OPERA_L2_RTC-S1_V1')

    links = [link for link in results[0].data_links() if link.endswith('VV.tif') or link.endswith('VH.tif')]
    if len(links) != 2:
        raise ValueError(f'VV+VH links not found for granule {granule}')

    paths = earthaccess.download(links, str(working_dir))

    cross_pol_path, co_pol_path = [Path(path) for path in sorted(paths)]
    return co_pol_path, cross_pol_path


def normalize_image_array(
    input_array: np.ndarray, vmin: float | None = None, vmax: float | None = None
) -> np.ndarray:
    """Function to normalize a browse image band.
    Modified from OPERA-ADT/RTC.

    Args:
        input_array: The array to normalize.
        vmin: The minimum value to normalize to.
        vmax: The maximum value to normalize to.

    Returns
        The normalized array.
    """
    input_array = input_array.astype(float)

    if vmin is None:
        vmin = np.nanpercentile(input_array, 3)

    if vmax is None:
        vmax = np.nanpercentile(input_array, 97)

    # gamma correction: 0.5
    is_not_negative = input_array - vmin >= 0
    is_negative = input_array - vmin < 0
    input_array[is_not_negative] = np.sqrt((input_array[is_not_negative] - vmin) / (vmax - vmin))
    input_array[is_negative] = 0
    input_array[np.isnan(input_array)] = 0
    normalized_array = np.round(np.clip(input_array, 0, 1) * 255).astype(np.uint8)
    return normalized_array


def create_browse_array(co_pol_array: np.ndarray, cross_pol_array: np.ndarray) -> np.ndarray:
    """Create a browse image array for an OPERA S1 RTC granule.
    Bands are normalized and follow the format: [co-pol, cross-pol, co-pol, no-data].

    Args:
        co_pol_array: Co-pol image array.
        cross_pol_array: Cross-pol image array.

    Returns:
       Browse image array.
    """
    co_pol_nodata = ~np.isnan(co_pol_array)
    co_pol = normalize_image_array(co_pol_array, 0, 0.15)

    cross_pol_nodata = ~np.isnan(cross_pol_array)
    cross_pol = normalize_image_array(cross_pol_array, 0, 0.025)

    no_data = (np.logical_and(co_pol_nodata, cross_pol_nodata) * 255).astype(np.uint8)
    browse_image = np.stack([co_pol, cross_pol, co_pol, no_data], axis=-1)
    return browse_image


def create_browse_image(co_pol_path: Path, cross_pol_path: Path, working_dir: Path) -> Path:
    """Create a browse image for an OPERA S1 RTC granule meeting GIBS requirements.

    Args:
        co_pol_path: Path to the co-pol image.
        cross_pol_path: Path to the cross-pol image.
        working_dir: Working directory to store intermediate files.

    Returns:
        Path to the created browse image.
    """
    co_pol_ds = gdal.Open(str(co_pol_path))
    co_pol = co_pol_ds.GetRasterBand(1).ReadAsArray()

    cross_pol_ds = gdal.Open(str(cross_pol_path))
    cross_pol = cross_pol_ds.GetRasterBand(1).ReadAsArray()

    browse_array = create_browse_array(co_pol, cross_pol)

    tmp_browse_path = working_dir / 'tmp.tif'
    driver = gdal.GetDriverByName('GTiff')
    browse_ds = driver.Create(str(tmp_browse_path), browse_array.shape[1], browse_array.shape[0], 4, gdal.GDT_Byte)
    browse_ds.SetGeoTransform(co_pol_ds.GetGeoTransform())
    browse_ds.SetProjection(co_pol_ds.GetProjection())
    for i in range(4):
        browse_ds.GetRasterBand(i + 1).WriteArray(browse_array[:, :, i])

    co_pol_ds = None
    cross_pol_ds = None
    browse_ds = None

    browse_path = working_dir / f'{co_pol_path.stem[:-3]}_rgb.tif'
    gdal.Warp(
        browse_path,
        tmp_browse_path,
        dstSRS='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs',
        xRes=2.74658203125e-4,
        yRes=2.74658203125e-4,
        format='GTiff',
        creationOptions=['COMPRESS=LZW', 'TILED=YES'],
    )
    tmp_browse_path.unlink()
    return browse_path


def create_browse_and_upload(
    granule: str,
    bucket: str = None,
    working_dir: Path | None = None,
) -> None:
    """Create browse images for an OPERA S1 RTC granule.

    Args:
        granule: The granule to create browse images for.
        bucket: AWS S3 bucket for upload the final product(s).
        working_dir: Working directory to store intermediate files.
    """
    if working_dir is None:
        working_dir = Path.cwd()

    co_pol_path, cross_pol_path = download_data(granule, working_dir)
    browse_path = create_browse_image(co_pol_path, cross_pol_path, working_dir)
    metadata_path = create_metadata_xml(co_pol_path, browse_path)
    co_pol_path.unlink()
    cross_pol_path.unlink()

    if bucket:
        s3.upload_file(browse_path, bucket, browse_path.name)
        s3.upload_file(metadata_path, bucket, browse_path.name)


def lambda_handler(event, context):
    with tempfile.TemporaryDirectory() as temp_dir:
        create_browse_and_upload(event['granule'], os.environ['BUCKET'], working_dir=Path(temp_dir))


def main():
    """opera_rtc_s1_browse entrypoint

    Example:
        create_browse OPERA_L2_RTC-S1_T035-073251-IW2_20240113T020816Z_20240113T113128Z_S1A_30_v1.0
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--bucket', help='AWS S3 bucket for uploading the final product')
    parser.add_argument('granule', type=str, help='OPERA S1 RTC granule to create a browse image for.')
    args = parser.parse_args()

    create_browse_and_upload(**args.__dict__)


if __name__ == '__main__':
    main()
