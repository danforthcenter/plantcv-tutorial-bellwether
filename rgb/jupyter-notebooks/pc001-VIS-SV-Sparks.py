#!/usr/bin/env python
# coding: utf-8

# # PlantCV Analysis of VIS (aka RGB) sideview (SV) images from experiment PC001 in the Bellwether Phenotyping Facility
# 
# Made by: Katie Murphy
# Updated: August 30, 2026

# ## Step 1: Import Packages
# 
# First, import the necessary package. If you get an error here, make sure your kernel (upper right) is set to PlantCV, and that you have PlantCV installed. 

# In[1]:


# %matplotlib widget makes the plots interactive (zoomable/pannable), which helps when you need to
# hover over the image to read off pixel coordinates (e.g. for the ROI or boundary line later on)
# Import the main PlantCV module (all image processing functions live here)
from plantcv import plantcv as pcv
# WorkflowInputs bundles your image path(s) and output settings into one object (args), used below
from plantcv.parallel import WorkflowInputs, workflow_inputs, JupyterConfig


# ## Step 2: Set Up Workflow Inputs
# 
# Next, import a sample image. Your images need to be on the server. Remember, always keep your raw images separate from your newly processed images! You will need to change the path to your image, and also if you want specific output folders and directories. 

# In[5]:


jupcon = JupyterConfig()
jupcon.verbose = False
jupcon.input_dir = "../img/" # path relative to your notebook
jupcon.metadata_regex = {"basename": "VIS_SV.*"}
summary, full_meta = jupcon.inspect_dataset()
jupcon.cluster_config["n_workers"] = 5
summary


# In[6]:


jupcon = JupyterConfig()
jupcon.verbose = False
jupcon.input_dir = "../img/" # path relative to your notebook
jupcon.metadata_filters = {"metadata_0":"VIS", "metadata_1":"SV"}
jupcon.groupby = ["filepath"]
summary, full_meta = jupcon.inspect_dataset()
jupcon.cluster_config["n_workers"] = 5
summary


# In[ ]:


jupcon = JupyterConfig()
jupcon.verbose = False
jupcon.input_dir = "../img/" # path relative to your notebook
jupcon.filename_metadata = ["imgtype", "camera", "angle", "zoom", "height", "gain", "exp", "view", "rep", "zo"]
jupcon.metadata_filters = {"metadata_0":"VIS", "metadata_1":"SV"}
jupcon.groupby = ["filepath"]
summary, full_meta = jupcon.inspect_dataset()
jupcon.cluster_config["n_workers"] = 5
summary


# In[ ]:


# when you are ready to run in parallel save the notebook, restart the kernel (just to be safe)
# and run to this cell with `jupcon.run()` and `args = workflow_inputs()` uncommmented

# jupcon.run()
# args = workflow_inputs()


# ## Step 3: Set Debug and Display Parameters
# 
# These settings control how PlantCV shows you feedback while you build your workflow interactively, and don't affect the final trait measurements.

# In[18]:


# Set debug to the global parameter, so every PlantCV function displays its output the same way
pcv.params.debug = args.debug
# Change display settings
pcv.params.dpi = 100            # resolution of displayed debug images
pcv.params.text_size = 3        # font size for annotations PlantCV draws on images
pcv.params.text_thickness = 2  # line thickness for annotations PlantCV draws on images


# In[6]:


import re
hline = 1950
if bool(re.search("_h0_", args.image)):
    hline = 2150


# ## Step 4: Read In Your Image
# 
# Read the RGB image from the path you set above.

# In[7]:


# Read in your image, which is based on the path you put above

# Inputs:
#   filename - Image file to be read in 
#   mode - Return mode of image; either 'native' (default), 'rgb', 'gray', or 'csv' 
img, path, filename = pcv.readimage(filename=args.image)


# ## Step 5: Color-Correct the Image
# 
# Use the color card in the image to correct for lighting/camera differences, so trait values are comparable across images taken at different times.

# In[19]:


# Detect the color card, create a matrix of color chip values, and perform linear color correction.
img_cc = pcv.transform.auto_correct_color(rgb_img=img, radius=15)


# ## Step 6: Choose a Masking Strategy
# 
# Explore colorspaces to find a channel that best separates the plant from the background, then threshold and clean up that channel to build a binary mask.

# In[10]:


# Update params related to plotting so we can see better 
pcv.params.text_size=50
pcv.params.text_thickness=15


#Look at the colorspace - which of these looks the best for masking? Which channel makes the plant look most distinct?
colorspace_img = pcv.visualize.colorspaces(rgb_img=img_cc)


# In[11]:


