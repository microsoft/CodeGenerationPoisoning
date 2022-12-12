import numpy as np
import matplotlib.pyplot as plt
import h5py
import pymap3d as pm
import icebear.utils as utils
import datetime
from dateutil.tz import tzutc


def map_target(tx, rx, az, el, rf, dop, wavelength):
    """
    Find the scatter location given tx location, rx location, total rf distance, and target angle-of-arrival
    using the 'WGS84' Earth model. Also determines the bistatic velocity vector and bistatic radar wavelength.

    Parameters
    ----------
        tx : float np.array
            [latitude, longitude, altitude] of tx array in degrees and kilometers
        rx : float np.array
            [latitude, longitude, altitude] of rx array in degrees and kilometers
        az : float np.array
            angle-of-arrival azimuth in degrees
        el : float np.array
            angle-of-arrival elevation in degrees
        rf : float np.array
            total rf path distance rf = c * tau in kilometers
        dop : float np.array
            doppler shift in hertz
        wavelength : float
            radar signal center wavelength

    Returns
    -------
        sx : float np.array
            [latitude, longitude, altitude] of scatter in degrees and kilometers
        sa : float np.array
            [azimuth, elevation, slant range] of scatter in degrees and kilometers
        sv : float np.array
            [azimuth, elevation, velocity] the bistatic Doppler velocity vector in degrees and kilometers.
            Coordinates given in the scattering targets local frame (azimuth from North, elevation up from
            the plane normal to zenith, Doppler [Hz] * lambda / (2 cos(e/2)) )

    Notes
    -----
    tx : transmitter location
    rx : receiver location
    sx : scatter location
    gx : geometric center of Earth, origin
    u_rt : unit vector rx to tx
    u_rs : unit vector rx to sx
    u_gt : unit vector gx to tx
    u_gr : unit vector gx to rx
    u_gs : unit vector gx to sx
    """

    # Initialize output arrays
    sx = np.zeros((3, len(rf)), dtype=float)
    sa = np.zeros((3, len(rf)), dtype=float)
    sv = np.zeros((3, len(rf)), dtype=float)

    # Setup variables in correct units for pymap3d
    rf = rf * 1.0e3
    az = np.where(az < 0.0, az + 360.0, az)
    az = np.deg2rad(az)
    el = np.deg2rad(np.abs(el))

    # Determine the slant range, r
    bx1, by1, bz1 = pm.geodetic2ecef(rx[0], rx[1], rx[2], ell=pm.Ellipsoid("wgs84"), deg=True)
    v_gr = np.array([bx1, by1, bz1])
    bx2, by2, bz2 = pm.geodetic2ecef(tx[0], tx[1], tx[2], ell=pm.Ellipsoid("wgs84"), deg=True)
    v_gt = np.array([bx2, by2, bz2])
    raz, rel, b = pm.ecef2aer(bx2, by2, bz2, rx[0], rx[1], rx[2], ell=pm.Ellipsoid("wgs84"), deg=True)
    u_rt = np.array([np.sin(np.deg2rad(raz)) * np.cos(np.deg2rad(rel)),
                     np.cos(np.deg2rad(raz)) * np.cos(np.deg2rad(rel)),
                     np.sin(np.deg2rad(rel))])
    el -= relaxation_elevation(el, rf, az, b, u_rt)
    u_rs = np.array([np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])
    r = (rf ** 2 - b ** 2) / (2 * (rf - b * np.dot(u_rt, u_rs)))

    # WGS84 Model for lat, long, alt
    sx[:, :] = pm.aer2geodetic(np.rad2deg(az), np.rad2deg(el), np.abs(r),
                               np.repeat(rx[0], len(az)),
                               np.repeat(rx[1], len(az)),
                               np.repeat(rx[2], len(az)),
                               ell=pm.Ellipsoid("wgs84"), deg=True)

    # Determine the bistatic Doppler velocity vector
    x, y, z = pm.geodetic2ecef(sx[0, :], sx[1, :], sx[2, :],
                               ell=pm.Ellipsoid('wgs84'), deg=True)
    v_gs = np.array([x, y, z])
    v_bi = (-1 * v_gs.T + v_gt / 2.0 + v_gr / 2.0).T
    u_bi = v_bi / np.linalg.norm(v_bi, axis=0)
    v_sr = (v_gr - v_gs.T).T
    u_sr = v_sr / np.linalg.norm(v_sr, axis=0)
    radar_wavelength = wavelength / np.abs(2.0 * np.einsum('ij,ij->j', u_sr, u_bi))
    # doppler_sign = np.sign(dop)  # 1 for positive, -1 for negative, and 0 for zero
    doppler_sign = np.where(dop >= 0, 1, -1)  # 1 for positive, -1 for negative, and 0 for zero
    vaz, vel, _ = pm.ecef2aer(doppler_sign * u_bi[0, :] + x,
                              doppler_sign * u_bi[1, :] + y,
                              doppler_sign * u_bi[2, :] + z,
                              sx[0, :], sx[1, :], sx[2, :],
                              ell=pm.Ellipsoid("wgs84"), deg=True)

    # Convert back to conventional units
    sx[2, :] /= 1.0e3
    az = np.rad2deg(az)
    el = np.rad2deg(el)
    sa[:, :] = np.array([az, el, r / 1.0e3])
    sv[:, :] = np.array([vaz, vel, dop * radar_wavelength])

    return sx, sa, sv


