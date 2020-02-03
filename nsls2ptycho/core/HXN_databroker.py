from databroker import Broker
import numpy as np
import sys, os
import h5py
try:
    from nsls2ptycho.core.widgets.imgTools import rm_outlier_pixels
except ModuleNotFoundError:
    # for test purpose
    from widgets.imgTools import rm_outlier_pixels

from hxntools.handlers import register
from hxntools.scan_info import ScanInfo
try:
    # new mongo database
    hxn_db = Broker.named('hxn')
    register(hxn_db)
except FileNotFoundError:
    print("hxn.yml not found. Unable to access HXN's database.", file=sys.stderr)
    hxn_db = None


# ***************************** "Public API" *****************************
# The following functions must exist in nsls2ptycho/core/*_databroker.py,
# but the function signatures do not need to agree across modules
# (obviously, it is impossible for all beamlines to have the same setup).
#   - load_metadata
#   - save_data
#   - get_single_image
#   - get_detector_names
# Other function must not be imported in the GUI.
# ************************************************************************


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
    header = db[sid]

    plan_args = header.start['plan_args']
    scan_type = header.start['plan_name']
    scan_motors = header.start['motors']
    items = [det_name, 'sclr1_ch3', 'sclr1_ch4'] + scan_motors
    bl = db.get_table(header, stream_name='baseline')
    df = db.get_table(header, fields=items, fill=False)
    #images = db_old.get_images(db_old[sid], name=det_name)

    # get energy_kev
    dcm_th = bl.dcm_th[1]
    energy_kev = 12.39842 / (2.*3.1355893 * np.sin(dcm_th * np.pi / 180.))

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
    elif scan_type == 'rel_spiral_fermat' or scan_type == 'fermat':
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

    # get points
    num_frame, count = np.shape(df)
    points = np.zeros((2, num_frame))
    points[0] = np.array(df[scan_motors[0]])
    points[1] = np.array(df[scan_motors[1]])

    # get angle, ic
    if scan_motors[1] == 'ssy':
        angle = 0#bl.zpsth[1]
        ic = np.asfarray(df['sclr1_ch3'])
    elif scan_motors[1] == 'zpssy':
        angle = bl.zpsth[1]
        ic = np.asfarray(df['sclr1_ch4'])
    else:
        angle = bl.dsth[1]
        ic = np.asfarray(df['sclr1_ch4'])
    
    # get ccd_pixel_um
    ccd_pixel_um = 55.

    # get diffamp dimensions (uncropped!)
    nz, = df[det_name].shape
    mds_table = df[det_name]

    # get nx and ny by looking at the first image
    img = db.reg.retrieve(mds_table.iat[0])[0]
    nx, ny = img.shape # can also give a ValueError; TODO: come up a better way!

    # write everything we need to a dict
    metadata = dict()
    metadata['xray_energy_kev'] = energy_kev
    metadata['scan_type'] = scan_type
    metadata['dr_x'] = dr_x
    metadata['dr_y'] = dr_y
    metadata['x_range'] = x_range
    metadata['y_range'] = y_range
    metadata['points'] = points
    metadata['angle'] = angle
    metadata['ic'] = ic
    metadata['ccd_pixel_um'] = ccd_pixel_um
    metadata['nz'] = nz
    metadata['nx'] = nx
    metadata['ny'] = ny
    metadata['mds_table'] = mds_table

    return metadata


