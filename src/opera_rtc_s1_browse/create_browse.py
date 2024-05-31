"""
opera-rtc-s1-browse processing
"""
import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple

import asf_search
import morecantile
import numpy as np
from hyp3lib.aws import upload_file_to_s3
from osgeo import gdal
from rio_tiler.io import Reader

from opera_rtc_s1_browse.auth import get_earthdata_credentials


log = logging.getLogger(__name__)
gdal.UseExceptions()


def download_data(granule: str, working_dir: Path) -> Tuple[Path, Path]:
    """Download co-pol and cross-pol images for an OPERA S1 RTC granule.

    Args:
        granule: The granule to download data for.
        working_dir: Working directory to store the downloaded files.

    Returns:
        Path to the co-pol and cross-pol images.
    """
    result = asf_search.granule_search([granule])[0]
    urls = result.properties['additionalUrls']
    urls.append(result.properties['url'])

    co_pol = [x for x in urls if 'VV' in x]
    if not co_pol:
        raise ValueError('No co-pol found in granule.')
    co_pol = co_pol[0]

    cross_pol = [x for x in urls if 'VH' in x]
    if not cross_pol:
        raise ValueError('No cross-pol found in granule.')
    cross_pol = cross_pol[0]

    co_pol_path = working_dir / Path(co_pol).name
    cross_pol_path = working_dir / Path(cross_pol).name
    if co_pol_path.exists() and cross_pol_path.exists():
        return co_pol_path, cross_pol_path

    username, password = get_earthdata_credentials()
    session = asf_search.ASFSession().auth_with_creds(username, password)
    asf_search.download_urls(urls=[co_pol, cross_pol], path=working_dir, session=session)
    return co_pol_path, cross_pol_path


def normalize_image_array(
    input_array: np.ndarray, vmin: Optional[float] = None, vmax: Optional[float] = None
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
    co_pol = normalize_image_array(co_pol_array, 0.02, 0.3)

    cross_pol_nodata = ~np.isnan(cross_pol_array)
    cross_pol = normalize_image_array(cross_pol_array, 0.003, 0.08)

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


def tile_browse(browse_path: Path, zoom_level: int = 8):
    """Tile a browse image to fit with WebMercator TileMatrixSet

    Args:
        browse_path: Path to the browse image.
        zoom_level: The zoom level to tile the image to.

    Returns:
        List of paths to the tiled browse images.
    """
    if zoom_level > 11:
        raise ValueError('Zoom level must be less than or equal to 11.')

    dir = browse_path.parent
    base_name = browse_path.with_suffix('').name
    tms = morecantile.tms.get('WGS1984Quad')
    
    tilesize = 256 * (2**(11-zoom_level))
    tile_paths = []
    with Reader(browse_path, tms=tms) as browse:
        tile_covers = list(tms.tiles(*browse.geographic_bounds, zooms=zoom_level))
        for tile_cover in tile_covers:
            tile = browse.tile(tile_cover.x, tile_cover.y, tile_cover.z, tilesize=tilesize)
            tile_path = dir / f'{base_name}_wgs1984quad_x{tile_cover.x}y{tile_cover.y}.tif'
            with open(tile_path, 'wb') as f:
                f.write(tile.render(img_format='GTiff', add_mask=True, compress='DEFLATE'))
            tile_paths.append(tile_path)

    return tile_paths


def create_browse_and_upload(
    granule: str,
    bucket: str = None,
    bucket_prefix: str = '',
    working_dir: Optional[Path] = None,
) -> None:
    """Create browse images for an OPERA S1 RTC granule.

    Args:
        granule: The granule to create browse images for.
        bucket: AWS S3 bucket for upload the final product(s).
        bucket_prefix: Add a bucket prefix to product(s).
        working_dir: Working directory to store intermediate files.
    """
    if working_dir is None:
        working_dir = Path.cwd()

    co_pol_path, cross_pol_path = download_data(granule, working_dir)
    browse_path = create_browse_image(co_pol_path, cross_pol_path, working_dir)
    tile_browse(browse_path)
    # co_pol_path.unlink()
    # cross_pol_path.unlink()

    if bucket:
        upload_file_to_s3(browse_path, bucket, bucket_prefix)


def main():
    """opera_rtc_s1_browse entrypoint

    Example:
        create_browse OPERA_L2_RTC-S1_T035-073251-IW2_20240113T020816Z_20240113T113128Z_S1A_30_v1.0
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--bucket', help='AWS S3 bucket for uploading the final product')
    parser.add_argument('--bucket-prefix', default='', help='Add a bucket prefix for product')
    parser.add_argument('granule', type=str, help='OPERA S1 RTC granule to create a browse image for.')
    args = parser.parse_args()

    create_browse_and_upload(**args.__dict__)


if __name__ == '__main__':
    main()
