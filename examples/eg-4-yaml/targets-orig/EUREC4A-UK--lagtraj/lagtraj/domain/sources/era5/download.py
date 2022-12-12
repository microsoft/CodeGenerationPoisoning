"""
Routines for downloading era5 data for a given domain and storing it locally
"""
import datetime
import warnings
from pathlib import Path

import requests
import yaml

from .... import utils
from . import FILENAME_FORMAT, VERSION_FILENAME
from .cdsapi_request import RequestFetchCDSClient

DATA_REQUESTS_FILENAME = "data_requests.yaml"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%h:%M:%s"
REPOSITORY_NAME = "reanalysis-era5-complete"


def _normalise_date(d):
    if isinstance(d, datetime.datetime):
        warnings.warn(
            "the era5 downloader for lagtraj downloads data in blocks of days"
            f" and so the time component of the provided datetime `{d}` will be ignored"
        )
        return d.date()
    return d


def download_data(
    path, start_date, end_date, bbox, latlon_sampling, version, overwrite_existing=False
):
    """
    Queue and download ERA5 data from ECMWF using the CDSAPI in the time range
    `start_date` to `end_date` into a local directory defined by `path` and give this
    dataset a specific `version`. The lat/lon sampling resolution is given by
    `latlon_sampling`. Download is split into individual files per day,
    run-type (analysis or forecast) and height-level (model or surface). Un
    less `overwite_existing==True` only missing files will be queued and
    downloaded.
    """
    start_date = _normalise_date(start_date)
    end_date = _normalise_date(end_date)

    dl_queries = list(
        _build_queries(
            start_date=start_date,
            end_date=end_date,
            bbox=bbox,
            latlon_sampling=latlon_sampling,
        )
    )

    try:
        c = RequestFetchCDSClient()
    except Exception as ex:
        if str(ex).startswith("Missing/incomplete configuration file"):
            raise Exception(
                "To download ERA5 data you will first need to set up the"
                " CDS API, details: https://cds.climate.copernicus.eu/api-how-to"
            )
        else:
            raise

    try:
        with open(path / DATA_REQUESTS_FILENAME, "r") as fh:
            download_requests = yaml.load(fh, Loader=yaml.FullLoader)
    except FileNotFoundError:
        download_requests = {}

    for output_filename, query_kwargs in dl_queries:
        file_path = Path(path) / output_filename
        query_hash = utils.dict_to_hash(query_kwargs)

        download_id = str(file_path)
        should_make_request = True
        if not overwrite_existing and file_path.exists():
            should_make_request = False

        if download_id in download_requests:
            download_request = download_requests[download_id]
            has_valid_args = download_request["query_hash"] == query_hash
            request_id = download_request["request_id"]

            if has_valid_args and _request_exists(request_id=request_id, c=c):
                # TODO: unqueue invalid requests here so that the server isn't
                # working on unecessary requests
                should_make_request = False
            else:
                del download_requests[download_id]

        if should_make_request:
            request_id = c.queue_data_request(
                repository_name=REPOSITORY_NAME, query_kwargs=query_kwargs
            )
            assert request_id is not None
            download_requests[download_id] = dict(
                request_id=request_id, query_hash=query_hash
            )

    # save the download requests IDs so we have them later in case we quit,
    # downloads fail, etc
    if len(download_requests) > 0:
        Path(path).mkdir(exist_ok=True, parents=True)
        with open(path / DATA_REQUESTS_FILENAME, "w") as fh:
            fh.write(yaml.dump(download_requests))

    files_to_download = _get_files(path=path, c=c, debug=True, with_status="completed")

    if len(files_to_download) > 0:
        print("Downloading files which are ready...")
        for file_path in files_to_download:
            request_details = download_requests[file_path]
            request_id = request_details["request_id"]
            query_hash = request_details["query_hash"]

            Path(file_path).parent.mkdir(exist_ok=True, parents=True)
            try:
                c.download_data_by_request(request_id=request_id, target=file_path)
            except requests.exceptions.HTTPError as ex:
                if ex.response.status_code == 404:
                    print(
                        f"Request {request_details['request_id']} wasn't found"
                        " on the CDS backend, it has probably expired."
                        " Re-requesting..."
                    )
                    # delete the stored request and re-request the data
                    query_kwargs = dict(dl_queries)[Path(file_path).name]
                    request_id = c.queue_data_request(
                        repository_name=REPOSITORY_NAME, query_kwargs=query_kwargs
                    )
                    assert request_id is not None
                    download_requests[download_id] = dict(
                        request_id=request_id, query_hash=query_hash
                    )
                else:
                    raise
            del download_requests[file_path]
    # save download requets again now we've downloaded the files that were
    # ready
    if len(download_requests) > 0:
        with open(path / DATA_REQUESTS_FILENAME, "w") as fh:
            fh.write(yaml.dump(download_requests))
    else:
        data_requests_file = Path(path / DATA_REQUESTS_FILENAME)
        if data_requests_file.exists():
            data_requests_file.unlink()

            version_filename = Path(path) / VERSION_FILENAME
            with open(version_filename, "w") as fh:
                fh.write(version)

        print("All files downloaded!")