def save_data(db, param, scan_num:int, n:int, nn:int, cx:int, cy:int, threshold=1., bad_pixels=None, zero_out=None):
    '''
    Save metadata and diffamp for the given scan number to a HDF5 file.

    Parameters:
        - db: 
            a Broker instance.
        - param: Param
            a Param instance containing the metadata and other information from the GUI
        - scan_num: int
            the scan number
        - n: int
            the x dimension of the ROI window (=nx_prb)
        - nn: int
            the y dimension of the ROI window (=ny_prb)
        - cx: int
            x index of the center of mass
        - cy: int
            y index of the center of mass
        - threshold: float, optional
            the threshold of raw image, below which the data is removed
        - bad_pixels: list of two lists, optional
            the data structure is [[x1, x2, ...], [y1, y2, ...]]. If given, they will be removed from the images.
        - zero_out: list of tuples, optional
            zero out the given rois [(x0, y0, w0, h0), (x1, y1, w1, h1), ...]

    Notes:
        1. the detector distance is assumed existent as param.z_m
    '''
    det_distance_m = param.z_m
    det_pixel_um = param.ccd_pixel_um
    num_frame = param.nz
    angle = param.angle
    lambda_nm = param.lambda_nm
    ic = param.ic
    #energy_kev = param.energy_kev

    #print('energy:', energy_kev)
    #print('angle: ', angle)
    #lambda_nm = 1.2398/energy_kev
    x_pixel_m = lambda_nm * 1.e-9 * det_distance_m / (n * det_pixel_um * 1e-6)
    y_pixel_m = lambda_nm * 1.e-9 * det_distance_m / (nn * det_pixel_um * 1e-6)
    x_depth_of_field_m = lambda_nm * 1.e-9 / (n/2 * det_pixel_um*1.e-6 / det_distance_m)**2
    y_depth_of_field_m = lambda_nm * 1.e-9 / (nn/2 * det_pixel_um*1.e-6 / det_distance_m)**2
    #print('pixel size: ', x_pixel_m, y_pixel_m)
    #print('depth of field: ', x_depth_of_field_m, y_depth_of_field_m)
    
    # get data array
    data = np.zeros((num_frame, n//2*2, nn//2*2)) # nz*nx*ny
    mask = []
    for i in range(num_frame):
        #print(param.mds_table.iat[i], file=sys.stderr)
        img = db.reg.retrieve(param.mds_table.iat[i])[0]
        #img = np.rot90(img, axes=(1,0)) #equivalent to tt = np.flipud(tt).T
        ny, nx = np.shape(img)

        img = img * ic[0] / ic[i]

        if bad_pixels is not None:
            img = rm_outlier_pixels(img, bad_pixels[0], bad_pixels[1])

        if zero_out is not None:
            for blue_roi in zero_out:
                x0 = blue_roi[0]
                y0 = blue_roi[1]
                w = blue_roi[2]
                h = blue_roi[3]
                img[y0:y0+h, x0:x0+w] = 0.

        if n < nx:
            # assuming n=nn???
            #print(nx, ny, file=sys.stderr)
            #print(cx-n//2, cx+n//2, cy-nn//2, cy+nn//2, file=sys.stderr)
            #tmptmp = img[cx-n//2:cx+n//2, cy-nn//2:cy+nn//2]
            tmptmp = img[cy-nn//2:cy+nn//2, cx-n//2:cx+n//2]
            #print(tmptmp.shape, file=sys.stderr)
        else: 
            raise Exception("zero padding not completed yet")
            # # is this part necessary???
            # #tmptmp = t
            # tmptmp = np.zeros((n, n))
            # #tmptmp[3:-3,:] = t[:,cy-n//2:cy+n//2]
            # tmptmp[4:-8, :] = img[:, cy-n//2:cy+n//2]

        #if i == 0:
        #    import matplotlib.pyplot as plt
        #    plt.imshow(tmptmp, vmin=np.min(img), vmax=np.max(img))
        #    plt.savefig("ttttt.png")
        #    return
        
        tmptmp = np.rot90(tmptmp, axes=(1,0)) #equivalent to np.flipud(tmptmp).T
        if not np.sum(tmptmp) > 0.:
            mask.append(i)
        data[i] = np.fft.fftshift(tmptmp)

    if len(mask) > 0:
        print("Removing the dark frames:", mask, file=sys.stderr)
        data = np.delete(data, mask, axis=0)
        param.points = np.delete(param.points, mask, axis=1)
        param.nz = param.nz - len(mask)
    data[data < threshold] = 0.
    data = np.sqrt(data)
    # data array got
    print('array size:', np.shape(data))
    
    # create a folder
    try:
        os.mkdir(param.working_directory + '/h5_data/')
    except FileExistsError:
        pass 

    file_path = param.working_directory + '/h5_data/scan_' + str(scan_num) + '.h5'
    with h5py.File(file_path, 'w') as hf:
        dset = hf.create_dataset('diffamp', data=data)
        dset = hf.create_dataset('points', data=param.points)
        dset = hf.create_dataset('x_range', data=param.x_range)
        dset = hf.create_dataset('y_range', data=param.y_range)
        dset = hf.create_dataset('dr_x', data=param.dr_x)
        dset = hf.create_dataset('dr_y', data=param.dr_y)
        dset = hf.create_dataset('z_m', data=det_distance_m)
        dset = hf.create_dataset('lambda_nm', data=lambda_nm)
        dset = hf.create_dataset('ccd_pixel_um', data=det_pixel_um)
        dset = hf.create_dataset('angle', data=angle)
        dset = hf.create_dataset('ic', data=ic)
        dset = hf.create_dataset('x_pixel_m', data=x_pixel_m)
        dset = hf.create_dataset('y_pixel_m', data=y_pixel_m)
        dset = hf.create_dataset('x_depth_field_m', data=x_depth_of_field_m)
        dset = hf.create_dataset('y_depth_field_m', data=y_depth_of_field_m)

    # symlink so ptycho can find it
    try:
        symlink_path = param.working_directory + '/scan_' + str(scan_num) + '.h5'
        os.symlink(file_path, symlink_path)
    except FileExistsError:
        os.remove(symlink_path)
        os.symlink(file_path, symlink_path)


def get_single_image(db, frame_num, mds_table):
    length = (mds_table.shape)[0] 
    if frame_num >= length:
        message = "[ERROR] The {0}-th frame doesn't exist. "
        message += "Available frames for the chosen scan: [0, {1}]."
        raise ValueError(message.format(frame_num, length-1))

    img = db.reg.retrieve(mds_table.iat[frame_num])[0]
    return img


def get_detector_names(db, scan_num:int):
    '''
    Returns
    -------
        list: detectors used in the scan or available in the beamline
    '''
    # TODO: a better way without ScanInfo?
    scan = ScanInfo(db[scan_num])
    return [key for key in scan.filestore_keys]
