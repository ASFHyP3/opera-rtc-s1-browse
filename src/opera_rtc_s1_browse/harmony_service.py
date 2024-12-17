import argparse
import tempfile
from pathlib import Path

import harmony_service_lib
import pystac
from harmony_service_lib.exceptions import HarmonyException

from opera_rtc_s1_browse import create_browse


class HarmonyAdapter(harmony_service_lib.BaseHarmonyAdapter):
    def process_item(self, item: pystac.Item, source: harmony_service_lib.message.Source | None = None) -> pystac.Item:
        """Processes a single input item.

        Parameters
        ----------
        item : pystac.Item
            the item that should be processed
        source : harmony_service_lib.message.Source
            the input source defining the variables, if any, to subset from the item

        Returns:
        -------
        pystac.Item
            a STAC catalog whose metadata and assets describe the service output
        """
        self.logger.info(f'Processing item {item.id}')

        co_pol_url = get_asset_url(item, '_VV.tif')
        cross_pol_url = get_asset_url(item, '_VH.tif')

        with tempfile.TemporaryDirectory() as temp_dir:
            co_pol_filename = harmony_service_lib.util.download(
                url=co_pol_url,
                destination_dir=temp_dir,
                logger=self.logger,
                access_token=self.message.accessToken,
            )
            cross_pol_filename = harmony_service_lib.util.download(
                url=cross_pol_url,
                destination_dir=temp_dir,
                logger=self.logger,
                access_token=self.message.accessToken,
            )
            rgb_path = create_browse.create_browse_image(
                co_pol_path=Path(co_pol_filename),
                cross_pol_path=Path(cross_pol_filename),
                working_dir=Path(temp_dir),
            )
            url = harmony_service_lib.util.stage(
                local_filename=str(rgb_path),
                remote_filename=rgb_path.name,
                mime='image/tiff',
                location=self.message.stagingLocation,
                logger=self.logger,
            )

            result = item.clone()
            result.assets = {
                'rgb_browse': pystac.Asset(url, title=rgb_path.name, media_type='image/tiff', roles=['visual'])
            }

        return result


def get_asset_url(item: pystac.Item, suffix: str) -> str:
    try:
        return next(asset.href for asset in item.assets.values() if asset.href.endswith(suffix))
    except StopIteration:
        raise HarmonyException(f'No {suffix} asset found for {item.id}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the Harmony service')
    harmony_service_lib.setup_cli(parser)
    args = parser.parse_args()
    harmony_service_lib.run_cli(parser, args, HarmonyAdapter)


if __name__ == '__main__':
    main()