def find_missing_files(path, start_date, end_date, bbox, latlon_sampling):
    """
    Check if all data has been downloaded in the request time interval,
    bounding-box and resolution.
    """
    start_date = _normalise_date(start_date)
    end_date = _normalise_date(end_date)

    dl_queries = list(
        _build_queries(
            start_date=start_date,
            end_date=end_date,
            bbox=bbox,
            latlon_sampling=latlon_sampling,
        )
    )

    missing_files = []

    # check if any files don't exist locally yet
    # NOTE: this will not check if files are only partially downloaded
    for output_filename, query_kwargs in dl_queries:
        fp = Path(path) / output_filename
        if not fp.exists():
            missing_files.append(
                dict(filepath=fp, source="ERA5 CDSAPI", query_kwargs=query_kwargs)
            )

    return missing_files


def data_backend_is_processing_requests(path):
    """
    Check if the CDSAPI is still processing some of the data requests
    """
    c = RequestFetchCDSClient()
    return len(_get_files(path=path, c=c, with_status=["queued", "running"])) == 0


def _request_exists(request_id, c):
    try:
        c.get_request_status(request_id)
        return True
    except c.RequestNotFoundException:
        return False


def _get_files(path, c, debug=False, with_status=None):
    meta_filename = path / DATA_REQUESTS_FILENAME
    if not meta_filename.exists():
        return []

    with open(meta_filename, "r") as fh:
        download_requests = yaml.load(fh, Loader=yaml.FullLoader)

    files = []
    if len(download_requests) > 0:
        if debug:
            print("Status on current data requests:")
        for file_path, request_details in download_requests.items():
            request_id = request_details["request_id"]
            status = c.get_request_status(request_id=request_id)
            if debug:
                print(" {}:\n\t{} ({})".format(file_path, status, request_id))

            if with_status is not None:
                if status == with_status or status in with_status:
                    files.append(file_path)
            else:
                files.append(file_path)
    return files


def _build_query_times(model_run_type, start_date, end_date):
    """
    We currently download era5 data by date, build the query dates as datetime
    objects in the request time range
    Note: forecast needs to start a day earlier, due to it starting from 18Z
    """
    if model_run_type == "an":
        return [
            (start_date + datetime.timedelta(days=x))
            for x in range(0, (end_date - start_date).days + 1)
        ]
    elif model_run_type == "fc":
        return [
            (start_date + datetime.timedelta(days=x))
            for x in range(-1, (end_date - start_date).days + 1)
        ]
    else:
        raise NotImplementedError(model_run_type)


def _build_queries(start_date, end_date, bbox, latlon_sampling):
    """
    Return a list of cdsapi query arguments for any files that don't already
    exist
    """
    model_run_types = ["an", "fc"]  # analysis and forecast runs
    level_types = ["model", "single"]  # need model and surface data

    for model_run_type in model_run_types:
        query_times = _build_query_times(
            model_run_type=model_run_type, start_date=start_date, end_date=end_date
        )
        for level_type in level_types:
            for t in query_times:
                output_filename = FILENAME_FORMAT.format(
                    model_run_type=model_run_type,
                    level_type=level_type,
                    date=t.strftime(DATE_FORMAT),
                )

                query_kwargs = _build_query(
                    model_run_type=model_run_type,
                    level_type=level_type,
                    date=t,
                    bbox=bbox,
                    latlon_sampling=latlon_sampling,
                )

                yield (output_filename, query_kwargs)


