import logging
import os
from calendar import monthrange
from datetime import datetime, timezone
from typing import Dict, List, Optional

import stactools.core.create
from pystac import Asset, Item, MediaType
from stactools.core.io import ReadHrefModifier

from stactools.nclimgrid.cog import create_cogs
from stactools.nclimgrid.constants import (
    ASSET_TITLES,
    RASTER_BANDS,
    RASTER_EXTENSION_V11,
    VARS,
)
from stactools.nclimgrid.utils import (
    data_frequency,
    day_indices,
    month_indices,
    nc_href_dict,
)

logger = logging.getLogger(__name__)


def create_item(cog_hrefs: Dict[str, str]) -> Item:
    frequency = data_frequency(cog_hrefs["prcp"])
    basename = os.path.splitext(os.path.basename(cog_hrefs["prcp"]))[0]

    nominal_datetime: Optional[datetime] = None
    if frequency == "Daily":
        id = basename[5:]
        year = int(id[0:4])
        month = int(id[4:6])
        day = int(id[-2:])
        start_datetime = datetime(year, month, day)
        end_datetime = datetime(year, month, day, 23, 59, 59)
        nominal_datetime = start_datetime
    else:
        id = f"nclimgrid-{basename[-6:]}"
        year = int(id[-6:-2])
        month = int(id[-2:])
        start_datetime = datetime(year, month, 1)
        end_datetime = datetime(year, month, monthrange(year, month)[1])
        nominal_datetime = None

    item = stactools.core.create.item(cog_hrefs["prcp"])
    item.id = id
    item.datetime = nominal_datetime
    item.common_metadata.start_datetime = start_datetime
    item.common_metadata.end_datetime = end_datetime
    item.common_metadata.created = datetime.now(tz=timezone.utc)

    item.assets.pop("data")
    for var in VARS:
        item.add_asset(
            var,
            Asset(
                href=cog_hrefs[var],
                media_type=MediaType.COG,
                roles=["data"],
                title=f"{frequency} {ASSET_TITLES[var]}",
                extra_fields={"raster:bands": RASTER_BANDS[var]},
            ),
        )
    item.stac_extensions.append(RASTER_EXTENSION_V11)

    return item


def create_items(
    nc_href: str,
    cog_dir: str,
    latest_only: bool = False,
    read_href_modifier: Optional[ReadHrefModifier] = None,
) -> List[Item]:
    frequency = data_frequency(nc_href)
    nc_hrefs = nc_href_dict(nc_href)

    if read_href_modifier:
        read_nc_hrefs = {var: read_href_modifier(nc_hrefs[var]) for var in VARS}
    else:
        read_nc_hrefs = nc_hrefs

    items = []
    if frequency == "Daily":
        days = day_indices(read_nc_hrefs["prcp"])
        for day in days:
            cog_paths = create_cogs(read_nc_hrefs, cog_dir, day=day)
            items.append(create_item(cog_paths))

    else:
        months = month_indices(read_nc_hrefs["prcp"])
        for month in months:
            cog_paths = create_cogs(read_nc_hrefs, cog_dir, month=month)
            items.append(create_item(cog_paths))

    return items


# # nc_href = "tests/data-files/netcdf/daily/beta/by-month/2022/01/prcp-202201-grd-prelim.nc"
# # nc_href = "tests/data-files/netcdf/daily/beta/by-month/1951/01/ncdd-195101-grd-scaled.nc"
# # nc_href = "tests/data-files/netcdf/monthly/nclimgrid_prcp.nc"

# nc_href = "https://nclimgridwesteurope.blob.core.windows.net/nclimgrid/nclimgrid-daily/beta/by-month/2022/06/prcp-202206-grd-prelim.nc"  # noqa
# nc_href = "https://nclimgridwesteurope.blob.core.windows.net/nclimgrid/nclimgrid-daily/beta/by-month/2022/06/prcp-202206-grd-scaled.nc"  # noqa
# nc_href = "https://nclimgridwesteurope.blob.core.windows.net/nclimgrid/nclimgrid-monthly/nclimgrid_prcp.nc"  # noqa

# nc_href = "https://e84ai4earth.blob.core.windows.net/nclimgrid/nclimgrid-monthly/nclimgrid_prcp.nc?sv=2020-10-02&st=2022-07-18T21%3A31%3A19Z&se=2022-12-19T22%3A31%3A00Z&sr=c&sp=racwdxlt&sig=dPkXcbmMAGd0DdwbYY7DMfULeiTSCXXS1KfisER3RvA%3D"  # noqa


# cog_dir = "/Users/pjh/dev/nclimgrid/pjh/test_cogs"
# items = create_items(nc_href, cog_dir)
# import json

# for item in items:
#     with open(f"pjh/test_items/{item.id}.json", "w") as f:
#         json.dump(item.to_dict(), f)