#mask the plant
# Convert the color-corrected image to the CMYK colorspace and keep only the cyan (c) channel,
# since that channel made the plant look most distinct from the background
gray_img = pcv.rgb2gray_cmyk(rgb_img=img_cc, channel='c')
# Turn the grayscale channel into a binary (black/white) mask: pixels lighter than 75 are kept
# as the object (the plant), since object_type='light' selects the brighter pixels
thresh_c = pcv.threshold.binary(gray_img=gray_img, threshold=75, object_type='light')


# In[12]:


# Fill small holes inside the plant mask (e.g. gaps where background shows through overlapping leaves)
c_fillholes_image = pcv.fill_holes(thresh_c)


# In[13]:


# Remove small noise objects from the mask that are smaller than 85 pixels (specks that aren't the plant)
c_fill_image = pcv.fill(bin_img=c_fillholes_image, size=85)


# ## Step 7: Define Your Region of Interest and Filter the Mask
# 
# Draw a box around where you expect your plant to be, then keep only the parts of your mask that fall inside it.

# In[14]:


# Define the region of interest (ROI). This should include your plant, but not you color card or other things. 

# Inputs: 
#   img - RGB or grayscale image to plot the ROI on 
#   x - The x-coordinate of the upper left corner of the rectangle 
#   y - The y-coordinate of the upper left corner of the rectangle 
#   h - The height of the rectangle 
#   w - The width of the rectangle 

roi1 = pcv.roi.rectangle(img=img_cc, x=750, y=0, h=hline, w=2100)


# In[15]:


# Make a new filtered mask that only keeps the plant in your ROI and not objects outside of the ROI
# We have set to partial here so that if a leaf extends outside of your ROI it will still be selected. Switch to "cutto" if you have other plants that are getting selected on accident

# Inputs:
#    mask            = the clean mask you made above
#    roi            = the region of interest you specified above
#    roi_type       = 'partial' (default, for partially inside the ROI), 'cutto', or 
#                     'largest' (keep only largest contour)

kept_mask  = pcv.roi.filter(mask=c_fill_image, roi=roi1, roi_type='partial')


# ## Step 8: Shape Analysis

# In[21]:


############### Analysis ################ 

# Find shape properties, data gets stored to an Outputs class automatically

# Inputs:
#   img - RGB or grayscale image data 
#   labeled_mask - the mask of each individual object, set by the create_labels function. 
#   n_labels - the number of objects, set by the create_labels function. 

analysis_image = pcv.analyze.size(img=img_cc, labeled_mask=kept_mask)


# In[23]:


# Shape properties relative to user boundary line (optional). This is useful if your plant is hanging below the pot and you want height from the top of the pot.
# Set your line_position by finding the x-value at the top of the pot, hover your cursor to get that value

# Inputs:
#   img - RGB or grayscale image data 
#   obj - Single or grouped contour object 
#   mask - Binary mask of selected contours 
#   line_position - Position of boundary line (a value of 0 would draw a line 
#                   through the bottom of the image) 
#   label - Optional label parameter, modifies the variable name of observations recorded. (default `label="default"`)

boundary_image = pcv.analyze.bound_horizontal(img=img_cc,labeled_mask=kept_mask, 
                                               line_position=2150, label="default")


# ## Step 9: Color Analysis

# In[ ]:


# Determine color properties: Histograms, Color Slices and Pseudocolored Images, output color analyzed images (optional)

# Inputs:
#   rgb_img - RGB image data
#   mask - Binary mask of selected contours 
#   colorspaces - 'all' (default), 'rgb', 'lab', or 'hsv'
#                 This is the data to be printed to the SVG histogram file  
#   label - Optional label parameter, modifies the variable name of observations recorded. (default `label="default"`)

color_histogram = pcv.analyze.color(rgb_img=img_cc, labeled_mask=kept_mask, colorspaces='all', label="default")


# ## Step 10: Save Your Results

# In[ ]:


# The save results function will take the measurements stored when running any PlantCV analysis functions, format, 
# and print an output text file for data analysis. The Outputs class stores data whenever any of the following functions
# are ran: analyze_bound_horizontal, analyze_bound_vertical, analyze_color, analyze_nir_intensity, analyze_object, 
# fluor_fvfm, report_size_marker_area, watershed. If no functions have been run, it will print an empty text file 

#This saves results for one image, and each image is saved individually if you run another image (it will overwrite the last one)
pcv.outputs.save_results(filename=args.result)


# ## Step 11: Build Your Batch Workflow
# 
# Congrats, you now know all the settings you like for this day of imaging! It's time to make this into a workflow so that it will analyze all your images at once and you can go have a cup of coffee. To do so, go back to the folder and open up the config_template.json file, and the config_workflow.py files, and you will edit them according to the values you changed in this file. 