def _build_query(model_run_type, level_type, date, bbox, latlon_sampling):
    if model_run_type == "an" and level_type == "single":
        return _build_single_level_an_query(
            date=date, bbox=bbox, latlon_sampling=latlon_sampling
        )
    elif model_run_type == "an" and level_type == "model":
        return _build_model_level_an_query(
            date=date, bbox=bbox, latlon_sampling=latlon_sampling
        )
    elif model_run_type == "fc" and level_type == "single":
        return _build_single_level_fc_query(
            date=date, bbox=bbox, latlon_sampling=latlon_sampling
        )
    elif model_run_type == "fc" and level_type == "model":
        return _build_model_level_fc_query(
            date=date, bbox=bbox, latlon_sampling=latlon_sampling
        )
    else:
        raise NotImplementedError(model_run_type, level_type)


def _build_single_level_an_query(date, bbox, latlon_sampling):
    # 2D ANALYSIS FROM ERA5
    # 27 Low vegetation cover [(0 - 1)], cvl
    # 28 High vegetation cover [(0 - 1)], cvh
    # 29 Type of low vegetation [~], tvl
    # 30 Type of high vegetation cover [~], tvh
    # 31 Sea ice area fraction [(0 - 1)], ci
    # 32 Snow albedo [(0 - 1)], asn
    # 33 Snow density [kg m**-3], rsn
    # 34 Sea surface temperature [K], sst
    # 35 Ice temperature layer 1 [K], istl1
    # 39 Volumetric soil water layer 11 [m**3 m**-3], swvl1
    # 40 Volumetric soil water layer 21 [m**3 m**-3], swvl2
    # 41 Volumetric soil water layer 31 [m**3 m**-3], swvl3
    # 42 Volumetric soil water layer 41 [m**3 m**-3], swvl4
    # 66 Leaf area index, low vegetation [m**2 m**-2], lai_lv
    # 67 Leaf area index, high vegetation [m**2 m**-2], lai_hv
    # 129 Geopotential [m**2 s**-2], z
    # 134 Surface pressure [Pa], sp
    # 136 Total column water  [kg m**-2], tcw
    # 139 Soil temperature level 11 [K], stl1
    # 141 Snow depth [m of water equivalent], sd
    # 151 Mean sea level pressure [Pa], msl
    # 159 Boundary layer height [m],  blh
    # 160 Standard deviation of orography [~], sdor
    # 161 Anisotropy of sub-gridscale orography [~], isor
    # 162 Angle of sub-gridscale orography [radians], anor
    # 163 Slope of sub-gridscale orography [~], slor
    # 164 Total cloud cover [(0 - 1)],  tcc
    # 170 Soil temperature level 21 [K], stl2
    # 172 Land-sea mask [(0 - 1)], lsm
    # 183 Soil temperature level 31 [K], stl3
    # 186 Low cloud cover [(0 - 1)],  lcc
    # 187 Medium cloud cover  [(0 - 1)],  mcc
    # 188 High cloud cover  [(0 - 1)],  hcc
    # 198 Skin reservoir content [m of water equivalent], src
    # 236 Soil temperature level 41 [K], stl4
    # 238 Temperature of snow layer [K], tsn
    # 243 Forecast albedo [(0 - 1)], fal
    # 244 Forecast surface roughness [m], fsr
    # 245 Forecast logarithm of surface roughness for heat [~], flsr

    return {
        "class": "ea",
        "date": date.strftime(DATE_FORMAT),
        "expver": "1",
        "levtype": "sfc",
        "param": (
            "27.128/28.128/29.128/30.128/31.128/32.128/33.128/34.128"
            "/35.128/39.128/40.128/41.128/42.128/66.128/67.128"
            "/129.128/134.128/136.128/139.128/141.128/151.128/159.128"
            "/160.128/161.128/162.128/163.128/164.128/170.128/172.128"
            "/183.128/186.128/187.128/188.128/198.128/236.128/238.128"
            "/243.128/244.128/245.128"
        ),
        "stream": "oper",
        "time": (
            "00:00:00/01:00:00/02:00:00/03:00:00/04:00:00/05:00:00"
            "/06:00:00/07:00:00/08:00:00/09:00:00/10:00:00/11:00:00"
            "/12:00:00/13:00:00/14:00:00/15:00:00/16:00:00/17:00:00"
            "/18:00:00/19:00:00/20:00:00/21:00:00/22:00:00/23:00:00"
        ),
        "area": [
            bbox.lat_max,
            bbox.lon_min,
            bbox.lat_min,
            bbox.lon_max,
        ],
        "grid": "{}/{}".format(latlon_sampling.lat, latlon_sampling.lon),
        "type": "an",
        "format": "netcdf",
    }


