import argparse
from pathlib import Path

import numpy as np
from osgeo import gdal


gdal.UseExceptions()


def normalize_image_array(input_array: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """Function to normalize array values to a byte value between 0 and 255

    Args:
        input_array: The array to normalize.
        vmin: The minimum value to normalize to (mapped to 0).
        vmax: The maximum value to normalize to (mapped to 255).

    Returns:
        The normalized array.
    """
    input_array = input_array.astype(float)
    scaled_array = (input_array - vmin) / (vmax - vmin)
    scaled_array[np.isnan(input_array)] = 0
    normalized_array = np.round(np.clip(scaled_array, 0, 1) * 255).astype(np.uint8)
    return normalized_array


def create_browse_array(co_pol_array: np.ndarray, cross_pol_array: np.ndarray) -> np.ndarray:
    """Create a browse image array for an OPERA S1 RTC granule.
    Input arrays are converted to amplitude, normalized, and returned as [co-pol, cross-pol, co-pol, no-data].

    Args:
        co_pol_array: Co-pol image array.
        cross_pol_array: Cross-pol image array.

    Returns:
       Browse image array.
    """
    co_pol_range = [0.14, 0.52]
    co_pol_nodata = ~np.isnan(co_pol_array)
    co_pol_amplitude = np.sqrt(co_pol_array)
    co_pol = normalize_image_array(co_pol_amplitude, *co_pol_range)

    cross_pol_range = [0.05, 0.259]
    cross_pol_nodata = ~np.isnan(cross_pol_array)
    cross_pol_amplitude = np.sqrt(cross_pol_array)
    cross_pol = normalize_image_array(cross_pol_amplitude, *cross_pol_range)

    no_data = (np.logical_and(co_pol_nodata, cross_pol_nodata) * 255).astype(np.uint8)
    browse_image = np.stack([co_pol, cross_pol, co_pol, no_data], axis=-1)
    return browse_image


def create_browse_image(co_pol_path: Path, cross_pol_path: Path, working_dir: Path) -> Path:
    """Create an RGB browse image for an OPERA S1 RTC granule

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

    browse_path = working_dir / f'{co_pol_path.stem[:-3]}_rgb.tif'
    driver = gdal.GetDriverByName('GTiff')
    browse_ds = driver.Create(
        utf8_path=str(browse_path),
        xsize=browse_array.shape[1],
        ysize=browse_array.shape[0],
        bands=4,
        eType=gdal.GDT_Byte,
        options={'COMPRESS': 'LZW', 'TILED': 'YES'},
    )
    browse_ds.SetGeoTransform(co_pol_ds.GetGeoTransform())
    browse_ds.SetProjection(co_pol_ds.GetProjection())
    for i in range(4):
        browse_ds.GetRasterBand(i + 1).WriteArray(browse_array[:, :, i])

    co_pol_ds = None
    cross_pol_ds = None
    browse_ds = None

    return browse_path


def main():
    """create_browse entrypoint

    Example:
        create_browse foo_VV.tif foo_VH.tif
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('co_pol_path', type=Path, help='Path to the co-polarized (VV) image')
    parser.add_argument('cross_pol_path', type=Path, help='Path to the cross-polarized (VH) image')
    args = parser.parse_args()

    create_browse_image(args.co_pol_path, args.cross_pol_path, Path())


if __name__ == '__main__':
    main()