def relaxation_elevation(beta, rf_distance, azimuth, bistatic_distance, bistatic_vector):
    """

    Parameters
    ----------
    beta : float np.array
        Measured elevation angle in degrees
    rf_distance :
    azimuth
    bistatic_distance
    bistatic_vector

    Returns
    -------

    """
    n = 0
    radius_of_earth = 6378.0e3
    err = np.deg2rad(1.0)
    target = np.deg2rad(0.1)
    m = np.zeros((3, len(beta)))
    m[1, :] = 0.1
    v = np.array(
        [np.sin(azimuth) * np.cos(beta - m[1, :]), np.cos(azimuth) * np.cos(beta - m[1, :]), np.sin(beta - m[1, :])])
    r = (rf_distance ** 2 - bistatic_distance ** 2) / (
                2 * (rf_distance - bistatic_distance * (np.dot(bistatic_vector, v))))
    m[2, :] = 1 / (radius_of_earth / r + np.sin(beta) / 2)
    while np.nanmean(err) > target:
        m[0, :] = m[1, :]
        m[1, :] = m[2, :]
        v = np.array([np.sin(azimuth) * np.cos(beta - m[1, :]), np.cos(azimuth) * np.cos(beta - m[1, :]),
                      np.sin(beta - m[1, :])])
        r = (rf_distance ** 2 - bistatic_distance ** 2) / (
                    2 * (rf_distance - bistatic_distance * (np.dot(bistatic_vector, v))))
        m[2, :] = 1 / (radius_of_earth / r + np.sin(beta) / 2)
        err = np.abs((m[1, :] - m[2, :]) ** 2 / (2 * m[1, :] - m[0, :] - m[2, :]))
        n += 1

    m[2, :] = np.where(err >= target, np.nan, m[2, :])
    print('\t-relaxation mean error:', np.rad2deg(np.nanmean(err)), 'iterations:', n)
    return m[2, :]