def _build_model_level_an_query(date, bbox, latlon_sampling):
    # 3D ANALYSIS FROM ERA5
    # 75  Specific rain water content [kg kg**-1],  crwc
    # 76  Specific snow water content [kg kg**-1],  cswc
    # 77  Eta-coordinate vertical velocity [s**-1], etadot
    # 129 Geopotential* [m**2 s**-2], z
    # 130 Temperature [K],  t
    # 131 U component of wind [m s**-1],  u
    # 132 V component of wind [m s**-1],  v
    # 133 Specific humidity [kg kg**-1],  q
    # 135 Vertical velocity [Pa s**-1], w
    # 152 Logarithm of surface pressure*  [~],  lnsp
    # 203 Ozone mass mixing ratio [kg kg**-1],  o3
    # 246 Specific cloud liquid water content [kg kg**-1],  clwc
    # 247 Specific cloud ice water content  [kg kg**-1],  ciwc
    # 248 Fraction of cloud cover [(0 - 1)],  cc
    return {
        "class": "ea",
        "date": date.strftime(DATE_FORMAT),
        "expver": "1",
        "levelist": (
            "1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/"
            "22/23/24/25/26/27/28/29/30/31/32/33/34/35/36/37/38/39/"
            "40/41/42/43/44/45/46/47/48/49/50/51/52/53/54/55/56/57/"
            "58/59/60/61/62/63/64/65/66/67/68/69/70/71/72/73/74/75/"
            "76/77/78/79/80/81/82/83/84/85/86/87/88/89/90/91/92/93/"
            "94/95/96/97/98/99/100/101/102/103/104/105/106/107/108/"
            "109/110/111/112/113/114/115/116/117/118/119/120/121/"
            "122/123/124/125/126/127/128/129/130/131/132/133/134/"
            "135/136/137"
        ),
        "levtype": "ml",
        "param": "75/76/77/129/130/131/132/133/135/152/203/246/247/248",
        "stream": "oper",
        "time": (
            "00:00:00/01:00:00/02:00:00/03:00:00/04:00:00/05:00:00"
            "/06:00:00/07:00:00/08:00:00/09:00:00/10:00:00/11:00:00"
            "/12:00:00/13:00:00/14:00:00/15:00:00/16:00:00/17:00:00"
            "/18:00:00/19:00:00/20:00:00/21:00:00/22:00:00/23:00:00"
        ),
        "area": [bbox.lat_max, bbox.lon_min, bbox.lat_min, bbox.lon_max],
        "grid": "{}/{}".format(latlon_sampling.lat, latlon_sampling.lon),
        "type": "an",
        "format": "netcdf",
    }


