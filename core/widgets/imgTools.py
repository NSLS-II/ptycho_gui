import numpy as np
from scipy.ndimage import median_filter

def rm_outlier_pixels(data, rows, cols, set_to_zero=False):
    '''
    WARNING: this function mutates the input array "data"!!!
    '''
    if set_to_zero:
        data[rows, cols] = 0.
    else:
        assert(len(rows) == len(cols))
        for x, y in zip(rows, cols):
            data[x,y] = np.median(data[x-1:x+1,y-1:y+1])
    return data

def find_outlier_pixels(data,tolerance=3,worry_about_edges=True, get_fixed_image=False):
    #This function finds the hot or dead pixels in a 2D dataset.
    #tolerance is the number of standard deviations used to cutoff the hot pixels
    #If you want to ignore the edges and greatly speed up the code, then set
    #worry_about_edges to False.
    #
    #The function returns a list of hot pixels and also an image with with hot pixels removed

    data = data.astype(float)
    blurred = median_filter(data, size=2)
    difference = data - blurred
    threshold = 10*np.std(difference)

    #find the hot pixels, but ignore the edges
    hot_pixels = np.nonzero((np.abs(difference[1:-1,1:-1])>threshold) )
    hot_pixels = np.array(hot_pixels) + 1 #because we ignored the first row and first column

    if get_fixed_image:
        fixed_image = np.copy(data) #This is the image with the hot pixels removed
        for y,x in zip(hot_pixels[0],hot_pixels[1]):
            fixed_image[y,x]=blurred[y,x]

        if worry_about_edges == True:
            height,width = np.shape(data)
            ###Now get the pixels on the edges (but not the corners)###

            #left and right sides
            for index in range(1,height-1):
                #left side:
                med  = np.median(data[index-1:index+2,0:2])
                diff = np.abs(data[index,0] - med)
                if diff>threshold:
                    hot_pixels = np.hstack(( hot_pixels, [[index],[0]]  ))
                    fixed_image[index,0] = med

                #right side:
                med  = np.median(data[index-1:index+2,-2:])
                diff = np.abs(data[index,-1] - med)
                if diff>threshold:
                    hot_pixels = np.hstack(( hot_pixels, [[index],[width-1]]  ))
                    fixed_image[index,-1] = med

            #Then the top and bottom
            for index in range(1,width-1):
                #bottom:
                med  = np.median(data[0:2,index-1:index+2])
                diff = np.abs(data[0,index] - med)
                if diff>threshold:
                    hot_pixels = np.hstack(( hot_pixels, [[0],[index]]  ))
                    fixed_image[0,index] = med

                #top:
                med  = np.median(data[-2:,index-1:index+2])
                diff = np.abs(data[-1,index] - med)
                if diff>threshold:
                    hot_pixels = np.hstack(( hot_pixels, [[height-1],[index]]  ))
                    fixed_image[-1,index] = med

            ###Then the corners###

            #bottom left
            med  = np.median(data[0:2,0:2])
            diff = np.abs(data[0,0] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[0],[0]]  ))
                fixed_image[0,0] = med

            #bottom right
            med  = np.median(data[0:2,-2:])
            diff = np.abs(data[0,-1] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[0],[width-1]]  ))
                fixed_image[0,-1] = med

            #top left
            med  = np.median(data[-2:,0:2])
            diff = np.abs(data[-1,0] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[height-1],[0]]  ))
                fixed_image[-1,0] = med

            #top right
            med  = np.median(data[-2:,-2:])
            diff = np.abs(data[-1,-1] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[height-1],[width-1]]  ))
                fixed_image[-1,-1] = med

        return hot_pixels,fixed_image
    return hot_pixels

def find_brightest_pixels(data):
    indices = np.where(data == np.max(data))
    return indices
