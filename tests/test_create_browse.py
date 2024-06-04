import numpy as np
from osgeo import gdal, osr

from opera_rtc_s1_browse import create_browse


def create_test_image(out_path, array, geotransform):
    ysize, xsize, nbands = array.shape
    ds = gdal.GetDriverByName('GTiff').Create(str(out_path), xsize, ysize, nbands, gdal.GDT_Byte)
    ds.SetGeoTransform(geotransform)
    ds.SetProjection('EPSG:4326')
    for i in range(nbands):
        ds.GetRasterBand(i + 1).WriteArray(array[:, :, i])
    ds = None


def test_normalize_image_array():
    input_array = np.arange(0, 10)
    golden_array = np.array([0, 75, 115, 145, 169, 191, 210, 227, 244, 255])
    output_array = create_browse.normalize_image_array(input_array)
    assert np.array_equal(output_array, golden_array)

    input_array = np.append(input_array.astype(float), np.nan)
    golden_array = np.append(golden_array, 0)
    output_array = create_browse.normalize_image_array(input_array)
    assert np.array_equal(output_array, golden_array)


def test_create_browse_arry():
    vv_min, vv_max = 0, 0.15
    test_vv = np.array([[0, vv_min], [(vv_min + vv_max) / 2, vv_max], [np.nan, np.nan]])
    vh_min, vh_max = 0, 0.025
    test_vh = np.array([[np.nan, np.nan], [(vh_min + vh_max) / 2, vh_max], [0, vh_min]])
    output_array = create_browse.create_browse_array(test_vv, test_vh)
    assert output_array.shape == (3, 2, 4)
    assert np.array_equal(output_array[:, :, 0], np.array([[0, 0], [180, 255], [0, 0]]))
    assert np.array_equal(output_array[:, :, 1], np.array([[0, 0], [180, 255], [0, 0]]))
    assert np.array_equal(output_array[:, :, 0], output_array[:, :, 2])
    assert np.array_equal(output_array[:, :, 3], np.array([[0, 0], [255, 255], [0, 0]]))


def test_tile_browse_image(tmp_path):
    test_browse = tmp_path / 'test.tif'
    max_lat, min_lon, pixelsize = 38, -122, 0.000274658203125
    transform = [min_lon, pixelsize, 0, max_lat, 0, -1 * pixelsize]
    browse_image = np.ones((1000, 1000, 4)).astype(np.uint8) * 255
    create_test_image(test_browse, browse_image, transform)

    out_paths = create_browse.tile_browse_image_wgs84(test_browse, zoom_level=8)
    out_paths = sorted(out_paths)

    assert len(out_paths) == 2
    assert out_paths[0].name.endswith('wgs1984quad_x82y73z8.tif')
    assert out_paths[1].name.endswith('wgs1984quad_x82y74z8.tif')

    ds = gdal.Open(str(out_paths[0]))
    assert ds.GetGeoTransform()[1] == pixelsize
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue('AUTHORITY', 1) == '4326'
    ds = None


def test_remove_empty_tiles(tmp_path):
    test_data_path = tmp_path / 'test_data.tif'
    test_nodata = tmp_path / 'test_nodata.tif'
    max_lat, min_lon, pixelsize = 1, 1, 0.1
    transform = [min_lon, pixelsize, 0, max_lat, 0, -1 * pixelsize]
    array = np.ones((10, 10, 4)).astype(np.uint8) * 255
    create_test_image(test_data_path, array, transform)
    create_test_image(test_nodata, array * 0, transform)

    data_paths = create_browse.remove_empty_tiles([test_data_path, test_nodata])
    assert len(data_paths) == 1
    assert data_paths[0] == test_data_path