def _build_single_level_fc_query(date, bbox, latlon_sampling):
    # 2D FORECAST DATA FROM ERA5
    # 146 Surface sensible heat flux (accumulated) [J m**-2], sshf
    # 147 Surface latent heat flux (accumulated) [J m**-2], slhf
    # 228001 Convective inhibition [J kg**-1], cin
    # 228003 Friction velocity [m s**-1], zust
    # 228023 Cloud base height [m], cbh
    # 235033 Mean surface sensible heat flux [W m**-2], msshf
    # 235034 Mean surface latent heat flux [W m**-2], mslhf
    # 235035 Mean surface downward short-wave radiation flux [W m**-2],
    #        msdwswrf
    # 235036 Mean surface downward long-wave radiation flux [W m**-2], msdwlwrf
    # 235037 Mean surface net short-wave radiation flux [W m**-2], msnswrf
    # 235038 Mean surface net long-wave radiation flux [W m**-2], msnlwrf
    # 235039 Mean top net short-wave radiation flux [W m**-2], mtnswrf
    # 235040 Mean top net long-wave radiation flux [W m**-2], mtnlwrf
    # 235043 Mean evaporation rate [kg m**-2 s**-1 ], mer
    # 235049 Mean top net short-wave radiation flux, clear sky [W m**-2],
    #        mtnswrfcs
    # 235050 Mean top net long-wave radiation flux, clear sky [W m**-2],
    #        mtnlwrfcs
    # 235051 Mean surface net short-wave radiation flux, clear sky [W m**-2],
    #        msnswrfcs
    # 235052 Mean surface net long-wave radiation flux, clear sky [W m**-2],
    #        msnlwrfcs
    # 235053 Mean top downward short-wave radiation flux [W m**-2], mtdwswrf
    # 235058 Mean surface direct short-wave radiation flux [W m**-2], msdrswrf
    # 235059 Mean surface direct short-wave radiation flux, clear sky [W m**-2]
    #        msdrswrfcs
    # 235068 Mean surface downward short-wave radiation flux, clear sky
    #        [W m**-2],msdwswrfcs
    # 235069 Mean surface downward long-wave radiation flux, clear sky
    #        [W m**-2], msdwlwrfcs
    # 235070 Mean potential evaporation rate [kg m**-2 s**-1 ], mper
    return {
        "class": "ea",
        "date": date.strftime(DATE_FORMAT),
        "expver": "1",
        "levtype": "sfc",
        "param": (
            "146.128/147.128/228001/228003/228023/235033/235034/235035"
            "/235036/235037/235038/235039/235040/235043/235049/235050"
            "/235051/235052/235053/235058/235059/235068/235069/235070"
        ),
        "stream": "oper",
        "time": "06:00:00/18:00:00",
        "area": [bbox.lat_max, bbox.lon_min, bbox.lat_min, bbox.lon_max],
        "grid": "{}/{}".format(latlon_sampling.lat, latlon_sampling.lon),
        "type": "fc",
        "step": "1/2/3/4/5/6/7/8/9/10/11/12",
        "format": "netcdf",
    }


def _build_model_level_fc_query(date, bbox, latlon_sampling):
    # 3D FORECAST DATA FROM ERA5
    # 235001  Mean temperature tendency due to short-wave radiation [K s**-1],
    #         mttswr
    # 235002  Mean temperature tendency due to long-wave radiation  [K s**-1],
    #         mttlwr
    # 235003  Mean temperature tendency due to short-wave radiation
    #         [clear sky  K s**-1], mttswrcs
    # 235004  Mean temperature tendency due to long-wave radiation
    #         [clear sky K s**-1], mttlwrcs
    return {
        "class": "ea",
        "date": date.strftime(DATE_FORMAT),
        "expver": "1",
        "levelist": (
            "1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/"
            "22/23/24/25/26/27/28/29/30/31/32/33/34/35/36/37/38/39/"
            "40/41/42/43/44/45/46/47/48/49/50/51/52/53/54/55/56/57/"
            "58/59/60/61/62/63/64/65/66/67/68/69/70/71/72/73/74/75/"
            "76/77/78/79/80/81/82/83/84/85/86/87/88/89/90/91/92/93/"
            "94/95/96/97/98/99/100/101/102/103/104/105/106/107/108/"
            "109/110/111/112/113/114/115/116/117/118/119/120/121/"
            "122/123/124/125/126/127/128/129/130/131/132/133/134/"
            "135/136/137"
        ),
        "levtype": "ml",
        "param": "235001/235002/235003/235004",
        "stream": "oper",
        "time": "06:00:00/18:00:00",
        "type": "fc",
        "area": [
            bbox.lat_max,
            bbox.lon_min,
            bbox.lat_min,
            bbox.lon_max,
        ],
        "grid": "{}/{}".format(latlon_sampling.lat, latlon_sampling.lon),
        "step": "1/2/3/4/5/6/7/8/9/10/11/12",
        "format": "netcdf",
    }