def velocity_plot(sx, sv, date, time, filepath):
    year = date[0]
    month = date[1]
    day = date[2]
    hour = time[0:2]
    minute = time[2:4]
    second = time[4:6]
    # import cartopy.crs as ccrs
    # ax = plt.axes(projection=ccrs.PlateCarree())
    # ax.set_extent([np.min(sv[0, :]),np.max(sv[0, :]), np.min(sv[1, :]), np.max(sv[1, :])], crs=ccrs.PlateCarree())
    # ax.lakes
    # ax.coastline
    # ax.rivers

    u = np.sin(np.deg2rad(sv[0, :])) * np.cos(np.deg2rad(sv[1, :]))
    v = np.cos(np.deg2rad(sv[0, :])) * np.cos(np.deg2rad(sv[1, :]))
    n = np.sqrt(u ** 2 + v ** 2)
    u /= n
    v /= n
    # u = np.where(sv[2, :] == 0, np.nan, u)
    # v = np.where(sv[2, :] == 0, np.nan, v)

    # plt.figure(figsize=[18, 14])
    fig = plt.figure(figsize=[20, 14], constrained_layout=True)
    gs = fig.add_gridspec(1, 4)
    fig.suptitle(f'{year}-{month}-{day} {hour}:{minute}:{second}')

    # Altitude slice
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('black')
    plt.scatter(sx[2, :], sx[0, :], c=sv[2, :], marker='D', cmap='RdBu', vmin=-1500.0, vmax=1500.0)
    plt.xlabel('Altitude [km]')
    plt.ylabel('Latitude [deg]')
    plt.clim(-1500.0, 1500.0)
    plt.xlim([200.0, 0.0])
    plt.ylim([50.0, 62.0])
    plt.grid()

    # Azimuth slice
    ax2 = fig.add_subplot(gs[0, 1::])
    ax2.set_facecolor('black')
    plt.quiver(sx[1, :], sx[0, :], u, v, sv[2, :], cmap='RdBu')
    # plt.title(f'{year}-{month}-{day} {hour}:{minute}:{second}')
    plt.xlabel('Longitude [deg]')
    # plt.ylabel('Latitude [deg]')
    plt.colorbar(label='Velocity [m/s]')
    plt.clim(-1500.0, 1500.0)
    plt.scatter(sx[1, :], sx[0, :], c=sv[2, :], marker='D', cmap='RdBu', vmin=-1500.0, vmax=1500.0)
    plt.scatter(-109.403, 50.893, c='k')
    plt.annotate('TX', (-109.403, 50.893))
    plt.scatter(-106.450, 52.243, c='k')
    plt.annotate('RX', (-106.450, 52.24))
    props = dict(boxstyle='square', facecolor='wheat', alpha=0.5)
    plt.text(-100.0, 50.5, f'Records {len(sx[1, :]):3d}\nSNR Cutoff 3.0 dB', bbox=props)
    plt.xlim([-114.0, -96.0])
    plt.ylim([50.0, 62.0])
    plt.grid()

    plt.savefig(filepath + f'velocity_{year}{month}{day}_{hour}{minute}{second}.png')
    plt.close()
    # plt.show()
    return


