import datetime
from unittest.mock import patch

import numpy as np

from opera_rtc_s1_browse import create_browse


def test_normalize_image_array():
    input_array = np.arange(0, 10)
    golden_array = np.array([0, 75, 115, 145, 169, 191, 210, 227, 244, 255])
    output_array = create_browse.normalize_image_array(input_array)
    assert np.array_equal(output_array, golden_array)

    input_array = np.append(input_array.astype(float), np.nan)
    golden_array = np.append(golden_array, 0)
    output_array = create_browse.normalize_image_array(input_array)
    assert np.array_equal(output_array, golden_array)


def test_create_browse_array():
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


def test_create_metadata_xml(tmp_path):
    info = {
        'metadata': {
            '': {
                'ZERO_DOPPLER_START_TIME': '2024-01-13T02:08:16.123456Z',
                'ZERO_DOPPLER_END_TIME': '2024-01-13T02:08:19.987654',
            }
        }
    }
    with patch('opera_rtc_s1_browse.create_browse.now', return_value=datetime.datetime(2024, 6, 14, 6, 4, 32, 234)):
        with patch('osgeo.gdal.Info', return_value=info):
            co_pol_path = tmp_path / 'vv.tif'
            browse_path = tmp_path / 'browse.tif'
            metadata_path = create_browse.create_metadata_xml(co_pol_path, browse_path)
    assert metadata_path == tmp_path / 'browse.xml'
    assert metadata_path.read_text() == (
        '<ImageryMetadata xmlns="http://www.w3.org/2005/Atom" xmlns:georss="http://www.georss.org/georss/10">\n'
        '  <ProviderProductId>browse</ProviderProductId>\n'
        '  <ProductionDateTime>2024-06-14T06:04:32Z</ProductionDateTime>\n'
        '  <DataStartDateTime>2024-01-13T02:08:16Z</DataStartDateTime>\n'
        '  <DataEndDateTime>2024-01-13T02:08:19Z</DataEndDateTime>\n'
        '  <DataDay>20240113</DataDay>\n'
        '</ImageryMetadata>\n'
    )
