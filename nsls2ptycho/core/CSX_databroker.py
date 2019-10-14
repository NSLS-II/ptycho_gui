from databroker import Broker, get_table
import numpy as np
import sys, os
import h5py
try:
    from nsls2ptycho.core.widgets.imgTools import rm_outlier_pixels
except ModuleNotFoundError:
    # for test purpose
    from widgets.imgTools import rm_outlier_pixels

try:
    # TODO(leofang): RENAME THIS!!!!!   
    hxn_db = Broker.named('csx')
except FileNotFoundError:
    print("csx.yml not found. Unable to access CSX's database.", file=sys.stderr)
    hxn_db = None
from csxtools.utils import get_fastccd_images


#######################################


def load_metadata(db, scan_num:int, det_name:str=''):
    '''
    Get all metadata for the given scan number and detector name

    Parameters:
        - db: 
            a Broker instance.
        - scan_num: int
            the scan number
        - det_name: str
            the detector name; not used in CSX

    Return:
        A dictionary that holds the metadata (except for those directly related to the image)
    '''
    header = db[scan_num]
    scan_data = header.table(fill=False, stream_name='primary')  # acquired counters during the scan/ct, images excluded
    scan_supp = header.table(fill=False, stream_name='baseline') # supplementary information, images excluded

    scan_type = header.start['plan_name']
    plan_args = header.start['plan_args']
    nz = header.start['num_points']

    # get energy_kev
    energy_kev = scan_supp.pgm_energy_setpoint.iat[0] / 1E+3

    # get scan_type, x_range, y_range, dr_x, dr_y
    extents = header.start['extents']
    if scan_type.endswith('grid_scan'):
        x_num = plan_args['args'][7]
        y_num = plan_args['args'][3]
        x_range = (extents[0][1] - extents[0][0]) * 1E+3
        y_range = (extents[1][1] - extents[1][0]) * 1E+3
        dr_x = x_range / (x_num - 1)
        dr_y = y_range / (y_num - 1)
    elif scan_type == 'spiral_continuous':
        # The customized plan messed up...
        x_range = (extents[0][1] - extents[0][0])/2 * 1E+3
        y_range = (extents[1][1] - extents[1][0])/2 * 1E+3
        # not available in CSX
        dr_x = 0
        dr_y = 0
    else:
        raise NotImplementedError("Ask Wen Hu to explain to Leo Fang.")

    # get points
    points = np.zeros((2, nz))
    points[0] = scan_data.nanop_bx * 1E+3
    points[1] = scan_data.nanop_bz * 1E+3

    # get angle, ic
    angle = scan_supp.tardis_theta.iat[0]  # TODO(leofang): verify this
    
    # get ccd_pixel_um
    ccd_pixel_um = 30.

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
    metadata['ccd_pixel_um'] = ccd_pixel_um
    metadata['nz'] = nz
    metadata['nx'] = 960
    metadata['ny'] = 960

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
    data = np.zeros((num_frame, n, nn)) # nz*nx*ny
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


scan_image_itr_cache = {}


def load_scan_image_itr(db, scan_num:int, dark8ID:int=None, dark2ID:int=None, dark1ID:int=None):
    bgnd8 = db[dark8ID] if (dark8ID is not None) else None
    bgnd2 = db[dark2ID] if (dark2ID is not None) else None
    bgnd1 = db[dark1ID] if (dark1ID is not None) else None
    if (bgnd8 is None) and (bgnd2 is None) and (bgnd1 is None):
        dark_headers = None
    else:
        dark_headers = (bgnd8, bgnd2, bgnd1)
    silcerator = get_fastccd_images(db[scan_num], dark_headers=dark_headers)
    return silcerator


def get_single_image(db, frame_num, scan_num:int, dark8ID:int=None, dark2ID:int=None, dark1ID:int=None):
    key = (scan_num, dark8ID, dark2ID, dark1ID)
    if key in scan_image_itr_cache:
        return scan_image_itr_cache[key][frame_num]
    else:
        itr = load_scan_image_itr(db, scan_num, dark8ID, dark2ID, dark1ID)
        scan_image_itr_cache[key] = itr
        print(type(itr[frame_num]))
        return np.mean(itr[frame_num], axis=0)