def package_data(time, snr_db, range, azimuth, elevation, altitude,
                 velocity_azimuth, velocity_elevation, doppler_shift):
    # old version use create_level3
    config = ib.utils.Config('X://PythonProjects//icebear//dat//default.yml')

    f = h5py.File('cleaned_2020_06_16.h5', 'w')
    f.create_dataset('date_created', data=np.array([2021, 4, 1]))
    f.create_dataset('version', data=np.array(config.version, dtype='S'))
    f.create_dataset('experiment_name', data=np.array(['meteor winds'], dtype='S'))
    f.create_dataset('radar_config', data=np.array([config.radar_config], dtype='S'))
    f.create_dataset('center_freq', data=config.center_freq)
    # receiver site information
    f.create_dataset('rx_site_name', data=np.array([config.rx_site_name], dtype='S'))
    f.create_dataset('rx_site_lat_long', data=config.rx_site_lat_long)
    f.create_dataset('rx_heading', data=config.rx_heading)
    f.create_dataset('rx_rf_path', data=np.array([config.rx_rf_path], dtype='S'))
    f.create_dataset('rx_ant_type', data=np.array([config.rx_ant_type], dtype='S'))
    f.create_dataset('rx_ant_coords', data=config.rx_ant_coords)
    f.create_dataset('rx_feed_corr', data=config.rx_feed_corr)
    f.create_dataset('rx_feed_corr_date', data=config.rx_feed_corr_date)
    f.create_dataset('rx_feed_corr_type', data=np.array([config.rx_feed_corr_type], dtype='S'))
    f.create_dataset('rx_ant_mask', data=config.rx_ant_mask)
    f.create_dataset('rx_sample_rate', data=config.rx_sample_rate)
    # transmitter site information
    f.create_dataset('tx_site_name', data=np.array([config.tx_site_name], dtype='S'))
    f.create_dataset('tx_site_lat_long', data=config.tx_site_lat_long)
    f.create_dataset('tx_heading', data=config.tx_heading)
    f.create_dataset('tx_rf_path', data=np.array([config.tx_rf_path], dtype='S'))
    f.create_dataset('tx_ant_type', data=np.array([config.tx_ant_type], dtype='S'))
    f.create_dataset('tx_ant_coords', data=config.tx_ant_coords)
    f.create_dataset('tx_feed_corr', data=config.tx_feed_corr)
    f.create_dataset('tx_feed_corr_date', data=config.tx_feed_corr_date)
    f.create_dataset('tx_feed_corr_type', data=np.array([config.tx_feed_corr_type], dtype='S'))
    f.create_dataset('tx_ant_mask', data=config.tx_ant_mask)
    f.create_dataset('tx_sample_rate', data=config.tx_sample_rate)
    # processing settings
    f.create_dataset('decimation_rate', data=config.decimation_rate)
    f.create_dataset('time_resolution', data=config.time_resolution)
    f.create_dataset('coherent_integration_time', data=config.coherent_integration_time)
    f.create_dataset('incoherent_averages', data=config.incoherent_averages)
    f.create_dataset('snr_cutoff_db', data=config.snr_cutoff_db)
    # imaging settings
    f.create_dataset('imaging_method', data=np.array([config.imaging_method], dtype='S'))
    f.create_dataset('swht_coeffs', data=np.array([config.swht_coeffs], dtype='S'))
    f.create_dataset('fov', data=config.fov)
    f.create_dataset('fov_center', data=config.fov_center)
    f.create_dataset('resolution', data=config.resolution)
    f.create_dataset('lmax', data=config.lmax)
    f.create_group('data')

    # append a new group for the current measurement
    f.create_dataset(f'data/time', data=time)
    f.create_dataset(f'data/snr_db', data=snr_db)
    f.create_dataset(f'data/range', data=range)
    f.create_dataset(f'data/azimuth', data=azimuth)
    f.create_dataset(f'data/elevation', data=elevation)
    f.create_dataset(f'data/altitude', data=altitude)
    f.create_dataset(f'data/velocity_azimuth', data=velocity_azimuth)
    f.create_dataset(f'data/velocity_elevation', data=velocity_elevation)
    f.create_dataset(f'data/doppler_shift', data=doppler_shift)
    f.close()

    return


