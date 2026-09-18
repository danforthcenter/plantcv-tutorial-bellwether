from plantcv import plantcv as pcv 
from plantcv.parallel import workflow_inputs
import re

# get arguments from job scheduler
args = workflow_inputs()

# read image as numpy array
img, path, filename = pcv.readimage(filename=args.image1)

hline = 1950
if bool(re.search("_h0_", args.image1)):
    hline = 2150

# color card is in a consistent location so ROI for safety
cc_roi = pcv.roi.rectangle(img, x = 1700, y = 2500, h = 500, w = 800)
img_cc = pcv.transform.auto_correct_color(rgb_img=img, roi = cc_roi, color_chip_size = "passport")

# pulling c channel to mask plant
gray_img = pcv.rgb2gray_cmyk(rgb_img=img_cc, channel='c')
thresh_c = pcv.threshold.binary(gray_img=gray_img, threshold=75, object_type='light')

# Fill small holes inside the plant mask (e.g. gaps where background shows through overlapping leaves)
c_fillholes_image = pcv.fill_holes(thresh_c)

# Remove small noise objects from the mask that are smaller than 85 pixels (specks that aren't the plant)
c_fill_image = pcv.fill(bin_img=c_fillholes_image, size=85)

# generous ROI for where the plant may end up
roi1 = pcv.roi.rectangle(img=img_cc, x=750, y=0, h=1900, w=2100)

# keep any masked objects that touch the large ROI
kept_mask  = pcv.roi.filter(mask=c_fill_image, roi=roi1, roi_type='partial')


# analysis functions
shape_analysis_image = pcv.analyze.size(img=img_cc, labeled_mask=kept_mask)


shape_boundary_image = pcv.analyze.bound_horizontal(img=img_cc,labeled_mask=kept_mask, 
                                               line_position=2150, label="default")

color_histogram = pcv.analyze.color(rgb_img=img_cc, labeled_mask=kept_mask, colorspaces='all', label="default")

# write out results
pcv.outputs.save_results(filename= args.result)
