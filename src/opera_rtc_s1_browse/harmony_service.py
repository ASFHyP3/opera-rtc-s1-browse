import argparse
import tempfile
from pathlib import Path

import harmony_service_lib
import pystac

from opera_rtc_s1_browse import create_browse


class HarmonyAdapter(harmony_service_lib.BaseHarmonyAdapter):

    def process_item(self, item: pystac.Item, source: harmony_service_lib.message.Source = None) -> pystac.Item:
        """
        Processes a single input item.

        Parameters
        ----------
        item : pystac.Item
            the item that should be processed
        source : harmony_service_lib.message.Source
            the input source defining the variables, if any, to subset from the item

        Returns
        -------
        pystac.Item
            a STAC catalog whose metadata and assets describe the service output
        """
        self.logger.info(f'Processing item {item.id}')

        co_pol_filename = None
        cross_pol_filename = None

        with tempfile.TemporaryDirectory() as temp_dir:

            for asset in item.assets.values():
                if asset.href.endswith('VV.tif'):
                    co_pol_filename = harmony_service_lib.util.download(
                        url=asset.href,
                        destination_dir=temp_dir,
                        logger=self.logger,
                        access_token=self.message.accessToken,
                    )
                if asset.href.endswith('VH.tif'):
                    cross_pol_filename = harmony_service_lib.util.download(
                        url=asset.href,
                        destination_dir=temp_dir,
                        logger=self.logger,
                        access_token=self.message.accessToken,
                    )

            if co_pol_filename is None:
                raise ValueError(f'No VV.tif found for {item.id}')

            if cross_pol_filename is None:
                raise ValueError(f'No VH.tif found for {item.id}')

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


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the Harmony service')
    harmony_service_lib.setup_cli(parser)
    args = parser.parse_args()
    harmony_service_lib.run_cli(parser, args, HarmonyAdapter)


if __name__ == "__main__":
    main()
