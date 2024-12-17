import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import harmony_service_lib
import pystac
import pytest
from harmony_service_lib.exceptions import HarmonyException

from opera_rtc_s1_browse import harmony_service


def mock_download(**kwargs) -> str:
    assert set(kwargs.keys()) == {'url', 'destination_dir', 'logger', 'access_token'}

    assert kwargs['url'] in ('url/to/mock_VV.tif', 'url/to/mock_VH.tif')
    assert isinstance(kwargs['destination_dir'], str)
    assert isinstance(kwargs['logger'], logging.Logger)
    assert kwargs['access_token'] == 'mock-access-token'

    if kwargs['url'] == 'url/to/mock_VV.tif':
        return 'mock_VV.tif'

    return 'mock_VH.tif'


def mock_create_browse_image(**kwargs) -> Path:
    assert set(kwargs.keys()) == {'co_pol_path', 'cross_pol_path', 'working_dir'}

    assert kwargs['co_pol_path'] == Path('mock_VV.tif')
    assert kwargs['cross_pol_path'] == Path('mock_VH.tif')
    assert isinstance(kwargs['working_dir'], Path)

    return Path('path') / 'to' / 'mock_rgb.tif'


def mock_stage(**kwargs) -> str:
    assert set(kwargs.keys()) == {'local_filename', 'remote_filename', 'mime', 'location', 'logger'}

    assert kwargs['local_filename'] == 'path/to/mock_rgb.tif'
    assert kwargs['remote_filename'] == 'mock_rgb.tif'
    assert kwargs['mime'] == 'image/tiff'
    assert kwargs['location'] == 'mock-staging-location'
    assert isinstance(kwargs['logger'], logging.Logger)

    return 'mock-staged-url'


def test_process_item():
    adapter = harmony_service.HarmonyAdapter(
        harmony_service_lib.message.Message(
            {
                'accessToken': 'mock-access-token',
                'stagingLocation': 'mock-staging-location',
            }
        )
    )
    item = pystac.Item(
        id='mock-pystac-item',
        geometry=None,
        bbox=None,
        datetime=datetime(2024, 1, 1),
        properties={},
        assets={
            'data': pystac.Asset(href='url/to/mock_VH.tif'),
            'data1': pystac.Asset(href='url/to/mock_VV.tif'),
        },
    )
    expected_result = pystac.Item(
        id='mock-pystac-item',
        geometry=None,
        bbox=None,
        datetime=datetime(2024, 1, 1),
        properties={},
        assets={
            'rgb_browse': pystac.Asset(
                href='mock-staged-url', title='mock_rgb.tif', media_type='image/tiff', roles=['visual']
            )
        },
    )
    with (
        patch('harmony_service_lib.util.download', mock_download),
        patch('opera_rtc_s1_browse.create_browse.create_browse_image', mock_create_browse_image),
        patch('harmony_service_lib.util.stage', mock_stage),
    ):
        assert adapter.process_item(item).to_dict() == expected_result.to_dict()


def test_process_item_missing_co_pol():
    adapter = harmony_service.HarmonyAdapter(harmony_service_lib.message.Message({}))
    item = pystac.Item(
        id='mock-pystac-item',
        geometry=None,
        bbox=None,
        datetime=datetime(2024, 1, 1),
        properties={},
        assets={
            'data': pystac.Asset(href='url/to/mock_VH.tif'),
        },
    )
    with pytest.raises(HarmonyException, match=r'^No _VV.tif asset found for mock-pystac-item$'):
        adapter.process_item(item)


def test_process_item_missing_cross_pol():
    adapter = harmony_service.HarmonyAdapter(harmony_service_lib.message.Message({}))
    item = pystac.Item(
        id='mock-pystac-item',
        geometry=None,
        bbox=None,
        datetime=datetime(2024, 1, 1),
        properties={},
        assets={
            'data': pystac.Asset(href='url/to/mock_VV.tif'),
        },
    )
    with pytest.raises(HarmonyException, match=r'^No _VH.tif asset found for mock-pystac-item$'):
        adapter.process_item(item)