def create_level3_hdf5(config, filename, epoch_time, rf_distance, snr_db,
                       lattitude, longitude, altitude, azimuth, elevation, slant_range,
                       velocity_azimuth, velocity_elevation, velocity, azimuth_extent, elevation_extent, area):
    # Add general information
    # general information
    f = h5py.File(filename, 'w')
    f.create_group('info')
    f.create_dataset('info/date_created', data=np.array(config.date_created))
    f.create_dataset('info/version', data=np.array(config.version, dtype='S'))
    f.create_dataset('info/date', data=config.date)
    f.create_dataset('info/experiment_name', data=np.array([config.experiment_name], dtype='S'))
    f.create_dataset('info/radar_config', data=np.array([config.radar_config], dtype='S'))
    f.create_dataset('info/center_freq', data=config.center_freq)
    # receiver site information
    f.create_dataset('info/rx_site_name', data=np.array([config.rx_site_name], dtype='S'))
    f.create_dataset('info/rx_site_lat_long', data=config.rx_site_lat_long)
    f.create_dataset('info/rx_heading', data=config.rx_heading)
    f.create_dataset('info/rx_rf_path', data=np.array([config.rx_rf_path], dtype='S'))
    f.create_dataset('info/rx_ant_type', data=np.array([config.rx_ant_type], dtype='S'))
    f.create_dataset('info/rx_ant_coords', data=config.rx_ant_coords)
    f.create_dataset('info/rx_feed_corr', data=config.rx_feed_corr)
    f.create_dataset('info/rx_feed_corr_date', data=config.rx_feed_corr_date)
    f.create_dataset('info/rx_feed_corr_type', data=np.array([config.rx_feed_corr_type], dtype='S'))
    f.create_dataset('info/rx_ant_mask', data=config.rx_ant_mask)
    f.create_dataset('info/rx_sample_rate', data=config.rx_sample_rate)
    # transmitter site information
    f.create_dataset('info/tx_site_name', data=np.array([config.tx_site_name], dtype='S'))
    f.create_dataset('info/tx_site_lat_long', data=config.tx_site_lat_long)
    f.create_dataset('info/tx_heading', data=config.tx_heading)
    f.create_dataset('info/tx_rf_path', data=np.array([config.tx_rf_path], dtype='S'))
    f.create_dataset('info/tx_ant_type', data=np.array([config.tx_ant_type], dtype='S'))
    f.create_dataset('info/tx_ant_coords', data=config.tx_ant_coords)
    f.create_dataset('info/tx_feed_corr', data=config.tx_feed_corr)
    f.create_dataset('info/tx_feed_corr_date', data=config.tx_feed_corr_date)
    f.create_dataset('info/tx_feed_corr_type', data=np.array([config.tx_feed_corr_type], dtype='S'))
    f.create_dataset('info/tx_ant_mask', data=config.tx_ant_mask)
    f.create_dataset('info/tx_sample_rate', data=config.tx_sample_rate)
    # processing settings
    f.create_dataset('info/decimation_rate', data=config.decimation_rate)
    f.create_dataset('info/time_resolution', data=config.time_resolution)
    f.create_dataset('info/coherent_integration_time', data=config.coherent_integration_time)
    f.create_dataset('info/incoherent_averages', data=config.incoherent_averages)
    f.create_dataset('info/snr_cutoff_db', data=config.snr_cutoff_db)
    # imaging settings
    f.create_dataset('info/image_method', data=np.array([config.image_method], dtype='S'))
    f.create_dataset('info/swht_coeffs', data=np.array([config.swht_coeffs], dtype='S'))
    f.create_dataset('info/fov', data=config.fov)
    f.create_dataset('info/fov_center', data=config.fov_center)
    f.create_dataset('info/resolution', data=config.resolution)
    f.create_dataset('info/lmax', data=config.lmax)

    # Create datasets
    f.create_group('data')
    # f.create_dataset('data/time_indices', data=time_indices)
    f.create_dataset('data/time', data=epoch_time)
    f.create_dataset('data/rf_distance', data=rf_distance)
    f.create_dataset('data/snr_db', data=snr_db)
    f.create_dataset('data/latitude', data=lattitude)
    f.create_dataset('data/longitude', data=longitude)
    f.create_dataset('data/altitude', data=altitude)
    f.create_dataset('data/azimuth', data=azimuth)
    f.create_dataset('data/elevation', data=elevation)
    f.create_dataset('data/slant_range', data=slant_range)
    f.create_dataset('data/velocity_azimuth', data=velocity_azimuth)
    f.create_dataset('data/velocity_elevation', data=velocity_elevation)
    f.create_dataset('data/velocity', data=velocity)
    f.create_dataset('data/azimuth_extent', data=azimuth_extent)
    f.create_dataset('data/elevation_extent', data=elevation_extent)
    f.create_dataset('data/area', data=area)

    f.close()

    return None


def epoch_time(start):
    time = datetime.datetime(year=start[0], month=start[1], day=start[2], hour=start[3],
                             minute=start[4], second=start[5], microsecond=0, tzinfo=tzutc())
    epoch = time.timestamp()
    return epoch


