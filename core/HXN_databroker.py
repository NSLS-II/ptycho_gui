#from hxntools.handlers import register
#import filestore
from metadatastore.mds import MDS
from databroker import Broker
from filestore.fs import FileStore

# database #1
_mds_config = {'host': 'xf03id-ca1',
               'port': 27017,
               'database': 'datastore-new',
               'timezone': 'US/Eastern'}
mds = MDS(_mds_config)
_fs_config = {'host': 'xf03id-ca1',
              'port': 27017,
              'database': 'filestore-new'}
db1 = Broker(mds, FileStore(_fs_config))

# database #2
_mds_config = {'host': 'xf03id-ca1',
               'port': 27017,
               'database': 'datastore-1',
               'timezone': 'US/Eastern'}
mds = MDS(_mds_config)
_fs_config = {'host': 'xf03id-ca1',
              'port': 27017,
              'database': 'filestore-1'}
db2 = Broker(mds, FileStore(_fs_config))

# database old
_mds_config_old = {'host': 'xf03id-ca1',
                   'port': 27017,
                   'database': 'datastore',
                   'timezone': 'US/Eastern'}
mds_old = MDS(_mds_config_old)

_fs_config_old = {'host': 'xf03id-ca1',
                  'port': 27017,
                  'database': 'filestore'}
db_old = Broker(mds_old, FileStore(_fs_config_old))

from hxntools.handlers.timepix import TimepixHDF5Handler
from hxntools.handlers.xspress3 import Xspress3HDF5Handler
db1.reg.register_handler(TimepixHDF5Handler._handler_name, TimepixHDF5Handler, overwrite=True)
db2.reg.register_handler(TimepixHDF5Handler._handler_name, TimepixHDF5Handler, overwrite=True)
db_old.reg.register_handler(Xspress3HDF5Handler.HANDLER_NAME, Xspress3HDF5Handler)
db_old.reg.register_handler(TimepixHDF5Handler._handler_name, TimepixHDF5Handler, overwrite=True)

import numpy as np
#######################################

def load_metadata(db, scan_num:int, det_name:str):
    '''
    Get all metadata for the given scan number and detector name

    Parameters:
        - db: 
            a Broker instance. For HXN experiments they are db1, db2, and db_old
        - scan_num: int
            the scan number
        - det_name: str
            the detector name

    Return:
        A dictionary that holds the metadata (except for those directly related to the image)
    '''
    sid = scan_num
    metadata = dict()

    bl = db.get_table(db[sid], stream_name='baseline')
    df = db.get_table(db[sid], fill=False)
    #images = db_old.get_images(db_old[sid], name=det_name)
    plan_args = db[sid].start['plan_args']
    scan_type = db[sid].start['plan_name']
    scan_motors = db[sid].start['motors']

    # get energy_kev
    dcm_th = bl.dcm_th[1]
    energy_kev = 12.39842 / (2.*3.1355893 * np.sin(dcm_th * np.pi / 180.))
    metadata['energy_kev'] = energy_kev

    # get scan_type, x_range, y_range, dr_x, dr_y
    if scan_type == 'FlyPlan2D':
        x_range = plan_args['scan_end1']-plan_args['scan_start1']
        y_range = plan_args['scan_end2']-plan_args['scan_start2']
        x_num = plan_args['num1']
        y_num = plan_args['num2']
        dr_x = 1.*x_range/x_num
        dr_y = 1.*y_range/y_num
        x_range = x_range - dr_x
        y_range = y_range - dr_y
    elif scan_type == 'rel_spiral_fermat':
        x_range = plan_args['x_range']
        y_range = plan_args['y_range']
        dr_x = plan_args['dr']
        dr_y = 0
    else:
        x_range = plan_args['args'][2]-plan_args['args'][1]
        y_range = plan_args['args'][6]-plan_args['args'][5]
        x_num = plan_args['args'][3]
        y_num = plan_args['args'][7]
        dr_x = 1.*x_range/x_num
        dr_y = 1.*y_range/y_num
        x_range = x_range - dr_x
        y_range = y_range - dr_y
    metadata['scan_type'] = scan_type
    metadata['dr_x'] = dr_x
    metadata['dr_y'] = dr_y
    metadata['x_range'] = x_range
    metadata['y_range'] = y_range

    # get points
    num_frame, count = np.shape(df)
    points = np.zeros((2, num_frame))
    points[0] = np.array(df[scan_motors[0]])
    points[1] = np.array(df[scan_motors[1]])
    metadata['points'] = points

    # get angle, ic
    if scan_motors[1] == 'dssy':
        angle = bl.dsth[1]
        ic = np.asfarray(df['sclr1_ch4'])
    elif scan_motors[1] == 'zpssy':
        angle = bl.zpsth[1]
        ic = np.asfarray(df['sclr1_ch3'])
    metadata['angle'] = angle
    metadata['ic'] = ic
    
    # get ccd_pixel_um
    ccd_pixel_um = 55.
    metadata['ccd_pixel_um'] = ccd_pixel_um

    # get diffamp dimensions (uncropped!)
    nz, = df[det_name].shape
    mds_table = df[det_name]
    metadata['nz'] = nz
    metadata['mds_table'] = mds_table

    # get x_pixel_m, y_pixel_m, x_depth_of_field_m, y_depth_of_field_m
    #x_pixel_m = lambda_nm * 1.e-9 * det_distance_m / (n * det_pixel_um * 1e-6)
    #y_pixel_m = lambda_nm * 1.e-9 * det_distance_m / (nn * det_pixel_um * 1e-6)
    #x_depth_of_field_m = lambda_nm * 1.e-9 / (n/2 * det_pixel_um*1.e-6 / det_distance_m)**2
    #y_depth_of_field_m = lambda_nm * 1.e-9 / (nn/2 * det_pixel_um*1.e-6 / det_distance_m)**2
    #metadata['x_pixel_m'] = x_pixel_m
    #metadata['y_pixel_m'] = y_pixel_m
    #metadata['x_depth_of_field_m'] = x_depth_of_field_m
    #metadata['y_depth_of_field_m'] = y_depth_of_field_m

    return metadata