class Config:
    def __init__(self, configuration):
        self.update_config(configuration)
        # Add version attribute
        here = os.path.abspath(os.path.dirname(__file__))
        regex = "(?<=__version__..\s)\S+"
        with open(os.path.join(here, '__init__.py'), 'r', encoding='utf-8') as f:
            text = f.read()
        match = re.findall(regex, text)
        setattr(self, 'version', '0.0.1')
        # setattr(self, 'version', str(match[0].strip("'")))
        # Add date_created attribute
        now = datetime.datetime.now()
        setattr(self, 'date_created', [now.year, now.month, now.day])
        # setattr(self, 'date_created', [2021, 6, 28])

    def update_config(self, file):
        if file.split('.')[1] == 'yml':
            with open(file, 'r') as stream:
                cfg = yaml.full_load(stream)
                for key, value in cfg.items():
                    setattr(self, key, np.array(value))
        if file.split('.')[1] == 'h5':
            stream = h5py.File(file, 'r')
            for key in list(stream.keys()):
                if key == 'data' or key == 'coeffs':
                    pass
                # This horrible little patch fixes strings to UTF-8 from 'S' when loaded from HDF5's
                # and removes unnecessary arrays
                elif '|S' in str(stream[f'{key}'].dtype):
                    temp_value = stream[f'{key}'][()].astype('U')
                    if len(temp_value) == 1:
                        temp_value = temp_value[0]
                    setattr(self, key, temp_value)
                else:
                    temp_value = stream[f'{key}'][()]
                    try:
                        if len(temp_value) == 1:
                            temp_value = temp_value[0]
                        setattr(self, key, temp_value)
                    except:
                        setattr(self, key, temp_value)

    def print_attrs(self):
        print("experiment attributes loaded: ")
        for item in vars(self).items():
            print(f"\t-{item}")
        return None

    def update_attr(self, key, value):
        if not self.check_attr(key):
            print(f'ERROR: Attribute {key} does not exists')
            exit()
        else:
            setattr(self, key, value)
        return None

    def check_attr(self, key):
        if hasattr(self, key):
            return True
        else:
            return False

    def compare_attr(self, key, value):
        if not self.check_attr(key):
            print(f'ERROR: Attribute {key} does not exists')
            exit()
        else:
            if getattr(self, key) == value:
                return True
            else:
                return False

    def add_attr(self, key, value):
        if self.check_attr(key):
            print(f'ERROR: Attribute {key} already exists')
            exit()
        else:
            setattr(self, key, value)
        return None

    def remove_attr(self, key):
        if not self.check_attr(key):
            print(f'ERROR: Attribute {key} does not exists')
            exit()
        else:
            delattr(self, key)
        return None


if __name__ == '__main__':
    # Pretty plot configuration.
    from matplotlib import rc

    rc('font', **{'family': 'serif', 'serif': ['DejaVu Serif']})
    SMALL_SIZE = 10
    MEDIUM_SIZE = 12
    BIGGER_SIZE = 12
    plt.rc('font', size=MEDIUM_SIZE)  # controls default text sizes
    plt.rc('axes', titlesize=BIGGER_SIZE)  # fontsize of the axes title
    plt.rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labelsa
    plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

    # Load the level 2 data file.
    filepath = '/beaver/backup/level2b/'  # Enter file path to level 1 directory
    # filepath = 'E:/icebear/level2b/'  # Enter file path to level 1 directory
    # files = utils.get_all_data_files(filepath, '2020_12_12', '2020_12_14')  # Enter first sub directory and last
    # files = utils.get_all_data_files(filepath, '2019_12_19', '2019_12_19')  # Enter first sub directory and last
    files = utils.get_all_data_files(filepath, '2020_03_31', '2020_03_31')  # Enter first sub directory and last
    # files = utils.get_all_data_files(filepath, '2021_02_02', '2021_02_02')  # Enter first sub directory and last
    # files = utils.get_all_data_files(filepath, '2020_06_16', '2020_06_16')

    pack_name = 'demo_ib3d_level3_20200616.h5'

    rf_distance = np.array([])
    snr_db = np.array([])
    doppler_shift = np.array([])
    azimuth = np.array([])
    elevation = np.array([])
    elevation_extent = np.array([])
    azimuth_extent = np.array([])
    area = np.array([])
    t = np.array([])
    for file in files:
        f = h5py.File(file, 'r')
        config = utils.Config(file)
        print(file)
        group = f['data']
        date = f['date']
        keys = group.keys()
        for key in keys:
            data = group[f'{key}']
            # Filter out dropped samples
            if np.any(data['rf_distance'][()] < 250):
                continue
            et = data['time'][()]
            et = np.append(date, et)
            et[5] = int(et[5] / 1000)
            et = epoch_time(et)
            t = np.append(t, np.repeat(et, len(data['rf_distance'][()])))
            rf_distance = np.append(rf_distance, data['rf_distance'][()])
            snr_db = np.append(snr_db, np.abs(data['snr_db'][()]))
            doppler_shift = np.append(doppler_shift, data['doppler_shift'][()])
            azimuth = np.append(azimuth, data['azimuth'][()])
            elevation = np.append(elevation, np.abs(data['elevation'][()]))
            elevation_extent = np.append(elevation_extent, data['elevation_extent'][()])
            azimuth_extent = np.append(azimuth_extent, data['azimuth_extent'][()])
            area = np.append(area, data['area'][()])

    print('\t-loading completed')
    azimuth += 7.0
    print('\t-total data', len(rf_distance))
    # Pre-masking
    m = np.ones_like(rf_distance)
    m = np.ma.masked_where(snr_db <= 6.0, m)  # Weak signals close to noise or highly multipathed (meteors are strong)
    # m = np.ma.masked_where(doppler_shift >= 50, m)  # Meteors are less than |150 m/s|
    # m = np.ma.masked_where(doppler_shift <= -50, m)  # Meteors are less than |150 m/s|
    # m = np.ma.masked_where(area >= 5.0, m)  # Meteors should have small scattering cross-sectional area

    rf_distance = rf_distance * m
    snr_db = snr_db * m
    doppler_shift = doppler_shift * m
    azimuth = azimuth * m
    azimuth_extent = azimuth_extent * m
    elevation = elevation * m
    elevation_extent = elevation_extent * m
    area = area * m
    t = t * m
    print('\t-pre-masking completed')

    sx, sa, sv = map_target([50.893, -109.403, 0.0],
                            [52.243, -106.450, 0.0],
                            azimuth, elevation, rf_distance,
                            doppler_shift, 6.056)
    lat = sx[0, :]
    lon = sx[1, :]
    altitude = sx[2, :]
    vaz = sv[0, :]
    vel = sv[1, :]
    doppler_shift = sv[2, :]
    slant_range = sa[2, :]
    bad_alt = -6378.0 + np.sqrt(6378.0**2 + slant_range**2 - 2*6328.0*slant_range*np.cos(np.deg2rad(90 + elevation)))
    elevation = sa[1, :]
    print('\t-mapping completed')

    # Set up a filtering mask.
    m = np.ma.masked_where(elevation == np.nan, m)  # Elevation iterations not converging (noise)
    m = np.ma.masked_where(elevation <= 0.0, m)  # Elevation below the ground
    m = np.ma.masked_where(slant_range <= 275, m)  # Man made noise and multipath objects
    m = np.ma.masked_where(altitude <= 50, m)  # Man made noise and multipath objects
    # m = np.ma.masked_where(((slant_range <= 100.0) & (altitude <= 25.0)), m)  # Beam camping location
    rf_distance = rf_distance * m
    snr_db = snr_db * m
    doppler_shift = doppler_shift * m
    azimuth = azimuth * m
    azimuth_extent = azimuth_extent * m
    elevation = elevation * m
    elevation_extent = elevation_extent * m
    area = area * m
    slant_range = slant_range * m
    altitude = altitude * m
    bad_alt = bad_alt * m
    t = t * m
    lat = lat * m
    lon = lon * m
    vaz = vaz * m
    vel = vel * m

    rf_distance = rf_distance[~rf_distance.mask].flatten()
    snr_db = snr_db[~snr_db.mask].flatten()
    doppler_shift = doppler_shift[~doppler_shift.mask].flatten()
    azimuth = azimuth[~azimuth.mask].flatten()
    azimuth_extent = azimuth_extent[~azimuth_extent.mask].flatten()
    elevation = elevation[~elevation.mask].flatten()
    elevation_extent = elevation_extent[~elevation_extent.mask].flatten()
    area = area[~area.mask].flatten()
    slant_range = slant_range[~slant_range.mask].flatten()
    altitude = altitude[~altitude.mask].flatten()
    bad_alt = bad_alt[~bad_alt.mask].flatten()
    t = t[~t.mask].flatten()
    lat = lat[~lat.mask].flatten()
    lon = lon[~lon.mask].flatten()
    vaz = vaz[~vaz.mask].flatten()
    vel = vel[~vel.mask].flatten()

    print('\t-masking completed')
    print('\t-remaining data', len(rf_distance))

    plt.figure()
    plt.subplot(211)
    plt.scatter(slant_range, bad_alt, c='r', marker='.')
    plt.plot([0, 1000], [110, 110], '--k')
    plt.plot([0, 1000], [70, 70], '--k')
    plt.grid()
    #plt.axis('equal')
    plt.xlim(200, 1000)
    plt.ylim(0, 300)
    #plt.xlabel('Slant Range [km]')
    plt.ylabel('Altitude [km]')
    # plt.title('Conventional')
    plt.title('Geminids Meteor Shower\nDecember 12-15, 2020')

    plt.subplot(212)
    plt.scatter(slant_range, altitude, c='b', marker='.')
    plt.plot([0, 1000], [110, 110], '--k')
    plt.plot([0, 1000], [70, 70], '--k')
    #plt.axis('equal')
    plt.grid()
    plt.xlim(200, 1000)
    plt.ylim(0, 300)
    plt.xlabel('Slant Range [km]')
    plt.ylabel('Altitude [km]')
    # plt.title('Geo-central')

    #plt.suptitle('Geminids Meteor Shower\n2020-12-15')
    plt.tight_layout()
    # plt.savefig('/beaver/backup/images/conventional_vs_geocentral.png')
    # plt.show()
    print(len(altitude))


    plt.figure()
    mean_altitude = np.mean(altitude)
    total_targets = len(altitude)
    _ = plt.hist(bad_alt, bins='auto', orientation='horizontal', histtype=u'step', label=f'Conventional')
    _ = plt.hist(altitude, bins='auto', orientation='horizontal', histtype=u'step', label=f'Geocentral')
    # plt.xscale('log')
    plt.title('Conventional versus Geocentral Altitude Distribution')
    plt.xlabel('Count')
    plt.ylabel('Altitude [km]')
    plt.ylim((50, 200))
    plt.xlim((10, 4_000))
    plt.plot([0, 4_000], [mean_altitude, mean_altitude], '--k', label=f'Mean Altitude {mean_altitude:.1f} [km]')
    plt.legend(loc='upper right')
    plt.grid()
    # plt.savefig(f'/beaver/backup/images/20210202_scatter_distribution.png')
    #
    # plt.figure(figsize=[12, 12])
    # mean_longitude = np.mean(lon)
    # _ = plt.hist(lon, bins='auto', orientation='vertical', histtype=u'step', label=f'Total Targets {total_targets}')
    # plt.yscale('log')
    # # plt.title('E-Region Scatter 2020-03-31 Altitude Distribution')
    # # plt.title('E-Region Scatter 2019-12-19 Longitude Distribution')
    # plt.title('E-Region Scatter 2021-02-02 Longitude Distribution')
    # # plt.title('Geminids 2020-12-12 to 2020-12-15 Meteor Altitude Distribution')
    # plt.xlabel('Longitude [deg]')
    # plt.ylabel('Count')
    # plt.ylim((10, 100_000))
    # plt.xlim((-114.0, -96.0))
    # plt.plot([mean_longitude, mean_longitude], [10, 100_000], '--k', label=f'Mean Longitude {mean_longitude:.1f} [km]')
    # plt.legend(loc='upper right')
    # plt.grid()
    # # plt.savefig(f'/beaver/backup/geminids/summary/altitude_histogram_filtered_02.png')
    plt.show()

exit()  # Needs a clean exit?
